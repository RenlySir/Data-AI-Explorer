import unittest

from fastapi.testclient import TestClient

from app.chatbi import DASHBOARD_REPORTS, DATA_SOURCES, DATA_SOURCE_SECRETS
from app.main import DATASETS, OPERATIONS, app


class ChatBIApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        demo = DATA_SOURCES["ds-demo-tidb"]
        DATA_SOURCES.clear()
        DATA_SOURCES[demo.id] = demo
        DATA_SOURCE_SECRETS.clear()
        DASHBOARD_REPORTS.clear()
        DATASETS.clear()
        OPERATIONS.clear()

    def test_csv_datasource_query_and_dashboard_flow(self) -> None:
        upload = self.client.post(
            "/api/v1/chatbi/datasources/upload",
            files={"file": ("sales.csv", b"day,gmv\n2026-08-17,10\n2026-08-18,20\n", "text/csv")},
        )
        self.assertEqual(upload.status_code, 201, upload.text)
        datasource = upload.json()
        self.assertEqual(datasource["kind"], "csv")
        self.assertEqual(datasource["status"], "ready")
        self.assertEqual(datasource["row_count"], 2)

        analysis = self.client.post(
            "/api/v1/chatbi/query",
            json={"datasource_id": datasource["id"], "question": "按日查看 GMV 趋势"},
        )
        self.assertEqual(analysis.status_code, 202, analysis.text)
        operation = analysis.json()
        self.assertEqual(operation["chart"]["type"], "line")
        self.assertEqual(operation["evidence"][0]["ref"], datasource["id"])
        self.assertEqual(len(operation["rows"]), 2)

        report = self.client.post(
            "/api/v1/chatbi/reports",
            json={"operation_id": operation["operation_id"], "datasource_id": datasource["id"], "title": "GMV 趋势"},
        )
        self.assertEqual(report.status_code, 201, report.text)
        self.assertEqual(report.json()["chart"]["type"], "line")
        mismatched = self.client.post(
            "/api/v1/chatbi/reports",
            json={"operation_id": operation["operation_id"], "datasource_id": "ds-demo-tidb", "title": "错误归属"},
        )
        self.assertEqual(mismatched.status_code, 409)
        listed = self.client.get("/api/v1/chatbi/reports")
        self.assertEqual(len(listed.json()), 1)
        removed = self.client.delete(f"/api/v1/chatbi/reports/{report.json()['id']}")
        self.assertEqual(removed.status_code, 204)
        self.assertEqual(self.client.get("/api/v1/chatbi/reports").json(), [])

    def test_database_credentials_never_appear_in_response(self) -> None:
        response = self.client.post(
            "/api/v1/chatbi/datasources",
            json={
                "name": "分析库",
                "kind": "tidb",
                "host": "10.0.0.8",
                "port": 4000,
                "database": "analytics",
                "username": "reader",
                "password": "secret-value",
                "test_on_create": False,
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        datasource = response.json()
        self.assertNotIn("password", datasource)
        self.assertNotIn("secret-value", response.text)
        self.assertEqual(DATA_SOURCE_SECRETS[datasource["id"]], "secret-value")
        deleted = self.client.delete(f"/api/v1/chatbi/datasources/{datasource['id']}")
        self.assertEqual(deleted.status_code, 204)
        self.assertNotIn(datasource["id"], DATA_SOURCE_SECRETS)

    def test_invalid_sources_and_write_intent_are_rejected(self) -> None:
        missing = self.client.post("/api/v1/chatbi/query", json={"datasource_id": "missing", "question": "销售额"})
        self.assertEqual(missing.status_code, 404)
        blocked = self.client.post(
            "/api/v1/chatbi/query",
            json={"datasource_id": "ds-demo-tidb", "question": "删除订单表"},
        )
        self.assertEqual(blocked.status_code, 400)
        self.assertEqual(self.client.delete("/api/v1/chatbi/datasources/ds-demo-tidb").status_code, 400)


if __name__ == "__main__":
    unittest.main()
