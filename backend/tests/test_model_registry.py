import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.model_registry import MODEL_CONNECTIONS, MODEL_SECRETS, active_model_config


class ModelRegistryApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        MODEL_CONNECTIONS.clear()
        MODEL_SECRETS.clear()

    def test_provider_catalog_contains_public_and_private_options(self) -> None:
        response = self.client.get("/api/v1/models/providers")
        self.assertEqual(response.status_code, 200)
        providers = response.json()
        self.assertGreaterEqual(len(providers), 8)
        self.assertIn("public", {item["deployment"] for item in providers})
        self.assertIn("private", {item["deployment"] for item in providers})
        self.assertIn("ollama", {item["id"] for item in providers})

    def test_readiness_uses_environment_gateway_when_registry_is_empty(self) -> None:
        with patch.dict("os.environ", {"MODEL_GATEWAY_BASE_URL": "http://127.0.0.1:11434/v1", "MODEL_GATEWAY_MODEL": "local-model"}):
            response = self.client.get("/api/v1/models/readiness")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["source"], "environment")
        self.assertTrue(response.json()["ready"])

    def test_connection_test_default_and_secret_redaction(self) -> None:
        client = MagicMock()
        client.__enter__.return_value.get.return_value.raise_for_status.return_value = None
        client.__enter__.return_value.post.return_value.raise_for_status.return_value = None
        client.__enter__.return_value.post.return_value.json.return_value = {"choices": [{"message": {"content": "OK"}}]}
        with patch("app.model_registry.httpx.Client", return_value=client):
            response = self.client.post(
                "/api/v1/models/connections",
                json={
                    "name": "企业推理服务",
                    "provider": "custom",
                    "deployment": "private",
                    "base_url": "http://10.0.0.8:8000/v1",
                    "model": "enterprise-chat",
                    "api_key": "private-secret",
                    "test_on_create": True,
                    "set_default": True,
                },
            )
        self.assertEqual(response.status_code, 201, response.text)
        item = response.json()
        self.assertEqual(item["status"], "ready")
        self.assertTrue(item["is_default"])
        self.assertTrue(item["has_credential"])
        self.assertNotIn("api_key", item)
        self.assertNotIn("private-secret", response.text)
        self.assertEqual(active_model_config(), (item["base_url"], item["model"], "private-secret"))

        removed = self.client.delete(f"/api/v1/models/connections/{item['id']}")
        self.assertEqual(removed.status_code, 204)
        self.assertNotIn(item["id"], MODEL_SECRETS)

    def test_public_provider_requires_key_and_unverified_cannot_activate(self) -> None:
        missing_key = self.client.post(
            "/api/v1/models/connections",
            json={
                "name": "OpenAI",
                "provider": "openai",
                "deployment": "public",
                "base_url": "https://api.openai.com/v1",
                "model": "configured-model",
                "test_on_create": False,
            },
        )
        self.assertEqual(missing_key.status_code, 422)

        created = self.client.post(
            "/api/v1/models/connections",
            json={
                "name": "Ollama",
                "provider": "ollama",
                "deployment": "private",
                "base_url": "http://127.0.0.1:11434",
                "model": "local-model",
                "test_on_create": False,
            },
        )
        self.assertEqual(created.status_code, 201)
        activate = self.client.post(f"/api/v1/models/connections/{created.json()['id']}/activate")
        self.assertEqual(activate.status_code, 409)


if __name__ == "__main__":
    unittest.main()
