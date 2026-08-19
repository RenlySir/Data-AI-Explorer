import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.agent_registry import AGENT_TEMPLATES, MODULE_AGENTS
from app.main import app
from app.model_registry import MODEL_CONNECTIONS, MODEL_SECRETS, ModelConnection
from app.product_catalog import PRODUCT_MODULES


class AgentRegistryApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        MODULE_AGENTS.clear()
        MODEL_CONNECTIONS.clear()
        MODEL_SECRETS.clear()

    def add_ready_model(self) -> ModelConnection:
        item = ModelConnection(
            id="mdl-test",
            name="企业默认模型",
            provider="custom",
            provider_name="OpenAI-Compatible",
            deployment="private",
            protocol="openai-compatible",
            base_url="http://127.0.0.1:8000/v1",
            model="enterprise-chat",
            status="ready",
            is_default=True,
            has_credential=True,
            created_at="2026-08-19T00:00:00+00:00",
        )
        MODEL_CONNECTIONS[item.id] = item
        MODEL_SECRETS[item.id] = "secret-value"
        return item

    def test_templates_follow_the_product_module_catalog(self) -> None:
        response = self.client.get("/api/v1/agents/templates")
        self.assertEqual(response.status_code, 200)
        templates = response.json()
        self.assertEqual(len(templates), len(PRODUCT_MODULES))
        self.assertEqual(
            {item["module_id"] for item in templates},
            {item.id for item in PRODUCT_MODULES},
        )
        self.assertEqual(len(AGENT_TEMPLATES), 8)
        self.assertTrue(all(item["tools"] for item in templates))
        scenario = next(item for item in templates if item["module_id"] == "scenario-command")
        self.assertEqual(scenario["approval_policy"], "human_approval")
        self.assertIn(
            "POST /api/v1/scenarios/{scenario_id}/runs",
            {item["api_ref"] for item in scenario["tools"]},
        )

    def test_provision_requires_a_verified_active_model(self) -> None:
        response = self.client.post("/api/v1/agents/provision", json={})
        self.assertEqual(response.status_code, 409)
        self.assertIn("connect and activate", response.text)

    def test_one_click_provision_is_complete_and_idempotent(self) -> None:
        self.add_ready_model()
        first = self.client.post("/api/v1/agents/provision", json={})
        self.assertEqual(first.status_code, 200, first.text)
        payload = first.json()
        self.assertEqual(payload["requested"], 8)
        self.assertEqual(len(payload["created"]), 8)
        self.assertEqual(payload["existing"], [])
        self.assertTrue(all(item["status"] == "ready" for item in payload["created"]))
        self.assertTrue(all(item["model_connection_id"] == "mdl-test" for item in payload["created"]))

        second = self.client.post("/api/v1/agents/provision", json={})
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(second.json()["created"], [])
        self.assertEqual(len(second.json()["existing"]), 8)
        self.assertEqual(len(MODULE_AGENTS), 8)

    def test_agent_can_be_disabled_enabled_and_checked(self) -> None:
        self.add_ready_model()
        created = self.client.post(
            "/api/v1/agents",
            json={"template_id": "tpl-smart-query"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        agent_id = created.json()["id"]

        disabled = self.client.put(
            f"/api/v1/agents/{agent_id}/enabled", json={"enabled": False}
        )
        self.assertEqual(disabled.status_code, 200)
        self.assertEqual(disabled.json()["status"], "disabled")
        check = self.client.post(f"/api/v1/agents/{agent_id}/test")
        self.assertEqual(check.status_code, 200)
        self.assertFalse(check.json()["passed"])

        enabled = self.client.put(
            f"/api/v1/agents/{agent_id}/enabled", json={"enabled": True}
        )
        self.assertEqual(enabled.json()["status"], "ready")
        check = self.client.post(f"/api/v1/agents/{agent_id}/test")
        self.assertTrue(check.json()["passed"])

    def test_agent_invoke_uses_bound_model_without_executing_tools(self) -> None:
        self.add_ready_model()
        created = self.client.post(
            "/api/v1/agents",
            json={"template_id": "tpl-aiops"},
        ).json()
        session = MagicMock()
        response = session.__enter__.return_value.post.return_value
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "choices": [{"message": {"content": "先核对告警证据，再提交处置审批。"}}]
        }
        with patch("app.agent_registry.httpx.Client", return_value=session):
            invoked = self.client.post(
                f"/api/v1/agents/{created['id']}/invoke",
                json={"input": "分析当前 P1 事件并给出处置建议"},
            )
        self.assertEqual(invoked.status_code, 200, invoked.text)
        self.assertEqual(invoked.json()["execution_mode"], "advisory")
        self.assertTrue(invoked.json()["approval_required"])
        self.assertIn("处置审批", invoked.json()["answer"])
        request = session.__enter__.return_value.post.call_args.kwargs["json"]
        self.assertEqual(request["model"], "enterprise-chat")
        self.assertIn("不要声称已经调用工具", request["messages"][1]["content"])
        self.assertNotIn("secret-value", invoked.text)

    def test_removing_a_bound_model_marks_agents_unavailable(self) -> None:
        model = self.add_ready_model()
        created = self.client.post(
            "/api/v1/agents",
            json={"template_id": "tpl-knowledge"},
        ).json()
        removed = self.client.delete(f"/api/v1/models/connections/{model.id}")
        self.assertEqual(removed.status_code, 204)
        agent = next(item for item in self.client.get("/api/v1/agents").json() if item["id"] == created["id"])
        self.assertEqual(agent["status"], "error")
        self.assertIn("removed", agent["last_error"])


if __name__ == "__main__":
    unittest.main()
