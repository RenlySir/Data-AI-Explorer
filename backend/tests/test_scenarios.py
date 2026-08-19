import unittest

from fastapi.testclient import TestClient

from app.main import app


class ScenarioApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_catalog_contains_all_document_scenarios(self) -> None:
        response = self.client.get("/api/v1/scenarios")
        self.assertEqual(response.status_code, 200)
        items = response.json()
        self.assertEqual(len(items), 12)
        self.assertIn("夜间跑批值守与自动恢复", [item["name"] for item in items])
        self.assertIn("企业智能问数交付团队", [item["name"] for item in items])
        self.assertTrue(all(item["agents"] and item["steps"] for item in items))

    def test_run_advances_and_high_risk_requires_approval(self) -> None:
        created = self.client.post(
            "/api/v1/scenarios/script-repair/runs",
            json={"objective": "修复今晚订单同步脚本失败", "context": "预发布环境"},
        )
        self.assertEqual(created.status_code, 201)
        run = created.json()
        self.assertEqual(run["status"], "running")
        run_id = run["run_id"]

        for _ in range(4):
            advanced = self.client.post(f"/api/v1/scenario-runs/{run_id}/advance")
            self.assertEqual(advanced.status_code, 200)
        waiting = advanced.json()
        self.assertEqual(waiting["status"], "waiting_approval")
        self.assertEqual(waiting["steps"][3]["status"], "waiting_approval")
        self.assertEqual(self.client.post(f"/api/v1/scenario-runs/{run_id}/advance").status_code, 409)

        approved = self.client.post(f"/api/v1/scenario-runs/{run_id}/approve")
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.json()["status"], "running")
        self.assertEqual(approved.json()["approvals_granted"], 1)

        completed = self.client.post(f"/api/v1/scenario-runs/{run_id}/advance")
        self.assertEqual(completed.status_code, 200)
        self.assertEqual(completed.json()["status"], "running")
        release_gate = self.client.post(f"/api/v1/scenario-runs/{run_id}/advance")
        self.assertEqual(release_gate.status_code, 200)
        self.assertEqual(release_gate.json()["status"], "waiting_approval")
        self.assertEqual(self.client.post(f"/api/v1/scenario-runs/{run_id}/approve").status_code, 200)
        finished = self.client.post(f"/api/v1/scenario-runs/{run_id}/advance")
        self.assertEqual(finished.status_code, 200)
        self.assertEqual(finished.json()["status"], "completed")
        self.assertEqual(finished.json()["approvals_granted"], 2)

    def test_filters_and_missing_resources(self) -> None:
        response = self.client.get("/api/v1/scenarios", params={"category": "安全治理"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()], ["security-response"])
        self.assertEqual(self.client.get("/api/v1/scenarios/not-found").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/scenario-runs/not-found").status_code, 404)


if __name__ == "__main__":
    unittest.main()
