from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch
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
        history = self.client.get(f"/api/v1/knowledge-bases/{knowledge_base['id']}/queries")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()[0]["query_id"], payload["query_id"])
        feedback = self.client.post(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}/queries/{payload['query_id']}/feedback",
            json={"helpful": True, "comment": "引用准确"},
        )
        self.assertEqual(feedback.status_code, 201, feedback.text)
        self.assertTrue(feedback.json()["helpful"])
        invalid_feedback = self.client.post(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}/queries/kbq-missing/feedback",
            json={"helpful": False},
        )
        self.assertEqual(invalid_feedback.status_code, 404)
        invalid_limit = self.client.get(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}/queries?limit=0"
        )
        self.assertEqual(invalid_limit.status_code, 422)

    def test_document_chunks_can_be_reviewed(self) -> None:
        knowledge_base = self.create_base()
        document = self.client.post(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}/documents",
            json={
                "title": "分块检查文档",
                "content": "第一段说明变更前检查。" * 30 + "\n\n" + "第二段说明变更后验证。" * 30,
            },
        )
        self.assertEqual(document.status_code, 201, document.text)
        chunks = self.client.get(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}/documents/{document.json()['id']}/chunks"
        )
        self.assertEqual(chunks.status_code, 200, chunks.text)
        self.assertGreater(len(chunks.json()), 1)
        self.assertEqual(chunks.json()[0]["position"], 0)
        missing = self.client.get(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}/documents/doc-missing/chunks"
        )
        self.assertEqual(missing.status_code, 404)

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

    def test_hybrid_retrieval_supports_tag_filter_and_retrieval_only_mode(self) -> None:
        knowledge_base = self.create_base()
        first = self.client.post(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}/documents",
            json={
                "title": "TiDB 慢 SQL Runbook",
                "content": "发现慢 SQL 后先执行 EXPLAIN ANALYZE，检查统计信息和索引选择，再评估 TiDB 版本特性。",
                "tags": ["TiDB", "SQL"],
            },
        )
        self.assertEqual(first.status_code, 201, first.text)
        second = self.client.post(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}/documents",
            json={
                "title": "发布回滚规范",
                "content": "高风险发布需要双人审批，异常时按预案回滚并保留验证证据。",
                "tags": ["变更"],
            },
        )
        self.assertEqual(second.status_code, 201, second.text)
        result = self.client.post(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}/query",
            json={
                "question": "TiDB 慢 SQL 应该如何分析？",
                "top_k": 3,
                "tags": ["SQL"],
                "generate_answer": False,
            },
        )
        self.assertEqual(result.status_code, 200, result.text)
        payload = result.json()
        self.assertEqual(payload["generation_mode"], "retrieval-only")
        self.assertGreaterEqual(payload["candidate_count"], len(payload["citations"]))
        self.assertLessEqual(len(payload["citations"]), 3)
        self.assertTrue(payload["citations"])
        self.assertTrue(payload["citations"][0]["matched_terms"])
        self.assertIn("SQL", payload["citations"][0]["tags"])
        self.assertIn("+", payload["retrieval_mode"])
        self.assertGreaterEqual(payload["retrieval_latency_ms"], 1)

    def test_knowledge_base_exposes_splitter_provider(self) -> None:
        knowledge_base = self.create_base()
        self.assertIn(
            knowledge_base["splitter_provider"],
            {"langchain-recursive", "builtin-recursive"},
        )

    def test_index_modes_are_listed_and_settings_rebuild_chunks(self) -> None:
        modes = self.client.get("/api/v1/knowledge-bases/index-modes")
        self.assertEqual(modes.status_code, 200, modes.text)
        self.assertEqual(
            {item["id"] for item in modes.json()},
            {"lexical", "semantic", "hybrid"},
        )
        self.assertEqual(sum(item["recommended"] for item in modes.json()), 1)

        knowledge_base = self.create_base()
        document = self.client.post(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}/documents",
            json={
                "title": "需要重新分块的长文档",
                "content": ("TiDB 慢 SQL 需要检查执行计划、统计信息和索引选择。" * 80),
            },
        )
        self.assertEqual(document.status_code, 201, document.text)
        old_count = document.json()["chunk_count"]

        updated = self.client.patch(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}",
            json={
                "chunk_size": 600,
                "chunk_overlap": 80,
                "retrieval_strategy": "semantic",
            },
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        payload = updated.json()
        self.assertEqual(payload["chunk_size"], 600)
        self.assertEqual(payload["chunk_overlap"], 80)
        self.assertEqual(payload["retrieval_strategy"], "semantic")
        self.assertEqual(payload["embedding_provider"], "local-character")
        self.assertNotEqual(payload["chunk_count"], old_count)

        documents = self.client.get(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}/documents"
        ).json()
        self.assertEqual(documents[0]["id"], document.json()["id"])
        self.assertEqual(documents[0]["chunk_count"], payload["chunk_count"])
        chunks = self.client.get(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}/documents/{document.json()['id']}/chunks"
        ).json()
        self.assertEqual(len(chunks), payload["chunk_count"])

        result = self.client.post(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}/query",
            json={"question": "TiDB 慢 SQL 怎么检查？", "generate_answer": False},
        )
        self.assertEqual(result.status_code, 200, result.text)
        self.assertTrue(result.json()["retrieval_mode"].startswith("semantic+"))

    def test_settings_reject_unknown_mode_and_invalid_overlap(self) -> None:
        knowledge_base = self.create_base()
        unknown = self.client.patch(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}",
            json={"retrieval_strategy": "vector-magic"},
        )
        self.assertEqual(unknown.status_code, 422)
        invalid = self.client.patch(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}",
            json={"chunk_size": 300, "chunk_overlap": 300},
        )
        self.assertEqual(invalid.status_code, 422)

    def test_chunking_modes_and_markdown_sections_are_supported(self) -> None:
        modes = self.client.get("/api/v1/knowledge-bases/chunking-modes")
        self.assertEqual(modes.status_code, 200, modes.text)
        self.assertEqual({item["id"] for item in modes.json()}, {"recursive", "markdown"})

        knowledge_base = self.client.post(
            "/api/v1/knowledge-bases",
            json={
                "name": f"Markdown 知识库-{uuid4().hex[:8]}",
                "chunk_size": 240,
                "chunk_overlap": 20,
                "chunking_strategy": "markdown",
            },
        )
        self.assertEqual(knowledge_base.status_code, 201, knowledge_base.text)
        self.assertEqual(knowledge_base.json()["chunking_strategy"], "markdown")
        self.assertIn(knowledge_base.json()["splitter_provider"], {"langchain-markdown", "builtin-markdown"})
        document = self.client.post(
            f"/api/v1/knowledge-bases/{knowledge_base.json()['id']}/documents",
            json={
                "title": "Markdown 手册",
                "content": "# 发布准备\n检查审批和回滚预案。\n\n# 发布验证\n检查错误率和延迟。",
            },
        )
        self.assertEqual(document.status_code, 201, document.text)
        self.assertGreaterEqual(document.json()["chunk_count"], 2)

    def test_document_governance_and_score_threshold(self) -> None:
        knowledge_base = self.create_base()
        document = self.client.post(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}/documents",
            json={
                "title": "TiDB 变更手册",
                "content": "TiDB 生产变更必须完成双人审批，并准备可验证的回滚方案。",
                "tags": ["TiDB", "变更"],
            },
        )
        self.assertEqual(document.status_code, 201, document.text)
        document_id = document.json()["id"]
        self.assertTrue(document.json()["enabled"])
        self.assertIsNotNone(document.json()["indexed_at"])

        disabled = self.client.patch(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}/documents/{document_id}",
            json={"enabled": False},
        )
        self.assertEqual(disabled.status_code, 200, disabled.text)
        self.assertFalse(disabled.json()["enabled"])
        disabled_query = self.client.post(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}/query",
            json={"question": "TiDB 变更如何审批？", "score_threshold": 0},
        )
        self.assertEqual(disabled_query.status_code, 200, disabled_query.text)
        self.assertEqual(disabled_query.json()["citations"], [])

        enabled = self.client.patch(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}/documents/{document_id}",
            json={"enabled": True},
        )
        self.assertEqual(enabled.status_code, 200, enabled.text)
        strict_query = self.client.post(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}/query",
            json={"question": "TiDB 变更如何审批？", "score_threshold": 1},
        )
        self.assertEqual(strict_query.status_code, 200, strict_query.text)
        self.assertEqual(strict_query.json()["score_threshold"], 1)
        self.assertEqual(strict_query.json()["citations"], [])

        reindexed = self.client.post(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}/documents/{document_id}/reindex"
        )
        self.assertEqual(reindexed.status_code, 200, reindexed.text)
        self.assertEqual(reindexed.json()["status"], "ready")
        deleted = self.client.delete(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}/documents/{document_id}"
        )
        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.assertTrue(deleted.json()["deleted"])
        current = self.client.get(f"/api/v1/knowledge-bases/{knowledge_base['id']}")
        self.assertEqual(current.json()["document_count"], 0)
        self.assertEqual(current.json()["chunk_count"], 0)

    def test_model_answer_requires_valid_citation_and_degrades_when_invalid(self) -> None:
        knowledge_base = self.create_base()
        document = self.client.post(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}/documents",
            json={
                "title": "变更门禁",
                "content": "高风险变更需要双人审批，并在发布后观察核心指标。",
                "tags": ["变更"],
            },
        )
        self.assertEqual(document.status_code, 201, document.text)

        client = MagicMock()
        session = client.__enter__.return_value
        session.post.return_value.raise_for_status.return_value = None
        session.post.return_value.json.return_value = {
            "choices": [{"message": {"content": "高风险变更需要双人审批。[1]"}}]
        }
        with patch("app.knowledge_base.active_model_config", return_value=("http://model.local/v1", "chat", "secret")), patch(
            "app.knowledge_base.httpx.Client", return_value=client
        ):
            grounded = self.client.post(
                f"/api/v1/knowledge-bases/{knowledge_base['id']}/query",
                json={"question": "高风险变更需要什么审批？"},
            )
        self.assertEqual(grounded.status_code, 200, grounded.text)
        self.assertEqual(grounded.json()["generation_mode"], "model")
        self.assertIn("[1]", grounded.json()["answer"])

        session.post.return_value.json.return_value = {
            "choices": [{"message": {"content": "这是没有合法引用的回答。"}}]
        }
        with patch("app.knowledge_base.active_model_config", return_value=("http://model.local/v1", "chat", "secret")), patch(
            "app.knowledge_base.httpx.Client", return_value=client
        ):
            degraded = self.client.post(
                f"/api/v1/knowledge-bases/{knowledge_base['id']}/query",
                json={"question": "高风险变更需要什么审批？"},
            )
        self.assertEqual(degraded.status_code, 200, degraded.text)
        self.assertEqual(degraded.json()["generation_mode"], "extractive")
        self.assertIn("仅基于列出的知识片段", degraded.json()["answer"])


if __name__ == "__main__":
    unittest.main()
