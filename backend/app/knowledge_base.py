from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


KnowledgeStatus = Literal["ready", "processing", "failed"]
SourceType = Literal["text", "upload", "local_directory", "connector"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(default="", max_length=500)
    scope: str = Field(default="workspace", max_length=40)
    embedding_provider: str = Field(default="local-keyword", max_length=80)
    retrieval_strategy: str = Field(default="lexical", max_length=40)
    chunk_size: int = Field(default=800, ge=200, le=4000)
    chunk_overlap: int = Field(default=120, ge=0, le=1000)


class KnowledgeBaseRecord(BaseModel):
    id: str
    name: str
    description: str
    scope: str
    embedding_provider: str
    retrieval_strategy: str
    chunk_size: int
    chunk_overlap: int
    document_count: int = 0
    chunk_count: int = 0
    created_at: str
    updated_at: str


class KnowledgeDocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    content: str = Field(min_length=1, max_length=4_000_000)
    source_type: SourceType = "text"
    source_uri: str = Field(default="manual://text", max_length=2048)
    tags: list[str] = Field(default_factory=list, max_length=20)
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeDocument(BaseModel):
    id: str
    knowledge_base_id: str
    title: str
    source_type: SourceType
    source_uri: str
    mime_type: str
    content_size: int
    status: KnowledgeStatus
    chunk_count: int
    tags: list[str]
    metadata: dict[str, Any]
    created_at: str
    updated_at: str


class KnowledgeChunk(BaseModel):
    id: str
    knowledge_base_id: str
    document_id: str
    position: int
    text: str
    token_count: int
    metadata: dict[str, Any]


class KnowledgeQuery(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class KnowledgeCitation(BaseModel):
    rank: int
    document_id: str
    document_title: str
    chunk_id: str
    score: float
    excerpt: str
    source_uri: str
    tags: list[str]


class KnowledgeQueryResult(BaseModel):
    query_id: str
    knowledge_base_id: str
    question: str
    answer: str
    confidence: Literal["low", "medium", "high"]
    retrieval_mode: str
    citations: list[KnowledgeCitation]
    generated_at: str


KNOWLEDGE_BASES: dict[str, KnowledgeBaseRecord] = {}
KNOWLEDGE_DOCUMENTS: dict[str, KnowledgeDocument] = {}
KNOWLEDGE_CHUNKS: dict[str, KnowledgeChunk] = {}


def _normalize_text(content: str) -> str:
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    content = re.sub(r"[ \t]+", " ", content)
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content.strip()


def _split_text(content: str, chunk_size: int, overlap: int) -> list[str]:
    content = _normalize_text(content)
    if not content:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(content):
        hard_end = min(len(content), start + chunk_size)
        end = hard_end
        if hard_end < len(content):
            candidates = [
                content.rfind("\n\n", start, hard_end),
                content.rfind("。", start, hard_end),
                content.rfind(". ", start, hard_end),
            ]
            boundary = max(candidates)
            if boundary > start + chunk_size // 2:
                end = boundary + (1 if content[boundary] == "。" else 0)
        text = content[start:end].strip()
        if text:
            chunks.append(text)
        if end >= len(content):
            break
        next_start = max(start + 1, end - overlap)
        start = next_start
    return chunks


def _tokens(text: str) -> set[str]:
    lowered = text.lower()
    tokens = set(re.findall(r"[a-z0-9_]{2,}", lowered))
    chinese_runs = re.findall(r"[\u4e00-\u9fff]+", lowered)
    for run in chinese_runs:
        tokens.update(run)
        tokens.update(run[index : index + 2] for index in range(max(0, len(run) - 1)))
    return tokens


def _score(question: str, title: str, tags: list[str], text: str) -> float:
    query_tokens = _tokens(question)
    if not query_tokens:
        return 0.0
    text_tokens = _tokens(text)
    overlap = query_tokens & text_tokens
    if not overlap:
        return 0.0
    base = len(overlap) / math.sqrt(max(1, len(query_tokens) * len(text_tokens)))
    title_overlap = len(query_tokens & _tokens(title)) / len(query_tokens)
    tag_overlap = len(query_tokens & _tokens(" ".join(tags))) / len(query_tokens)
    phrase_bonus = 0.2 if question.strip().lower() in text.lower() else 0.0
    return round(min(1.0, base * 2.4 + title_overlap * 0.35 + tag_overlap * 0.2 + phrase_bonus), 4)


def create_knowledge_base(payload: KnowledgeBaseCreate, *, record_id: str | None = None) -> KnowledgeBaseRecord:
    if payload.chunk_overlap >= payload.chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")
    timestamp = now_iso()
    record = KnowledgeBaseRecord(
        id=record_id or f"kb-{uuid4().hex[:10]}",
        created_at=timestamp,
        updated_at=timestamp,
        **payload.model_dump(),
    )
    KNOWLEDGE_BASES[record.id] = record
    return record


def add_document(
    knowledge_base_id: str,
    payload: KnowledgeDocumentCreate,
    *,
    mime_type: str = "text/plain",
    document_id: str | None = None,
) -> KnowledgeDocument:
    knowledge_base = KNOWLEDGE_BASES.get(knowledge_base_id)
    if not knowledge_base:
        raise KeyError(knowledge_base_id)
    content = _normalize_text(payload.content)
    if not content:
        raise ValueError("document content is empty")
    texts = _split_text(content, knowledge_base.chunk_size, knowledge_base.chunk_overlap)
    if not texts:
        raise ValueError("document did not produce any chunks")
    timestamp = now_iso()
    doc_id = document_id or f"doc-{uuid4().hex[:10]}"
    document = KnowledgeDocument(
        id=doc_id,
        knowledge_base_id=knowledge_base_id,
        title=payload.title,
        source_type=payload.source_type,
        source_uri=payload.source_uri,
        mime_type=mime_type,
        content_size=len(content.encode("utf-8")),
        status="ready",
        chunk_count=len(texts),
        tags=payload.tags,
        metadata=payload.metadata,
        created_at=timestamp,
        updated_at=timestamp,
    )
    KNOWLEDGE_DOCUMENTS[doc_id] = document
    for position, text in enumerate(texts):
        chunk_id = f"chunk-{uuid4().hex[:12]}"
        KNOWLEDGE_CHUNKS[chunk_id] = KnowledgeChunk(
            id=chunk_id,
            knowledge_base_id=knowledge_base_id,
            document_id=doc_id,
            position=position,
            text=text,
            token_count=len(_tokens(text)),
            metadata={"title": payload.title, "source_uri": payload.source_uri, **payload.metadata},
        )
    knowledge_base.document_count += 1
    knowledge_base.chunk_count += len(texts)
    knowledge_base.updated_at = timestamp
    return document


def list_documents(knowledge_base_id: str) -> list[KnowledgeDocument]:
    if knowledge_base_id not in KNOWLEDGE_BASES:
        raise KeyError(knowledge_base_id)
    return [
        document
        for document in reversed(list(KNOWLEDGE_DOCUMENTS.values()))
        if document.knowledge_base_id == knowledge_base_id
    ]


def query_knowledge_base(knowledge_base_id: str, payload: KnowledgeQuery) -> KnowledgeQueryResult:
    knowledge_base = KNOWLEDGE_BASES.get(knowledge_base_id)
    if not knowledge_base:
        raise KeyError(knowledge_base_id)
    ranked: list[tuple[float, KnowledgeChunk, KnowledgeDocument]] = []
    for chunk in KNOWLEDGE_CHUNKS.values():
        if chunk.knowledge_base_id != knowledge_base_id:
            continue
        document = KNOWLEDGE_DOCUMENTS[chunk.document_id]
        score = _score(payload.question, document.title, document.tags, chunk.text)
        if score > 0:
            ranked.append((score, chunk, document))
    ranked.sort(key=lambda item: (-item[0], item[1].position))
    if ranked:
        minimum_score = max(0.15, ranked[0][0] * 0.25)
        ranked = [item for item in ranked if item[0] >= minimum_score]
    citations = [
        KnowledgeCitation(
            rank=index,
            document_id=document.id,
            document_title=document.title,
            chunk_id=chunk.id,
            score=score,
            excerpt=chunk.text[:600],
            source_uri=document.source_uri,
            tags=document.tags,
        )
        for index, (score, chunk, document) in enumerate(ranked[: payload.top_k], start=1)
    ]
    if citations:
        evidence = "\n".join(f"[{item.rank}] {item.excerpt}" for item in citations[:3])
        answer = f"根据知识库检索到的内容：\n{evidence}\n\n以上结论仅基于列出的知识片段，请通过引用核验原文。"
        confidence: Literal["low", "medium", "high"] = "high" if citations[0].score >= 0.72 else "medium"
    else:
        answer = "当前知识库中没有检索到足够相关的内容。请补充资料、调整关键词，或选择其他知识库后重试。"
        confidence = "low"
    return KnowledgeQueryResult(
        query_id=f"kbq-{uuid4().hex[:10]}",
        knowledge_base_id=knowledge_base_id,
        question=payload.question,
        answer=answer,
        confidence=confidence,
        retrieval_mode=knowledge_base.retrieval_strategy,
        citations=citations,
        generated_at=now_iso(),
    )


def _bootstrap_demo() -> None:
    if KNOWLEDGE_BASES:
        return
    knowledge_base = create_knowledge_base(
        KnowledgeBaseCreate(
            name="企业运营知识库",
            description="汇集生产变更、TiDB 运维和数据质量规范，供本地 RAG 演示与引用核验。",
        ),
        record_id="kb-enterprise-ops",
    )
    demo_documents = [
        (
            "生产变更与回滚规范",
            "生产变更必须先完成风险评审，并明确负责人、影响范围和回滚条件。高风险变更需要双人审批。发布后应至少观察三十分钟，持续检查错误率、延迟和核心业务指标；指标异常时立即停止扩容或发布，并按预案回滚。",
            ["变更", "审批", "回滚"],
        ),
        (
            "TiDB 日常巡检手册",
            "TiDB 每日巡检应检查集群健康、Region 分布、磁盘容量、连接数、慢 SQL、锁等待和备份任务。发现慢 SQL 时先使用 EXPLAIN ANALYZE 核对执行计划，再检查统计信息、索引选择、执行算子和 TiDB 版本特性，禁止直接在生产执行未经审核的 DDL。",
            ["TiDB", "巡检", "SQL"],
        ),
        (
            "数据质量异常处理规范",
            "数据质量告警发生后，先确认规则、异常分区和影响表，再沿字段血缘定位上游任务和数据源。修复前需要保存证据并评估下游报表影响；补数完成后重新执行质量规则，记录修复范围、验证结果和责任人。",
            ["数据质量", "血缘", "补数"],
        ),
    ]
    for index, (title, content, tags) in enumerate(demo_documents, start=1):
        add_document(
            knowledge_base.id,
            KnowledgeDocumentCreate(
                title=title,
                content=content,
                source_type="connector",
                source_uri=f"demo://enterprise-handbook/{index}",
                tags=tags,
            ),
            document_id=f"doc-enterprise-{index}",
        )


_bootstrap_demo()
