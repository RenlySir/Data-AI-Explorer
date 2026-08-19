from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


class KnowledgeBaseApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def create_base(self, name: str | None = None) -> dict:
        response = self.client.post(
            "/api/v1/knowledge-bases",
            json={
                "name": name or f"测试知识库-{uuid4().hex[:8]}",
                "description": "知识库接口自动化测试",
                "chunk_size": 240,
                "chunk_overlap": 40,
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_demo_library_and_documents_are_available(self) -> None:
        response = self.client.get("/api/v1/knowledge-bases")
        self.assertEqual(response.status_code, 200)
        demo = next(item for item in response.json() if item["id"] == "kb-enterprise-ops")
        self.assertEqual(demo["document_count"], 3)
        documents = self.client.get(f"/api/v1/knowledge-bases/{demo['id']}/documents")
        self.assertEqual(documents.status_code, 200)
        self.assertEqual(len(documents.json()), 3)

    def test_add_document_and_grounded_query_return_citations(self) -> None:
        knowledge_base = self.create_base()
        document = self.client.post(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}/documents",
            json={
                "title": "订单系统应急预案",
                "content": "订单服务错误率超过百分之五时，应停止发布并切换到上一稳定版本。值班负责人完成回滚后，需要核验错误率和订单成功率。",
                "tags": ["订单", "回滚"],
            },
        )
        self.assertEqual(document.status_code, 201, document.text)
        result = self.client.post(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}/query",
            json={"question": "订单错误率过高时如何回滚？", "top_k": 3},
        )
        self.assertEqual(result.status_code, 200, result.text)
        payload = result.json()
        self.assertTrue(payload["citations"])
        self.assertEqual(payload["citations"][0]["document_title"], "订单系统应急预案")
        self.assertIn("仅基于列出的知识片段", payload["answer"])

    def test_upload_accepts_supported_text_and_rejects_binary_type(self) -> None:
        knowledge_base = self.create_base()
        uploaded = self.client.post(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}/documents/upload",
            files=[("files", ("runbook.md", "# 值班规范\n告警必须记录处置证据。", "text/markdown"))],
        )
        self.assertEqual(uploaded.status_code, 201, uploaded.text)
        self.assertEqual(uploaded.json()[0]["source_type"], "upload")
        rejected = self.client.post(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}/documents/upload",
            files=[("files", ("secret.exe", b"binary", "application/octet-stream"))],
        )
        self.assertEqual(rejected.status_code, 415)

    def test_local_directory_respects_allowlist_and_ignores_symlinks(self) -> None:
        knowledge_base = self.create_base()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "guide.txt").write_text("数据补数完成后必须重新执行质量规则。", encoding="utf-8")
            old_roots = os.environ.get("DATASET_ALLOWED_ROOTS")
            os.environ["DATASET_ALLOWED_ROOTS"] = str(root)
            try:
                response = self.client.post(
                    f"/api/v1/knowledge-bases/{knowledge_base['id']}/documents/local-directory",
                    json={"path": str(root), "tags": ["质量"]},
                )
                self.assertEqual(response.status_code, 201, response.text)
                self.assertEqual(len(response.json()), 1)
                denied = self.client.post(
                    f"/api/v1/knowledge-bases/{knowledge_base['id']}/documents/local-directory",
                    json={"path": "/tmp"},
                )
                self.assertEqual(denied.status_code, 403)
            finally:
                if old_roots is None:
                    os.environ.pop("DATASET_ALLOWED_ROOTS", None)
                else:
                    os.environ["DATASET_ALLOWED_ROOTS"] = old_roots

    def test_empty_library_answer_and_validation_errors_are_explicit(self) -> None:
        knowledge_base = self.create_base()
        result = self.client.post(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}/query",
            json={"question": "没有资料时怎么回答"},
        )
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["confidence"], "low")
        self.assertEqual(result.json()["citations"], [])
        invalid = self.client.post(
            "/api/v1/knowledge-bases",
            json={"name": "非法分块", "chunk_size": 200, "chunk_overlap": 200},
        )
        self.assertEqual(invalid.status_code, 422)
        missing = self.client.get("/api/v1/knowledge-bases/kb-missing/documents")
        self.assertEqual(missing.status_code, 404)


if __name__ == "__main__":
    unittest.main()
