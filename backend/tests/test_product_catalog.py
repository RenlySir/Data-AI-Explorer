import unittest

from fastapi.testclient import TestClient

from app.main import app


class ProductCatalogApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_catalog_exposes_complete_operational_contract(self) -> None:
        response = self.client.get("/api/v1/product/modules")
        self.assertEqual(response.status_code, 200, response.text)
        modules = response.json()
        self.assertEqual(len(modules), 8)
        self.assertEqual(len({module["id"] for module in modules}), 8)
        features = [item for module in modules for item in module["features"]]
        self.assertGreaterEqual(len(features), 50)
        self.assertEqual(len({item["id"] for item in features}), len(features))
        self.assertTrue(
            all(
                item["roles"]
                and item["inputs"]
                and item["outputs"]
                and item["guardrails"]
                and item["action_label"]
                for item in features
            )
        )
        scenario_ids = {
            scenario_id
            for item in features
            for scenario_id in item["scenario_ids"]
        }
        self.assertEqual(
            scenario_ids,
            {
                "batch-guard",
                "incident-warroom",
                "script-repair",
                "db-health",
                "release-review",
                "release-watch",
                "data-quality",
                "smart-query-team",
                "customer-diagnosis",
                "security-response",
                "cloud-finops",
                "project-staff",
            },
        )

    def test_role_state_search_and_detail_filters(self) -> None:
        dba = self.client.get("/api/v1/product/modules", params={"role": "DBA"})
        self.assertEqual(dba.status_code, 200)
        self.assertTrue(dba.json())
        self.assertTrue(
            all("DBA" in item["roles"] for module in dba.json() for item in module["features"])
        )

        available = self.client.get(
            "/api/v1/product/modules",
            params={"state": "available", "search": "引用"},
        )
        self.assertEqual(available.status_code, 200)
        self.assertEqual(
            {item["id"] for module in available.json() for item in module["features"]},
            {"knowledge-qa"},
        )

        detail = self.client.get("/api/v1/product/features/sql-advice")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["target_page"], "sql-optimizer")
        datasource = self.client.get("/api/v1/product/features/admin-datasource")
        self.assertEqual(datasource.status_code, 200)
        self.assertEqual(datasource.json()["delivery_state"], "available")
        self.assertEqual(datasource.json()["target_page"], "datasources")
        lineage = self.client.get("/api/v1/product/features/governance-lineage")
        self.assertEqual(lineage.status_code, 200)
        self.assertEqual(lineage.json()["delivery_state"], "available")
        self.assertEqual(lineage.json()["target_page"], "catalog")
        self.assertEqual(self.client.get("/api/v1/product/features/not-found").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/product/modules?state=unknown").status_code, 422)

    def test_local_development_origin_supports_dynamic_ports(self) -> None:
        response = self.client.options(
            "/api/v1/product/modules",
            headers={
                "Origin": "http://127.0.0.1:5174",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "http://127.0.0.1:5174",
        )


if __name__ == "__main__":
    unittest.main()
