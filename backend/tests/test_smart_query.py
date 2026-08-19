import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import DATASETS, OPERATIONS, app


class SmartQueryApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        OPERATIONS.clear()
        DATASETS.clear()

    def test_health_and_catalog_include_comments_and_relationships(self) -> None:
        health = self.client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "ok")
        self.assertEqual(health.json()["database"], "tidb")
        self.assertTrue(health.headers.get("X-Request-ID", "").startswith("req-"))
        self.assertEqual(health.headers["X-Content-Type-Options"], "nosniff")
        metrics = self.client.get("/metrics")
        self.assertEqual(metrics.status_code, 200)
        self.assertIn("aegis_http_requests_total", metrics.text)

        missing_endpoint = self.client.post("/api/v1/tidb/mcp/introspect", json={})
        self.assertEqual(missing_endpoint.status_code, 400)

        response = self.client.post("/api/v1/tidb/mcp/introspect", json={"endpoint": "demo://tidb"})
        self.assertEqual(response.status_code, 200)
        catalog = response.json()
        self.assertEqual(len(catalog["schemas"]), 2)
        self.assertEqual(catalog["schemas"][0]["tables"][0]["columns"][0]["comment"], "订单唯一标识")
        self.assertEqual(len(catalog["relationships"]), 2)

        current = self.client.get("/api/v1/tidb/catalog")
        self.assertEqual(current.status_code, 200)
        self.assertEqual(current.json()["source"], "demo")

    def test_text2sql_query_returns_chart_evidence_and_operation(self) -> None:
        response = self.client.post(
            "/api/v1/query/conversations",
            json={"question": "近 30 天 GMV 趋势", "source_type": "tidb"},
        )
        self.assertEqual(response.status_code, 202)
        operation = response.json()
        self.assertEqual(operation["status"], "completed")
        self.assertTrue(operation["sql"].lower().startswith("select"))
        self.assertEqual(operation["chart"]["type"], "line")
        self.assertGreater(len(operation["rows"]), 0)
        self.assertEqual(len(operation["evidence"]), 3)

        status = self.client.get(f"/api/v1/query/operations/{operation['operation_id']}")
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()["operation_id"], operation["operation_id"])

    def test_operation_events_stream_execution_phases(self) -> None:
        response = self.client.post(
            "/api/v1/chatbi/query",
            json={"datasource_id": "ds-demo-tidb", "question": "近 30 天 GMV 趋势"},
        )
        self.assertEqual(response.status_code, 202)
        operation_id = response.json()["operation_id"]
        events = self.client.get(f"/api/v1/query/operations/{operation_id}/events")
        self.assertEqual(events.status_code, 200)
        self.assertIn("event: progress", events.text)
        self.assertIn('"phase": "PLANNING"', events.text)
        self.assertIn('"phase": "COMPLETED"', events.text)
        self.assertEqual(events.headers["content-type"].split(";", 1)[0], "text/event-stream")

    def test_dangerous_intent_and_unknown_operation_are_rejected(self) -> None:
        for question in ("drop table sales.orders", "UPDATE orders SET amount=0", "删除订单"):
            response = self.client.post("/api/v1/query/conversations", json={"question": question})
            self.assertEqual(response.status_code, 400, question)

        self.assertEqual(self.client.get("/api/v1/query/operations/op-missing").status_code, 404)

    def test_incident_and_asset_filters(self) -> None:
        incidents = self.client.get("/api/v1/incidents", params={"severity": "P1"})
        self.assertEqual(incidents.status_code, 200)
        self.assertEqual(len(incidents.json()), 1)
        self.assertEqual(self.client.get("/api/v1/incidents/not-found").status_code, 404)

        assets = self.client.get("/api/v1/assets", params={"search": "订单"})
        self.assertEqual(assets.status_code, 200)
        self.assertEqual(len(assets.json()), 2)
        self.assertEqual(self.client.get("/api/v1/assets/asset-missing").status_code, 404)

    def test_mcp_endpoint_from_environment_and_relationship_tool(self) -> None:
        endpoint = "http://tidb-mcp.test/mcp"

        async def tool_result(_endpoint, _token, _tool_map, operation, _arguments):
            self.assertEqual(_endpoint, endpoint)
            return {
                "schemas": [{"name": "sales"}],
                "tables": [{"name": "orders", "comment": "订单表"}],
                "columns": [{"name": "order_id", "data_type": "BIGINT", "comment": "订单主键"}],
                "relationships": [{"from": "sales.orders.customer_id", "to": "sales.customers.customer_id", "type": "foreign_key"}],
            }[operation]

        old_endpoint = os.environ.get("TIDB_MCP_ENDPOINT")
        os.environ["TIDB_MCP_ENDPOINT"] = endpoint
        try:
            with patch("app.main.call_mcp", side_effect=tool_result) as mocked:
                response = self.client.post("/api/v1/tidb/mcp/introspect", json={})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["source"], endpoint)
            self.assertEqual(response.json()["relationships"][0]["type"], "foreign_key")
            self.assertEqual(mocked.call_count, 4)
        finally:
            if old_endpoint is None:
                os.environ.pop("TIDB_MCP_ENDPOINT", None)
            else:
                os.environ["TIDB_MCP_ENDPOINT"] = old_endpoint
            self.client.post("/api/v1/tidb/mcp/introspect", json={"endpoint": "demo://tidb"})

    def test_csv_upload_analyze_and_directory_allowlist(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as handle:
            handle.write("day,amount,region\n2026-08-17,10,East\n2026-08-18,20,West\n")
            csv_path = Path(handle.name)

        try:
            with csv_path.open("rb") as source:
                upload = self.client.post(
                    "/api/v1/datasets/upload",
                    files={"file": ("sales.csv", source, "text/csv")},
                )
            self.assertEqual(upload.status_code, 201)
            dataset = upload.json()
            self.assertEqual(dataset["name"], "sales.csv")
            self.assertEqual(dataset["rows"], 2)
            self.assertEqual(dataset["kind"], "csv")

            analysis = self.client.post(
                "/api/v1/datasets/analyze",
                json={"question": "按天汇总金额", "dataset_ids": [dataset["id"]]},
            )
            self.assertEqual(analysis.status_code, 202)
            self.assertEqual(analysis.json()["chart"]["type"], "line")
            self.assertEqual(len(analysis.json()["rows"]), 2)

            unsupported = self.client.post(
                "/api/v1/datasets/upload",
                files={"file": ("notes.txt", b"hello", "text/plain")},
            )
            self.assertEqual(unsupported.status_code, 415)

            with tempfile.TemporaryDirectory() as allowed:
                allowed_path = Path(allowed)
                (allowed_path / "daily.csv").write_text("day,value\n2026-08-19,3\n", encoding="utf-8")
                old_roots = os.environ.get("DATASET_ALLOWED_ROOTS")
                os.environ["DATASET_ALLOWED_ROOTS"] = str(allowed_path)
                try:
                    scan = self.client.post("/api/v1/datasets/local-directory", json={"path": str(allowed_path)})
                    self.assertEqual(scan.status_code, 200)
                    self.assertEqual(len(scan.json()), 1)
                    denied = self.client.post("/api/v1/datasets/local-directory", json={"path": "/tmp"})
                    self.assertEqual(denied.status_code, 403)
                finally:
                    if old_roots is None:
                        os.environ.pop("DATASET_ALLOWED_ROOTS", None)
                    else:
                        os.environ["DATASET_ALLOWED_ROOTS"] = old_roots
        finally:
            csv_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
