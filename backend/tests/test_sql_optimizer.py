import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.sql_optimizer import normalize_version, version_matches


class SqlOptimizerApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_version_profiles_and_patch_normalization(self) -> None:
        response = self.client.get("/api/v1/aiops/sql-optimizer/versions")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["minor"] for item in response.json()], ["7.5", "8.0", "8.1", "8.2", "8.3", "8.4", "8.5"])
        self.assertEqual(normalize_version("v8.5.4"), ("8.5.4", "8.5"))
        self.assertTrue(version_matches("8.5", "TiDB Server version: 8.5.4 TiDB Edition"))
        self.assertFalse(version_matches("8.4", "TiDB Server version: 8.5.4 TiDB Edition"))

    def test_simulated_plan_and_tidsadvisor_style_recommendations(self) -> None:
        response = self.client.post(
            "/api/v1/aiops/sql-optimizer/analyze",
            json={
                "sql": "SELECT o.customer_id, SUM(o.amount) AS total_amount FROM sales.orders o WHERE o.created_at >= '2026-01-01' GROUP BY o.customer_id ORDER BY total_amount DESC",
                "ddl": "CREATE TABLE orders (order_id BIGINT PRIMARY KEY, customer_id BIGINT, created_at DATETIME, amount DECIMAL(18,2));",
                "tidb_version": "8.5",
                "plan_mode": "simulate",
            },
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["optimizer_mode"], "simulated")
        self.assertFalse(result["version_verified"])
        self.assertTrue(any(node["id"] == "IndexRangeScan (hypothesis)" for node in result["plan"]))
        self.assertTrue(any(item["category"] == "index" for item in result["recommendations"]))
        self.assertEqual(len(result["sources"]), 3)

    def test_rejects_write_sql_and_unknown_version(self) -> None:
        base = {"ddl": "", "tidb_version": "8.5", "plan_mode": "simulate"}
        self.assertEqual(self.client.post("/api/v1/aiops/sql-optimizer/analyze", json={**base, "sql": "DROP TABLE orders"}).status_code, 400)
        self.assertEqual(self.client.post("/api/v1/aiops/sql-optimizer/analyze", json={**base, "sql": "SELECT 1", "tidb_version": "7.4"}).status_code, 422)

    def test_existing_left_prefix_index_is_not_recommended_again(self) -> None:
        response = self.client.post(
            "/api/v1/aiops/sql-optimizer/analyze",
            json={
                "sql": "SELECT customer_id FROM orders WHERE customer_id = 1 AND created_at >= '2026-01-01'",
                "ddl": "CREATE TABLE orders (customer_id BIGINT, created_at DATETIME, KEY idx_customer_created (customer_id, created_at));",
                "tidb_version": "8.5",
                "plan_mode": "simulate",
            },
        )
        self.assertEqual(response.status_code, 200)
        recommendations = response.json()["recommendations"]
        self.assertFalse(any(item["category"] == "index" for item in recommendations))

        qualified = self.client.post(
            "/api/v1/aiops/sql-optimizer/analyze",
            json={
                "sql": "SELECT customer_id FROM sales.orders WHERE created_at >= '2026-01-01'",
                "ddl": "CREATE TABLE sales.orders (customer_id BIGINT, created_at DATETIME);",
                "tidb_version": "8.5",
                "plan_mode": "simulate",
            },
        )
        action = next(item["action"] for item in qualified.json()["recommendations"] if item["category"] == "index")
        self.assertIn("ON `sales`.`orders`", action)

    def test_version_specific_deprecated_hint_rule(self) -> None:
        sql = "SELECT /*+ INL_MERGE_JOIN(a, b) */ a.id FROM a JOIN b ON a.id = b.id"
        base = {"sql": sql, "ddl": "", "plan_mode": "simulate"}
        before = self.client.post("/api/v1/aiops/sql-optimizer/analyze", json={**base, "tidb_version": "8.2"})
        after = self.client.post("/api/v1/aiops/sql-optimizer/analyze", json={**base, "tidb_version": "8.3"})
        self.assertEqual(before.status_code, 200)
        self.assertEqual(after.status_code, 200)
        self.assertFalse(any(item["id"] == "deprecated-hint" for item in before.json()["recommendations"]))
        self.assertTrue(any(item["id"] == "deprecated-hint" for item in after.json()["recommendations"]))

    def test_upload_and_directory_inputs(self) -> None:
        upload = self.client.post(
            "/api/v1/aiops/sql-optimizer/inputs/upload",
            files=[
                ("files", ("query.sql", b"SELECT * FROM orders;", "text/plain")),
                ("files", ("schema.ddl", b"CREATE TABLE orders (id BIGINT);", "text/plain")),
            ],
        )
        self.assertEqual(upload.status_code, 200)
        self.assertEqual(upload.json()["files"], ["query.sql", "schema.ddl"])
        self.assertEqual(len(upload.json()["sql_items"]), 1)
        self.assertIn("CREATE TABLE", upload.json()["ddl"])
        self.assertEqual(
            self.client.post(
                "/api/v1/aiops/sql-optimizer/inputs/upload",
                files=[("files", ("notes.csv", b"a,b\n1,2", "text/csv"))],
            ).status_code,
            415,
        )

        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside_directory:
            root = Path(directory)
            (root / "one.sql").write_text("SELECT id FROM orders;", encoding="utf-8")
            outside = Path(outside_directory) / "outside.sql"
            outside.write_text("SELECT secret FROM outside_table;", encoding="utf-8")
            (root / "outside.sql").symlink_to(outside)
            old_roots = os.environ.get("DATASET_ALLOWED_ROOTS")
            os.environ["DATASET_ALLOWED_ROOTS"] = str(root)
            try:
                scanned = self.client.post("/api/v1/aiops/sql-optimizer/inputs/local-directory", json={"path": str(root)})
                self.assertEqual(scanned.status_code, 200)
                self.assertEqual(scanned.json()["files"], ["one.sql"])
                self.assertEqual(self.client.post("/api/v1/aiops/sql-optimizer/inputs/local-directory", json={"path": "/tmp"}).status_code, 403)
            finally:
                if old_roots is None:
                    os.environ.pop("DATASET_ALLOWED_ROOTS", None)
                else:
                    os.environ["DATASET_ALLOWED_ROOTS"] = old_roots

    def test_live_explain_requires_matching_tidb_version(self) -> None:
        endpoint = "http://tidb-mcp.test/mcp"

        async def fake_call(_endpoint, _token, _tool_map, operation, arguments):
            self.assertEqual(_endpoint, endpoint)
            if arguments["sql"] == "SELECT VERSION() AS version":
                return {"rows": [{"version": "TiDB Server version: 8.5.4"}]}
            self.assertTrue(arguments["sql"].startswith("EXPLAIN FORMAT='verbose' SELECT"))
            return {"columns": [{"name": "id"}, {"name": "estRows"}, {"name": "task"}], "rows": [["TableFullScan", "10", "cop[tikv]"]]}

        request = {"sql": "SELECT id FROM orders", "ddl": "", "tidb_version": "8.5", "plan_mode": "live", "mcp_endpoint": endpoint}
        with patch("app.main.call_mcp", side_effect=fake_call):
            response = self.client.post("/api/v1/aiops/sql-optimizer/analyze", json=request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["optimizer_mode"], "live")
        self.assertTrue(response.json()["version_verified"])
        self.assertEqual(response.json()["plan"][0]["id"], "TableFullScan")

        async def mismatch_call(_endpoint, _token, _tool_map, operation, arguments):
            return {"rows": [{"version": "TiDB Server version: 8.4.0"}]}

        with patch("app.main.call_mcp", side_effect=mismatch_call):
            mismatch = self.client.post("/api/v1/aiops/sql-optimizer/analyze", json=request)
        self.assertEqual(mismatch.status_code, 409)

        invalid_endpoint = self.client.post(
            "/api/v1/aiops/sql-optimizer/analyze",
            json={**request, "mcp_endpoint": "file:///tmp/tidb.sock"},
        )
        self.assertEqual(invalid_endpoint.status_code, 400)


if __name__ == "__main__":
    unittest.main()
