from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import tempfile
import threading
from decimal import Decimal
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.product_catalog import (
    PRODUCT_FEATURES,
    DeliveryState,
    ProductFeature,
    ProductModule,
    list_modules,
)
from app.sql_optimizer import (
    ALLOWED_SQL_SUFFIXES,
    MAX_INPUT_BYTES,
    SQLOptimizeRequest,
    SQLOptimizeResponse,
    SQLDirectoryRequest,
    SQLInputBundle,
    TIDB_PROFILES,
    analyze_sql,
    bundle_from_files,
    normalize_version,
    version_matches,
)
from app.scenario_catalog import (
    SCENARIO_BY_ID,
    SCENARIO_RUNS,
    SCENARIO_TEMPLATES,
    ScenarioRun,
    ScenarioRunCreate,
    now_iso as scenario_now_iso,
    new_run,
)
from app.knowledge_base import (
    KNOWLEDGE_BASES,
    KnowledgeBaseCreate,
    KnowledgeBaseRecord,
    KnowledgeBaseUpdate,
    KnowledgeChunkingMode,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeDocumentCreate,
    KnowledgeDocumentUpdate,
    KnowledgeFeedback,
    KnowledgeFeedbackCreate,
    KnowledgeQuery,
    KnowledgeQueryResult,
    KnowledgeIndexMode,
    KNOWLEDGE_INDEX_MODES,
    KNOWLEDGE_CHUNKING_MODES,
    add_feedback,
    add_document,
    create_knowledge_base,
    delete_document,
    list_document_chunks,
    list_documents,
    list_queries,
    query_knowledge_base,
    reindex_document,
    update_document,
    update_knowledge_base,
)
from app.chatbi import (
    ChatBIQuery,
    DASHBOARD_REPORTS,
    DATA_SOURCES,
    DATA_SOURCE_SECRETS,
    DataSourceCreate,
    DataSourceRecord,
    DashboardReport,
    ReportCreate,
    create_csv_source,
    create_database_source,
    collect_recent_sql,
    execute_database_select,
    inspect_database,
    inspect_database_relationships,
    test_database_source,
)
from app.data_relationships import (
    RelationshipSnapshot,
    SqlCollectorStatus,
    SqlCollectorUpdate,
    SqlObservationRecord,
    SqlObservationRequest,
    build_snapshot,
    clear_datasource_relationships,
    ingest_sql,
)
from app.model_registry import (
    MODEL_CONNECTIONS,
    MODEL_SECRETS,
    PROVIDERS,
    ModelConnection,
    ModelConnectionCreate,
    ModelProvider,
    active_model_config,
    create_connection,
    set_default_connection,
    test_connection,
)
from app.agent_registry import (
    AGENT_TEMPLATES,
    MODULE_AGENTS,
    AgentCreate,
    AgentEnabledUpdate,
    AgentInvokeRequest,
    AgentInvokeResult,
    AgentProvisionRequest,
    AgentProvisionResult,
    AgentTemplate,
    AgentTestResult,
    ModuleAgent,
    create_agent,
    invoke_agent,
    mark_model_unavailable,
    provision_agents,
    set_agent_enabled,
    test_agent,
)
from app.platform_store import load_settings, record_audit, save_settings, ensure_schema as ensure_platform_schema


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    datasource_id: str = "demo-warehouse"
    source_type: str = "tidb"
    dataset_ids: list[str] = Field(default_factory=list)
    mcp_endpoint: str | None = None


class QueryOperation(BaseModel):
    operation_id: str
    status: str
    question: str
    sql: str | None = None
    answer: str | None = None
    columns: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)
    evidence: list[dict[str, str]] = Field(default_factory=list)
    chart: dict[str, Any] | None = None
    created_at: str


class Incident(BaseModel):
    id: str
    title: str
    severity: str
    status: str
    service: str
    started_at: str
    summary: str
    recommended_action: str


class Asset(BaseModel):
    id: str
    name: str
    type: str
    owner: str
    status: str
    database: str
    description: str
    columns: list[dict[str, str]]
    upstream: list[str]
    downstream: list[str]
    row_count: int | None = None
    quality_score: float | None = None


class WorkspaceSettings(BaseModel):
    workspace_name: str = Field(default="本地演示空间", min_length=1, max_length=120)
    language: str = Field(default="zh-CN", min_length=2, max_length=20)
    timezone: str = Field(default="Asia/Shanghai", min_length=1, max_length=64)
    data_retention_days: int = Field(default=90, ge=1, le=3650)
    tidb_mcp_endpoint: str = Field(default="demo://tidb", max_length=2048)
    allowed_data_root: str = Field(default="/workspace/data", max_length=2048)
    readonly_sql: bool = True
    operation_audit: bool = True
    high_risk_approval: bool = True
    local_models_only: bool = False
    updated_at: str = ""


class WorkspaceSettingsUpdate(BaseModel):
    workspace_name: str | None = Field(default=None, min_length=1, max_length=120)
    language: str | None = Field(default=None, min_length=2, max_length=20)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    data_retention_days: int | None = Field(default=None, ge=1, le=3650)
    tidb_mcp_endpoint: str | None = Field(default=None, max_length=2048)
    allowed_data_root: str | None = Field(default=None, max_length=2048)
    readonly_sql: bool | None = None
    operation_audit: bool | None = None
    high_risk_approval: bool | None = None
    local_models_only: bool | None = None


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=160)
    password: str = Field(min_length=1, max_length=256)


class LogoutRequest(BaseModel):
    session_id: str | None = None


class IncidentReadRequest(BaseModel):
    incident_ids: list[str] = Field(default_factory=list, max_length=100)


class GovernanceTaskRequest(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    asset_id: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=2000)


class GovernanceTask(BaseModel):
    task_id: str
    asset_id: str
    title: str
    description: str
    status: str
    created_at: str


class TidbMcpIntrospectRequest(BaseModel):
    endpoint: str | None = Field(default=None, min_length=1, max_length=2048)
    token: str | None = Field(default=None, max_length=4096)
    database: str | None = None
    tool_map: dict[str, str] = Field(default_factory=dict)


class DatasetAnalyzeRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    dataset_ids: list[str] = Field(min_length=1, max_length=20)


class LocalDirectoryRequest(BaseModel):
    path: str = Field(min_length=1, max_length=1024)


class KnowledgeDirectoryRequest(BaseModel):
    path: str = Field(min_length=1, max_length=1024)
    tags: list[str] = Field(default_factory=list, max_length=20)


class Dataset(BaseModel):
    id: str
    name: str
    kind: str
    path: str
    rows: int
    columns: list[dict[str, str]]
    created_at: str


class CatalogColumn(BaseModel):
    name: str
    data_type: str
    comment: str | None = None
    nullable: bool = True


class CatalogTable(BaseModel):
    name: str
    comment: str | None = None
    columns: list[CatalogColumn] = Field(default_factory=list)


class CatalogSchema(BaseModel):
    name: str
    tables: list[CatalogTable] = Field(default_factory=list)


class TidbCatalog(BaseModel):
    database: str
    schemas: list[CatalogSchema] = Field(default_factory=list)
    relationships: list[dict[str, str]] = Field(default_factory=list)
    source: str
    collected_at: str


INCIDENTS = [
    Incident(id="inc-1001", title="订单同步延迟超过阈值", severity="P1", status="investigating", service="order-sync", started_at="2026-08-19T08:42:00+08:00", summary="Kafka consumer lag持续增长，影响近30分钟订单入仓。", recommended_action="扩容 consumer 并重启卡住的分区任务。"),
    Incident(id="inc-1002", title="报表任务运行失败", severity="P2", status="open", service="bi-scheduler", started_at="2026-08-19T07:15:00+08:00", summary="daily_sales 聚合任务因源表字段变更失败。", recommended_action="检查字段兼容性并重新执行任务。"),
    Incident(id="inc-0998", title="API 错误率恢复", severity="P3", status="resolved", service="customer-api", started_at="2026-08-18T21:08:00+08:00", summary="连接池耗尽导致短时 5xx，已自动恢复。", recommended_action="复盘连接池上限并补充容量告警。"),
]

ASSETS = [
    Asset(id="asset-orders", name="dwd_orders", type="table", owner="数据平台组", status="certified", database="warehouse", description="订单明细事实表，供经营分析和履约监控使用。", columns=[{"name": "order_id", "type": "bigint", "sensitivity": "internal"}, {"name": "customer_id", "type": "bigint", "sensitivity": "restricted"}, {"name": "amount", "type": "decimal", "sensitivity": "internal"}], upstream=["ods_orders"], downstream=["ads_sales_daily", "rpt_order_fulfillment"], row_count=128400000, quality_score=98),
    Asset(id="asset-sales", name="ads_sales_daily", type="table", owner="经营分析组", status="certified", database="warehouse", description="按日汇总销售指标宽表。", columns=[{"name": "stat_date", "type": "date", "sensitivity": "public"}, {"name": "gmv", "type": "decimal", "sensitivity": "internal"}], upstream=["dwd_orders"], downstream=["dashboard_sales"], row_count=4800000, quality_score=94),
    Asset(id="asset-order-sync", name="order_sync_lag", type="metric", owner="SRE", status="active", database="observability", description="订单同步 Kafka consumer lag 指标。", columns=[{"name": "value", "type": "gauge", "sensitivity": "internal"}], upstream=[], downstream=["inc-1001"], row_count=None, quality_score=91),
]

DEMO_CATALOG = TidbCatalog(
    database="demo_tidb",
    source="demo",
    collected_at=now_iso(),
    schemas=[
        CatalogSchema(name="sales", tables=[
            CatalogTable(name="orders", comment="订单主表", columns=[CatalogColumn(name="order_id", data_type="BIGINT", comment="订单唯一标识", nullable=False), CatalogColumn(name="customer_id", data_type="BIGINT", comment="客户标识"), CatalogColumn(name="amount", data_type="DECIMAL(18,2)", comment="订单金额"), CatalogColumn(name="created_at", data_type="DATETIME", comment="下单时间")]),
            CatalogTable(name="customers", comment="客户维表", columns=[CatalogColumn(name="customer_id", data_type="BIGINT", comment="客户唯一标识", nullable=False), CatalogColumn(name="region", data_type="VARCHAR(64)", comment="客户所属区域")]),
        ]),
        CatalogSchema(name="reporting", tables=[CatalogTable(name="daily_sales", comment="日销售汇总", columns=[CatalogColumn(name="stat_date", data_type="DATE", comment="统计日期"), CatalogColumn(name="gmv", data_type="DECIMAL(18,2)", comment="日 GMV")])]),
    ],
    relationships=[{"from": "sales.orders.customer_id", "to": "sales.customers.customer_id", "type": "foreign_key"}, {"from": "sales.orders", "to": "reporting.daily_sales", "type": "derived"}],
)

OPERATIONS: dict[str, QueryOperation] = {}
CATALOG: TidbCatalog = DEMO_CATALOG
MCP_CONNECTION: TidbMcpIntrospectRequest | None = None
DATASETS: dict[str, Dataset] = {}
RELATIONSHIP_CATALOGS: dict[str, TidbCatalog] = {}
SQL_COLLECTOR_STATUS: dict[str, SqlCollectorStatus] = {}
SQL_COLLECTOR_STOPS: dict[str, threading.Event] = {}
GOVERNANCE_TASKS: dict[str, GovernanceTask] = {}
DATASET_DIR = Path(os.getenv("DATASET_STORAGE_DIR", tempfile.gettempdir() + "/aegis-datasets"))
DATASET_DIR.mkdir(parents=True, exist_ok=True)

KNOWLEDGE_ALLOWED_SUFFIXES = {".txt", ".md", ".markdown", ".html", ".htm", ".json", ".sql", ".ddl"}
KNOWLEDGE_MAX_FILE_BYTES = 4 * 1024 * 1024

DEFAULT_WORKSPACE_SETTINGS = WorkspaceSettings(updated_at=now_iso())
WORKSPACE_SETTINGS = DEFAULT_WORKSPACE_SETTINGS

app = FastAPI(title="Data AI Explorer API", version="0.2.0", description="企业 AI 落地平台的智能问数和数据目录 API")
CORS_ALLOW_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
    if origin.strip()
]
CORS_ALLOW_LOCALHOST = os.getenv("CORS_ALLOW_LOCALHOST", "true").lower() in {"1", "true", "yes"}
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_origin_regex=r"^https?://(?:localhost|127\.0\.0\.1)(?::\d+)?$" if CORS_ALLOW_LOCALHOST else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REQUEST_METRICS = {"requests": 0, "errors": 0}


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or f"req-{uuid4().hex[:16]}"
    REQUEST_METRICS["requests"] += 1
    response = await call_next(request)
    if response.status_code >= 500:
        REQUEST_METRICS["errors"] += 1
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.get("/metrics", include_in_schema=False, response_class=PlainTextResponse)
def metrics() -> str:
    return "\n".join(
        (
            "# HELP aegis_http_requests_total Total HTTP requests handled by the API.",
            "# TYPE aegis_http_requests_total counter",
            f"aegis_http_requests_total {REQUEST_METRICS['requests']}",
            "# HELP aegis_http_errors_total Total HTTP 5xx responses emitted by the API.",
            "# TYPE aegis_http_errors_total counter",
            f"aegis_http_errors_total {REQUEST_METRICS['errors']}",
            f"aegis_active_operations {len(OPERATIONS)}",
        )
    ) + "\n"


@app.on_event("startup")
def initialize_platform_store() -> None:
    global WORKSPACE_SETTINGS
    try:
        ensure_platform_schema()
        stored = load_settings()
        if stored:
            WORKSPACE_SETTINGS = WorkspaceSettings.model_validate(stored)
    except Exception:
        # The application remains usable in demo mode if the optional TiDB
        # metadata schema is temporarily unavailable.
        WORKSPACE_SETTINGS = DEFAULT_WORKSPACE_SETTINGS


def chart_spec(columns: list[str], rows: list[list[Any]], title: str) -> dict[str, Any]:
    if not columns or not rows:
        return {"type": "table", "title": title, "option": {}}
    x = columns[0]
    numeric_index = next((i for i, name in enumerate(columns[1:], start=1) if any(isinstance(row[i], (int, float)) for row in rows)), 1 if len(columns) > 1 else 0)
    y = columns[numeric_index]
    return {"type": "line", "title": title, "xField": x, "yField": y, "option": {"xAxis": {"type": "category", "data": [row[0] for row in rows]}, "yAxis": {"type": "value"}, "series": [{"type": "line", "smooth": True, "data": [row[numeric_index] for row in rows]}]}}


def model_chat_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    return base + "/chat/completions" if base.endswith(("/v1", "/v4")) else base + "/v1/chat/completions"


async def chatbi_chart_spec(question: str, columns: list[str], rows: list[list[Any]]) -> dict[str, Any]:
    """Choose a compact ECharts visualization, using the model gateway when configured."""
    if not columns or not rows:
        return {"type": "table", "title": question, "option": {}}
    numeric_index = next(
        (index for index in range(1, len(columns)) if any(isinstance(row[index], (int, float, Decimal)) for row in rows)),
        None,
    )
    if numeric_index is None:
        return {"type": "table", "title": question, "option": {}}

    chart_type = "line" if any(word in question.lower() for word in ("趋势", "每天", "按日", "日期", "trend")) else "bar"
    if any(word in question.lower() for word in ("占比", "比例", "构成", "份额", "pie")):
        chart_type = "pie"

    endpoint, model, api_key = active_model_config()
    if endpoint:
        payload = {
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": "Choose exactly one BI chart type from line, bar, pie, table. Return only the type.",
                },
                {
                    "role": "user",
                    "content": f"Question: {question}\nColumns: {', '.join(columns)}\nRows: {len(rows)}",
                },
            ],
        }
        if model:
            payload["model"] = model
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        try:
            async with httpx.AsyncClient(timeout=12) as client:
                response = await client.post(model_chat_url(endpoint), json=payload, headers=headers)
                response.raise_for_status()
                candidate = response.json()["choices"][0]["message"]["content"].strip().lower()
            if candidate in {"line", "bar", "pie", "table"}:
                chart_type = candidate
        except Exception:
            # Chart selection is non-critical; keep the deterministic fallback.
            pass

    labels = [row[0] for row in rows]
    values = [row[numeric_index] for row in rows]
    if chart_type == "pie":
        option = {
            "tooltip": {"trigger": "item"},
            "legend": {"bottom": 0},
            "series": [{"type": "pie", "radius": ["42%", "68%"], "data": [{"name": label, "value": value} for label, value in zip(labels, values)]}],
        }
    elif chart_type in {"line", "bar"}:
        option = {
            "tooltip": {"trigger": "axis"},
            "grid": {"left": 48, "right": 24, "top": 28, "bottom": 52},
            "xAxis": {"type": "category", "data": labels, "axisLabel": {"rotate": 24 if len(labels) > 8 else 0}},
            "yAxis": {"type": "value"},
            "series": [{"type": chart_type, "smooth": chart_type == "line", "barMaxWidth": 42, "data": values}],
        }
    else:
        option = {}
    return {"type": chart_type, "title": question, "xField": columns[0], "yField": columns[numeric_index], "option": option}


def safe_select(sql: str) -> str:
    """Reject write/multi-statement SQL before it reaches a database or DuckDB."""
    candidate = sql.strip().rstrip(";").strip()
    if not candidate or ";" in candidate or not re.match(r"(?is)^with\b|^select\b", candidate):
        raise HTTPException(400, "only a single SELECT/CTE statement is allowed")
    if re.search(r"(?is)\b(insert|update|delete|drop|alter|truncate|grant|revoke|create|replace|call|load)\b", candidate):
        raise HTTPException(400, "write or administrative SQL is blocked")
    return candidate


DANGEROUS_QUERY_RE = re.compile(
    r"(?is)\b(insert|update|delete|drop|alter|truncate|grant|revoke|create|replace|call|load)\b"
    r"|删除|删表|更新|修改|写入|建表|授权|撤销权限|执行存储过程"
)


def reject_dangerous_intent(question: str) -> None:
    """Reject explicit write or administrative intent before Text2SQL generation."""
    if DANGEROUS_QUERY_RE.search(question):
        raise HTTPException(400, "write or administrative intent is blocked")


def heuristic_sql(question: str, catalog: TidbCatalog) -> str:
    table = "reporting.daily_sales"
    date_column = "stat_date"
    value_column = "gmv"
    table_lookup = {item.name.lower(): (schema.name, item) for schema in catalog.schemas for item in schema.tables}
    lowered = question.lower()
    if "order_fact" in table_lookup:
        schema = table_lookup["order_fact"][0]
        orders = f"{schema}.order_fact"
        if any(word in lowered for word in ("区域", "region")) and "customer_dim" in table_lookup:
            customer_schema = table_lookup["customer_dim"][0]
            return f"SELECT c.region, SUM(o.amount) AS total_value FROM {orders} o JOIN {customer_schema}.customer_dim c ON c.customer_id = o.customer_id GROUP BY c.region ORDER BY total_value DESC LIMIT 100"
        if any(word in lowered for word in ("品类", "类别", "category")) and "product_dim" in table_lookup:
            product_schema = table_lookup["product_dim"][0]
            return f"SELECT p.category, SUM(o.amount) AS total_value FROM {orders} o JOIN {product_schema}.product_dim p ON p.product_id = o.product_id GROUP BY p.category ORDER BY total_value DESC LIMIT 100"
        if any(word in lowered for word in ("渠道", "channel")):
            return f"SELECT channel, SUM(amount) AS total_value FROM {orders} GROUP BY channel ORDER BY total_value DESC LIMIT 100"
        if any(word in lowered for word in ("状态", "status")):
            return f"SELECT status, COUNT(*) AS total_value FROM {orders} GROUP BY status ORDER BY total_value DESC LIMIT 100"

    for schema in catalog.schemas:
        for item in schema.tables:
            names = {column.name.lower() for column in item.columns}
            if "gmv" in names or "amount" in names:
                table = f"{schema.name}.{item.name}"
                value_column = "gmv" if "gmv" in names else "amount"
                date_column = next((name for name in names if "date" in name or "created" in name), date_column)
                break
    if any(word in lowered for word in ("趋势", "trend", "每天", "按日")):
        return f"SELECT {date_column}, SUM({value_column}) AS total_value FROM {table} GROUP BY {date_column} ORDER BY {date_column}"
    return f"SELECT {date_column}, SUM({value_column}) AS total_value FROM {table} GROUP BY {date_column} ORDER BY {date_column} LIMIT 100"


def catalog_context(catalog: TidbCatalog) -> str:
    return "\n".join(f"{schema.name}.{table.name}: " + ", ".join(f"{column.name} {column.data_type} -- {column.comment or ''}" for column in table.columns) for schema in catalog.schemas for table in schema.tables)


async def model_sql(question: str, catalog: TidbCatalog) -> str:
    endpoint, model, api_key = active_model_config()
    if not endpoint:
        return heuristic_sql(question, catalog)
    payload = {"temperature": 0, "messages": [{"role": "system", "content": "You generate one read-only TiDB SELECT statement. Return SQL only."}, {"role": "user", "content": f"Schema:\n{catalog_context(catalog)}\nQuestion: {question}"}]}
    if model:
        payload["model"] = model
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(model_chat_url(endpoint), json=payload, headers=headers)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
    return content.replace("```sql", "").replace("```", "").strip()


def normalize_tool_result(result: Any) -> Any:
    structured = getattr(result, "structured_content", None)
    if structured is not None:
        return structured
    content = getattr(result, "content", result)
    if isinstance(content, list):
        for item in content:
            text = getattr(item, "text", None)
            if text:
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return text
    return content


def pick_tool(available: list[str], aliases: list[str], configured: str | None) -> str:
    if configured:
        return configured
    for alias in aliases:
        if alias in available:
            return alias
    raise RuntimeError(f"MCP server is missing one of tools: {', '.join(aliases)}")


async def call_mcp(endpoint: str, token: str | None, tool_map: dict[str, str], operation: str, arguments: dict[str, Any]) -> Any:
    try:
        from mcp import Client
    except ImportError as exc:
        raise HTTPException(503, "MCP client dependency is not installed") from exc
    headers = {"Authorization": f"Bearer {token}"} if token else None
    try:
        client = Client(endpoint, headers=headers) if headers else Client(endpoint)
    except TypeError:
        client = Client(endpoint)
    async with client as session:
        listed = await session.list_tools()
        tools = getattr(listed, "tools", listed)
        names = [getattr(item, "name", str(item)) for item in tools]
        aliases = {
            "schemas": ["list_schemas", "get_schemas", "show_schemas"],
            "tables": ["list_tables", "get_tables", "show_tables"],
            "columns": ["describe_table", "get_table_schema", "get_columns", "describe"],
            "relationships": ["list_relationships", "get_relationships", "list_foreign_keys", "get_lineage"],
            "query": ["execute_query", "query", "run_sql", "execute_sql"],
        }[operation]
        tool = pick_tool(names, aliases, tool_map.get(operation))
        return normalize_tool_result(await session.call_tool(tool, arguments))


def rows_from_result(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        for key in ("rows", "data", "items", "tables", "schemas", "columns"):
            if key in value:
                return rows_from_result(value[key])
        return [value]
    if isinstance(value, list):
        if not value:
            return []
        if all(isinstance(item, dict) for item in value):
            return value
        if all(isinstance(item, (list, tuple)) for item in value):
            return [{str(index): item for index, item in enumerate(row)} for row in value]
    return []


def tabular_rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict) and isinstance(value.get("columns"), list) and isinstance(value.get("rows"), list):
        columns = [str(column.get("name") if isinstance(column, dict) else column) for column in value["columns"]]
        return [dict(zip(columns, row)) for row in value["rows"] if isinstance(row, (list, tuple))]
    return rows_from_result(value)


def first_scalar(value: Any) -> str:
    rows = rows_from_result(value)
    if rows and rows[0]:
        return str(next(iter(rows[0].values())))
    if isinstance(value, str):
        return value
    return ""


async def introspect_mcp(payload: TidbMcpIntrospectRequest) -> TidbCatalog:
    endpoint = payload.endpoint or os.getenv("TIDB_MCP_ENDPOINT", "").strip()
    if not endpoint:
        raise HTTPException(400, "MCP endpoint is required")
    if endpoint in ("demo://tidb", "demo"):
        return DEMO_CATALOG.model_copy(update={"source": "demo", "collected_at": now_iso()})
    try:
        schemas_raw = await call_mcp(endpoint, payload.token, payload.tool_map, "schemas", {"database": payload.database} if payload.database else {})
        schema_rows = rows_from_result(schemas_raw)
        schemas: list[CatalogSchema] = []
        for schema_item in schema_rows:
            schema_name = str(schema_item.get("name") or schema_item.get("schema_name") or schema_item.get("SCHEMA_NAME") or next(iter(schema_item.values()), "unknown"))
            tables_raw = await call_mcp(endpoint, payload.token, payload.tool_map, "tables", {"schema": schema_name, "database": payload.database} if payload.database else {"schema": schema_name})
            table_rows = rows_from_result(tables_raw)
            tables: list[CatalogTable] = []
            for table_item in table_rows:
                table_name = str(table_item.get("name") or table_item.get("table_name") or table_item.get("TABLE_NAME") or next(iter(table_item.values()), "unknown"))
                columns_raw = await call_mcp(endpoint, payload.token, payload.tool_map, "columns", {"schema": schema_name, "table": table_name, "database": payload.database} if payload.database else {"schema": schema_name, "table": table_name})
                columns = [CatalogColumn(name=str(item.get("name") or item.get("column_name") or item.get("COLUMN_NAME")), data_type=str(item.get("data_type") or item.get("type") or item.get("DATA_TYPE") or "unknown"), comment=item.get("comment") or item.get("COLUMN_COMMENT"), nullable=str(item.get("nullable", "YES")).upper() not in ("NO", "FALSE", "0")) for item in rows_from_result(columns_raw)]
                tables.append(CatalogTable(name=table_name, comment=table_item.get("comment") or table_item.get("TABLE_COMMENT"), columns=columns))
            schemas.append(CatalogSchema(name=schema_name, tables=tables))
        relationships: list[dict[str, str]] = []
        try:
            relationship_rows = rows_from_result(await call_mcp(endpoint, payload.token, payload.tool_map, "relationships", {"database": payload.database} if payload.database else {}))
            for item in relationship_rows:
                source = item.get("from") or item.get("source") or item.get("source_column")
                target = item.get("to") or item.get("target") or item.get("target_column")
                if source and target:
                    relationships.append({"from": str(source), "to": str(target), "type": str(item.get("type") or "relationship")})
        except RuntimeError:
            pass
        return TidbCatalog(database=payload.database or "tidb", schemas=schemas, relationships=relationships, source=endpoint, collected_at=now_iso())
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, f"MCP introspection failed: {exc.__class__.__name__}") from exc


def make_dataset_from_file(path: Path, dataset_id: str, kind: str, display_name: str | None = None) -> Dataset:
    try:
        if kind == "csv":
            import pandas as pd
            frame = pd.read_csv(path, nrows=1000)
            with path.open("r", encoding="utf-8", errors="ignore") as source:
                rows = sum(1 for _ in source) - 1
        else:
            import pandas as pd
            frame = pd.read_parquet(path)
            rows = len(frame)
    except ImportError as exc:
        raise HTTPException(503, "CSV/Parquet analysis dependencies are not installed") from exc
    except Exception as exc:
        raise HTTPException(400, f"cannot read dataset: {exc}") from exc
    return Dataset(id=dataset_id, name=display_name or path.name, kind=kind, path=str(path), rows=max(rows, 0), columns=[{"name": str(column), "type": str(dtype)} for column, dtype in frame.dtypes.items()], created_at=now_iso())


def allowed_local_path(path: Path) -> bool:
    roots = [Path(item).expanduser().resolve() for item in os.getenv("DATASET_ALLOWED_ROOTS", str(Path.cwd())).split(os.pathsep) if item]
    resolved = path.expanduser().resolve()
    return any(resolved == root or root in resolved.parents for root in roots)


class _KnowledgeHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.ignored_depth += 1
        elif tag in {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.ignored_depth:
            self.ignored_depth -= 1
        elif tag in {"p", "div", "li", "h1", "h2", "h3", "h4", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.ignored_depth:
            self.parts.append(data)


def knowledge_file_text(name: str, payload: bytes) -> tuple[str, str]:
    suffix = Path(name).suffix.lower()
    if suffix not in KNOWLEDGE_ALLOWED_SUFFIXES:
        raise HTTPException(415, f"unsupported knowledge document type: {suffix or 'unknown'}")
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(400, f"knowledge document must be UTF-8: {name}") from exc
    if suffix in {".html", ".htm"}:
        parser = _KnowledgeHTMLParser()
        parser.feed(text)
        return "".join(parser.parts), "text/html"
    mime_types = {".md": "text/markdown", ".markdown": "text/markdown", ".json": "application/json", ".sql": "application/sql", ".ddl": "application/sql"}
    return text, mime_types.get(suffix, "text/plain")


def active_mcp_config(explicit_endpoint: str | None = None) -> tuple[str, str | None, dict[str, str]]:
    endpoint = explicit_endpoint or (MCP_CONNECTION.endpoint if MCP_CONNECTION else None) or os.getenv("TIDB_MCP_ENDPOINT", "").strip()
    if not endpoint or endpoint in ("demo://tidb", "demo"):
        raise HTTPException(400, "live optimization requires a real TiDB MCP endpoint")
    parsed = urlparse(endpoint)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise HTTPException(400, "TiDB MCP endpoint must be an HTTP(S) URL without credentials or fragments")
    allowed_hosts = {item.strip().lower() for item in os.getenv("TIDB_MCP_ALLOWED_HOSTS", "").split(",") if item.strip()}
    if allowed_hosts and parsed.hostname.lower() not in allowed_hosts:
        raise HTTPException(403, "TiDB MCP endpoint host is not allowlisted")
    token = MCP_CONNECTION.token if MCP_CONNECTION and MCP_CONNECTION.endpoint == endpoint else None
    tool_map = MCP_CONNECTION.tool_map if MCP_CONNECTION and MCP_CONNECTION.endpoint == endpoint else {}
    return endpoint, token, tool_map


def direct_tidb_optimizer_plan(sql: str) -> tuple[str, list[dict[str, Any]]]:
    """Run a read-only EXPLAIN against the deployment's TiDB endpoint.

    MCP remains the preferred integration when configured.  The direct path is
    intentionally environment-only (no arbitrary host from the request) so a
    Python 3.9 deployment can still demonstrate live optimizer behavior when
    the MCP SDK is unavailable.
    """
    host = os.getenv("AEGIS_TIDB_OPTIMIZER_HOST", "").strip()
    if not host:
        raise HTTPException(400, "live optimization requires TiDB MCP or AEGIS_TIDB_OPTIMIZER_HOST")
    allowed_hosts = {item.strip().lower() for item in os.getenv("CHATBI_ALLOWED_DB_HOSTS", "").split(",") if item.strip()}
    if allowed_hosts and host.lower() not in allowed_hosts:
        raise HTTPException(403, "direct TiDB optimizer host is not allowlisted")
    try:
        import pymysql
    except ImportError as exc:
        raise HTTPException(503, "PyMySQL is not installed") from exc
    try:
        connection = pymysql.connect(
            host=host,
            port=int(os.getenv("AEGIS_TIDB_OPTIMIZER_PORT", os.getenv("AEGIS_TIDB_SQL_PORT", "4000"))),
            user=os.getenv("AEGIS_TIDB_OPTIMIZER_USER", "root"),
            password=os.getenv("AEGIS_TIDB_OPTIMIZER_PASSWORD", ""),
            database=os.getenv("AEGIS_TIDB_OPTIMIZER_DATABASE", ""),
            charset="utf8mb4",
            autocommit=True,
            connect_timeout=5,
            read_timeout=20,
            cursorclass=pymysql.cursors.DictCursor,
        )
    except Exception as exc:
        raise HTTPException(502, f"direct TiDB connection failed: {exc.__class__.__name__}") from exc
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION() AS version")
            version_row = cursor.fetchone() or {}
            actual_version = str(version_row.get("version", ""))
            cursor.execute(f"EXPLAIN FORMAT='verbose' {sql.strip().rstrip(';')}")
            plan_rows = list(cursor.fetchall())
    except Exception as exc:
        raise HTTPException(502, f"direct TiDB EXPLAIN failed: {exc.__class__.__name__}") from exc
    finally:
        connection.close()
    return actual_version, plan_rows


def register_dataset(path: Path, display_name: str | None = None) -> Dataset:
    suffix = path.suffix.lower()
    if suffix not in (".csv", ".parquet"):
        raise HTTPException(415, "only CSV and Parquet datasets are supported")
    dataset_id = f"ds-{uuid4().hex[:10]}"
    dataset = make_dataset_from_file(path, dataset_id, suffix[1:], display_name)
    DATASETS[dataset_id] = dataset
    return dataset


def dataset_query(dataset: Dataset, question: str) -> tuple[str, list[str], list[list[Any]]]:
    try:
        import duckdb
    except ImportError as exc:
        raise HTTPException(503, "DuckDB is not installed") from exc
    view_name = re.sub(r"[^a-zA-Z0-9_]", "_", Path(dataset.name).stem) or "dataset"
    connection = duckdb.connect()
    reader = "read_csv_auto" if dataset.kind == "csv" else "read_parquet"
    escaped_path = dataset.path.replace("'", "''")
    connection.execute(f'CREATE OR REPLACE VIEW "{view_name}" AS SELECT * FROM {reader}(\'{escaped_path}\')')
    columns = [item[0] for item in connection.execute(f'DESCRIBE "{view_name}"').fetchall()]
    numeric = [item[0] for item in connection.execute(f'DESCRIBE "{view_name}"').fetchall() if any(token in item[1].upper() for token in ("INT", "DECIMAL", "DOUBLE", "FLOAT", "REAL"))]
    date_col = next((column for column in columns if any(token in column.lower() for token in ("date", "time", "created", "day"))), None)
    if date_col and numeric:
        sql = f'SELECT "{date_col}", SUM("{numeric[0]}") AS total_value FROM "{view_name}" GROUP BY "{date_col}" ORDER BY "{date_col}" LIMIT 100'
    else:
        sql = f'SELECT * FROM "{view_name}" LIMIT 100'
    result = connection.execute(sql).fetchall()
    return sql, [description[0] for description in connection.description], [list(row) for row in result]


def catalog_from_database(item: DataSourceRecord, rows: list[dict[str, Any]]) -> TidbCatalog:
    schemas: dict[str, dict[str, CatalogTable]] = {}
    for row in rows:
        schema_name = str(row.get("TABLE_SCHEMA") or row.get("table_schema") or item.database or "tidb")
        table_name = str(row.get("TABLE_NAME") or row.get("table_name") or "unknown")
        tables = schemas.setdefault(schema_name, {})
        table = tables.setdefault(
            table_name,
            CatalogTable(name=table_name, comment=row.get("TABLE_COMMENT") or row.get("table_comment")),
        )
        table.columns.append(
            CatalogColumn(
                name=str(row.get("COLUMN_NAME") or row.get("column_name")),
                data_type=str(row.get("COLUMN_TYPE") or row.get("DATA_TYPE") or "unknown"),
                comment=row.get("COLUMN_COMMENT") or row.get("column_comment"),
                nullable=str(row.get("IS_NULLABLE") or "YES").upper() != "NO",
            )
        )
    return TidbCatalog(
        database=item.database or "tidb",
        schemas=[CatalogSchema(name=name, tables=list(tables.values())) for name, tables in schemas.items()],
        relationships=[],
        source=f"chatbi:{item.id}",
        collected_at=now_iso(),
    )


def collect_relationship_snapshot(datasource_id: str) -> RelationshipSnapshot:
    item = datasource_or_404(datasource_id)
    if item.kind not in {"tidb", "mysql"}:
        raise HTTPException(400, "data relationships require a TiDB or MySQL datasource")
    if item.id == "ds-demo-tidb":
        catalog = DEMO_CATALOG.model_copy(
            update={"source": f"chatbi:{item.id}", "collected_at": now_iso()}
        )
    else:
        if item.status != "ready":
            raise HTTPException(409, "datasource connection must be ready before collection")
        try:
            rows, _ = inspect_database(item)
            relationships = inspect_database_relationships(item)
        except Exception as exc:
            raise HTTPException(502, f"datasource metadata collection failed: {exc}") from exc
        catalog = catalog_from_database(item, rows).model_copy(
            update={"relationships": relationships, "collected_at": now_iso()}
        )
    RELATIONSHIP_CATALOGS[datasource_id] = catalog
    return build_snapshot(datasource_id, item.name, catalog)


def collect_sql_snapshot(datasource_id: str) -> RelationshipSnapshot:
    item = datasource_or_404(datasource_id)
    if item.kind != "tidb":
        raise HTTPException(400, "automatic statement-summary collection requires TiDB")
    if item.id == "ds-demo-tidb":
        rows = [
            {
                "DIGEST_TEXT": (
                    "SELECT o.order_id, c.region FROM sales.orders o "
                    "JOIN sales.customers c ON c.customer_id=o.customer_id"
                ),
                "EXEC_COUNT": 18,
            },
            {
                "DIGEST_TEXT": (
                    "SELECT DATE(o.created_at), SUM(o.amount), d.gmv "
                    "FROM sales.orders o JOIN reporting.daily_sales d "
                    "ON d.stat_date=DATE(o.created_at) GROUP BY DATE(o.created_at)"
                ),
                "EXEC_COUNT": 6,
            },
        ]
    else:
        if item.status != "ready":
            raise HTTPException(409, "datasource connection must be ready before SQL collection")
        try:
            rows = collect_recent_sql(item)
        except Exception as exc:
            raise HTTPException(502, f"TiDB statement summary collection failed: {exc}") from exc
    for row in rows:
        sql = str(row.get("DIGEST_TEXT") or row.get("digest_text") or "").strip()
        if not sql:
            continue
        try:
            ingest_sql(
                datasource_id,
                sql,
                item.database or "",
                "tidb-statements-summary",
                int(row.get("EXEC_COUNT") or row.get("exec_count") or 1),
                cumulative=True,
            )
        except ValueError:
            continue
    catalog = RELATIONSHIP_CATALOGS.get(datasource_id)
    if not catalog:
        return collect_relationship_snapshot(datasource_id)
    return build_snapshot(datasource_id, item.name, catalog)


def stop_sql_collector(datasource_id: str) -> None:
    event = SQL_COLLECTOR_STOPS.pop(datasource_id, None)
    if event:
        event.set()


def datasource_or_404(datasource_id: str) -> DataSourceRecord:
    item = DATA_SOURCES.get(datasource_id)
    if not item:
        raise HTTPException(404, "datasource not found")
    return item


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "data-ai-explorer",
        "node_role": os.getenv("AEGIS_NODE_ROLE", "local"),
        "deployment_version": os.getenv("AEGIS_DEPLOYMENT_VERSION", "dev"),
        "time": now_iso(),
    }


@app.get("/api/v1/deployment/status", tags=["system"])
def deployment_status() -> dict[str, Any]:
    """Expose a safe, live deployment view for the three-node demo environment."""
    raw_hosts = os.getenv("AEGIS_TIDB_ENDPOINTS", "10.2.106.5,10.2.106.124,10.2.106.182")
    hosts = [item.strip() for item in raw_hosts.split(",") if item.strip()]
    status_port = int(os.getenv("AEGIS_TIDB_STATUS_PORT", "11080"))
    sql_port = int(os.getenv("AEGIS_TIDB_SQL_PORT", "4100"))
    tidb_nodes: list[dict[str, Any]] = []
    with httpx.Client(timeout=1.5, follow_redirects=False) as client:
        for host in hosts:
            item: dict[str, Any] = {"host": host, "sql_port": sql_port, "status_port": status_port}
            try:
                response = client.get(f"http://{host}:{status_port}/status")
                response.raise_for_status()
                payload = response.json()
                item.update({"status": "ready", "version": payload.get("version", "unknown")})
            except Exception as exc:
                item.update({"status": "unreachable", "error": exc.__class__.__name__})
            tidb_nodes.append(item)
    return {
        "service": "data-ai-explorer",
        "deployment_version": os.getenv("AEGIS_DEPLOYMENT_VERSION", "dev"),
        "node_role": os.getenv("AEGIS_NODE_ROLE", "local"),
        "modules": [
            "smart-query",
            "chatbi",
            "data-relationships",
            "knowledge-base",
            "aiops",
            "sql-optimizer",
            "scenario-center",
            "agent-center",
        ],
        "tidb_nodes": tidb_nodes,
        "observability": {
            "node_exporter": os.getenv("AEGIS_NODE_EXPORTER_URL", "http://127.0.0.1:9100/metrics"),
            "external_adapter_mode": os.getenv("AEGIS_EXTERNAL_ADAPTER_MODE", "demo"),
        },
        "checked_at": now_iso(),
    }


@app.post("/api/v1/auth/login", tags=["auth"])
def login(payload: LoginRequest) -> dict[str, Any]:
    if "@" not in payload.email or not payload.password.strip():
        raise HTTPException(401, "invalid demo credentials")
    session_id = f"sess-{uuid4().hex[:16]}"
    try:
        record_audit(session_id, payload.email, "login", "session", session_id, {"mode": "demo"})
    except Exception:
        pass
    return {
        "session_id": session_id,
        "token_type": "demo",
        "user": {"email": payload.email, "display_name": payload.email.split("@", 1)[0]},
        "expires_in": 8 * 60 * 60,
    }


@app.post("/api/v1/auth/logout", tags=["auth"])
def logout(payload: LogoutRequest) -> dict[str, Any]:
    event_id = payload.session_id or f"sess-{uuid4().hex[:16]}"
    try:
        record_audit(event_id, "workspace-user", "logout", "session", payload.session_id, {})
    except Exception:
        pass
    return {"status": "ok", "logged_out_at": now_iso()}


@app.get("/api/v1/settings", response_model=WorkspaceSettings, tags=["settings"])
def get_settings() -> WorkspaceSettings:
    return WORKSPACE_SETTINGS


@app.patch("/api/v1/settings", response_model=WorkspaceSettings, tags=["settings"])
def patch_settings(payload: WorkspaceSettingsUpdate) -> WorkspaceSettings:
    global WORKSPACE_SETTINGS
    values = WORKSPACE_SETTINGS.model_dump()
    values.update({key: value for key, value in payload.model_dump().items() if value is not None})
    values["updated_at"] = now_iso()
    updated = WorkspaceSettings.model_validate(values)
    try:
        save_settings(updated.model_dump())
        record_audit(
            f"audit-{uuid4().hex[:16]}",
            "workspace-admin",
            "settings.update",
            "workspace_settings",
            "default",
            payload.model_dump(exclude_none=True),
        )
    except Exception as exc:
        raise HTTPException(503, f"platform metadata store unavailable: {exc.__class__.__name__}") from exc
    WORKSPACE_SETTINGS = updated
    return updated


@app.get("/api/v1/models/providers", response_model=list[ModelProvider], tags=["models"])
def model_providers() -> list[ModelProvider]:
    return PROVIDERS


@app.get("/api/v1/models/readiness", tags=["models"])
def model_readiness() -> dict[str, Any]:
    active_registry = next((item for item in MODEL_CONNECTIONS.values() if item.is_default and item.status == "ready"), None)
    endpoint, model, _ = active_model_config()
    return {
        "ready": bool(active_registry or (endpoint and model)),
        "source": "registry" if active_registry else ("environment" if endpoint and model else "none"),
        "connection_id": active_registry.id if active_registry else None,
        "model": active_registry.model if active_registry else (model or None),
    }


@app.get("/api/v1/models/connections", response_model=list[ModelConnection], tags=["models"])
def model_connections() -> list[ModelConnection]:
    return list(reversed(list(MODEL_CONNECTIONS.values())))


@app.post("/api/v1/models/connections", response_model=ModelConnection, status_code=201, tags=["models"])
def model_create_connection(payload: ModelConnectionCreate) -> ModelConnection:
    try:
        item = create_connection(payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if payload.test_on_create:
        return test_connection(item, set_default=payload.set_default)
    return item


@app.post("/api/v1/models/connections/{connection_id}/test", response_model=ModelConnection, tags=["models"])
def model_test_connection(connection_id: str) -> ModelConnection:
    item = MODEL_CONNECTIONS.get(connection_id)
    if not item:
        raise HTTPException(404, "model connection not found")
    return test_connection(item)


@app.post("/api/v1/models/connections/{connection_id}/activate", response_model=ModelConnection, tags=["models"])
def model_activate_connection(connection_id: str) -> ModelConnection:
    if connection_id not in MODEL_CONNECTIONS:
        raise HTTPException(404, "model connection not found")
    try:
        return set_default_connection(connection_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.delete("/api/v1/models/connections/{connection_id}", status_code=204, tags=["models"])
def model_delete_connection(connection_id: str) -> None:
    if connection_id not in MODEL_CONNECTIONS:
        raise HTTPException(404, "model connection not found")
    MODEL_CONNECTIONS.pop(connection_id, None)
    MODEL_SECRETS.pop(connection_id, None)
    mark_model_unavailable(connection_id)


@app.get("/api/v1/agents/templates", response_model=list[AgentTemplate], tags=["agents"])
def agent_templates() -> list[AgentTemplate]:
    return AGENT_TEMPLATES


@app.get("/api/v1/agents", response_model=list[ModuleAgent], tags=["agents"])
def agent_list() -> list[ModuleAgent]:
    return list(reversed(list(MODULE_AGENTS.values())))


@app.post("/api/v1/agents", response_model=ModuleAgent, status_code=201, tags=["agents"])
def agent_create(payload: AgentCreate) -> ModuleAgent:
    try:
        item, _ = create_agent(payload)
        return item
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/api/v1/agents/provision", response_model=AgentProvisionResult, tags=["agents"])
def agent_provision(payload: AgentProvisionRequest) -> AgentProvisionResult:
    try:
        return provision_agents(payload)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


def agent_or_404(agent_id: str) -> ModuleAgent:
    item = MODULE_AGENTS.get(agent_id)
    if not item:
        raise HTTPException(404, "agent not found")
    return item


@app.put("/api/v1/agents/{agent_id}/enabled", response_model=ModuleAgent, tags=["agents"])
def agent_update_enabled(agent_id: str, payload: AgentEnabledUpdate) -> ModuleAgent:
    return set_agent_enabled(agent_or_404(agent_id), payload.enabled)


@app.post("/api/v1/agents/{agent_id}/test", response_model=AgentTestResult, tags=["agents"])
def agent_test(agent_id: str) -> AgentTestResult:
    return test_agent(agent_or_404(agent_id))


@app.post("/api/v1/agents/{agent_id}/invoke", response_model=AgentInvokeResult, tags=["agents"])
def agent_invoke(agent_id: str, payload: AgentInvokeRequest) -> AgentInvokeResult:
    try:
        return invoke_agent(agent_or_404(agent_id), payload)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)) from exc


@app.delete("/api/v1/agents/{agent_id}", status_code=204, tags=["agents"])
def agent_delete(agent_id: str) -> None:
    agent_or_404(agent_id)
    MODULE_AGENTS.pop(agent_id, None)


@app.get("/api/v1/workbench/summary", tags=["workbench"])
def workbench_summary() -> dict[str, Any]:
    open_incidents = [i for i in INCIDENTS if i.status not in ("resolved", "closed")]
    return {"metrics": {"open_incidents": len(open_incidents), "critical_incidents": sum(i.severity == "P1" for i in open_incidents), "managed_assets": len(ASSETS), "query_success_rate": 98.6}, "incidents": [i.model_dump() for i in open_incidents[:3]], "recent_queries": list(OPERATIONS.values())[-5:]}


@app.post("/api/v1/tidb/mcp/introspect", response_model=TidbCatalog, tags=["tidb"])
async def tidb_mcp_introspect(payload: TidbMcpIntrospectRequest) -> TidbCatalog:
    global CATALOG, MCP_CONNECTION
    CATALOG = await introspect_mcp(payload)
    effective_endpoint = payload.endpoint or os.getenv("TIDB_MCP_ENDPOINT", "").strip()
    MCP_CONNECTION = payload.model_copy(update={"endpoint": effective_endpoint})
    return CATALOG


@app.get("/api/v1/tidb/catalog", response_model=TidbCatalog, tags=["tidb"])
def tidb_catalog() -> TidbCatalog:
    return CATALOG


@app.post(
    "/api/v1/data-relationships/{datasource_id}/collect",
    response_model=RelationshipSnapshot,
    tags=["data-relationships"],
)
def collect_data_relationships(datasource_id: str) -> RelationshipSnapshot:
    return collect_relationship_snapshot(datasource_id)


@app.get(
    "/api/v1/data-relationships/{datasource_id}",
    response_model=RelationshipSnapshot,
    tags=["data-relationships"],
)
def get_data_relationships(datasource_id: str) -> RelationshipSnapshot:
    item = datasource_or_404(datasource_id)
    catalog = RELATIONSHIP_CATALOGS.get(datasource_id)
    if not catalog:
        return collect_relationship_snapshot(datasource_id)
    return build_snapshot(datasource_id, item.name, catalog)


@app.post(
    "/api/v1/data-relationships/{datasource_id}/sql-observations",
    response_model=SqlObservationRecord,
    status_code=201,
    tags=["data-relationships"],
)
def add_sql_observation(
    datasource_id: str, payload: SqlObservationRequest
) -> SqlObservationRecord:
    item = datasource_or_404(datasource_id)
    if item.kind not in {"tidb", "mysql"}:
        raise HTTPException(400, "SQL relationships require a database datasource")
    try:
        return ingest_sql(
            datasource_id,
            payload.sql,
            item.database or "",
            payload.source,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post(
    "/api/v1/data-relationships/{datasource_id}/collect-sql",
    response_model=RelationshipSnapshot,
    tags=["data-relationships"],
)
def collect_datasource_sql(datasource_id: str) -> RelationshipSnapshot:
    return collect_sql_snapshot(datasource_id)


@app.get(
    "/api/v1/data-relationships/{datasource_id}/sql-collector",
    response_model=SqlCollectorStatus,
    tags=["data-relationships"],
)
def get_sql_collector(datasource_id: str) -> SqlCollectorStatus:
    datasource_or_404(datasource_id)
    return SQL_COLLECTOR_STATUS.get(
        datasource_id,
        SqlCollectorStatus(
            datasource_id=datasource_id,
            enabled=False,
            interval_seconds=30,
        ),
    )


@app.put(
    "/api/v1/data-relationships/{datasource_id}/sql-collector",
    response_model=SqlCollectorStatus,
    tags=["data-relationships"],
)
def configure_sql_collector(
    datasource_id: str, payload: SqlCollectorUpdate
) -> SqlCollectorStatus:
    item = datasource_or_404(datasource_id)
    if item.kind != "tidb":
        raise HTTPException(400, "automatic statement-summary collection requires TiDB")

    previous = SQL_COLLECTOR_STATUS.get(datasource_id)
    stop_sql_collector(datasource_id)
    status = SqlCollectorStatus(
        datasource_id=datasource_id,
        enabled=payload.enabled,
        interval_seconds=payload.interval_seconds,
        last_collected_at=previous.last_collected_at if previous else None,
        last_error=previous.last_error if previous else None,
    )
    SQL_COLLECTOR_STATUS[datasource_id] = status
    if not payload.enabled:
        return status

    try:
        collect_sql_snapshot(datasource_id)
        status = status.model_copy(
            update={"last_collected_at": now_iso(), "last_error": None}
        )
    except Exception as exc:
        status = status.model_copy(
            update={
                "last_error": (
                    str(exc.detail) if isinstance(exc, HTTPException) else str(exc)
                )
            }
        )
    SQL_COLLECTOR_STATUS[datasource_id] = status

    stop_event = threading.Event()
    SQL_COLLECTOR_STOPS[datasource_id] = stop_event

    def collect_forever() -> None:
        while not stop_event.wait(payload.interval_seconds):
            try:
                collect_sql_snapshot(datasource_id)
                last_collected_at = now_iso()
                last_error = None
            except Exception as exc:
                last_collected_at = None
                last_error = (
                    str(exc.detail) if isinstance(exc, HTTPException) else str(exc)
                )
            if stop_event.is_set():
                break
            current = SQL_COLLECTOR_STATUS.get(datasource_id)
            SQL_COLLECTOR_STATUS[datasource_id] = SqlCollectorStatus(
                datasource_id=datasource_id,
                enabled=True,
                interval_seconds=payload.interval_seconds,
                last_collected_at=last_collected_at
                or (current.last_collected_at if current else None),
                last_error=last_error,
            )

    threading.Thread(
        target=collect_forever,
        name=f"sql-relationship-collector-{datasource_id}",
        daemon=True,
    ).start()
    return status


@app.get("/api/v1/chatbi/datasources", response_model=list[DataSourceRecord], tags=["chatbi"])
def chatbi_datasources() -> list[DataSourceRecord]:
    return list(reversed(list(DATA_SOURCES.values())))


@app.post("/api/v1/chatbi/datasources", response_model=DataSourceRecord, status_code=201, tags=["chatbi"])
def chatbi_create_datasource(payload: DataSourceCreate) -> DataSourceRecord:
    item = create_database_source(payload)
    if payload.test_on_create:
        return test_database_source(item)
    return item


@app.post("/api/v1/chatbi/datasources/{datasource_id}/test", response_model=DataSourceRecord, tags=["chatbi"])
def chatbi_test_datasource(datasource_id: str) -> DataSourceRecord:
    return test_database_source(datasource_or_404(datasource_id))


@app.delete("/api/v1/chatbi/datasources/{datasource_id}", status_code=204, tags=["chatbi"])
def chatbi_delete_datasource(datasource_id: str) -> None:
    if datasource_id not in DATA_SOURCES:
        raise HTTPException(404, "datasource not found")
    if datasource_id == "ds-demo-tidb":
        raise HTTPException(400, "demo datasource cannot be deleted")
    DATA_SOURCES.pop(datasource_id, None)
    DATA_SOURCE_SECRETS.pop(datasource_id, None)
    stop_sql_collector(datasource_id)
    SQL_COLLECTOR_STATUS.pop(datasource_id, None)
    RELATIONSHIP_CATALOGS.pop(datasource_id, None)
    clear_datasource_relationships(datasource_id)


@app.post("/api/v1/chatbi/datasources/upload", response_model=DataSourceRecord, status_code=201, tags=["chatbi"])
async def chatbi_upload_datasource(file: UploadFile = File(...)) -> DataSourceRecord:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".csv", ".parquet"):
        raise HTTPException(415, "only .csv and .parquet files are supported")
    target = DATASET_DIR / f"{uuid4().hex}{suffix}"
    with target.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    dataset = register_dataset(target, Path(file.filename or target.name).name)
    return create_csv_source(dataset.name, dataset.id, dataset.rows)


@app.post("/api/v1/chatbi/query", response_model=QueryOperation, status_code=202, tags=["chatbi"])
async def chatbi_query(payload: ChatBIQuery) -> QueryOperation:
    item = datasource_or_404(payload.datasource_id)
    reject_dangerous_intent(payload.question)
    source = item.kind
    catalog = CATALOG
    if item.id == "ds-demo-tidb":
        sql = safe_select(await model_sql(payload.question, DEMO_CATALOG))
        columns = ["stat_date", "total_value"]
        rows = [["2026-08-17", 1213000], ["2026-08-18", 1286000]]
        catalog = DEMO_CATALOG
        source = "demo"
    elif item.kind == "csv":
        dataset = DATASETS.get(item.dataset_id or "")
        if not dataset:
            raise HTTPException(404, "dataset backing datasource not found")
        sql, columns, rows = dataset_query(dataset, payload.question)
        source = "duckdb"
    else:
        if item.status != "ready":
            raise HTTPException(409, "datasource must pass connection test before querying")
        try:
            metadata, _ = inspect_database(item)
            catalog = catalog_from_database(item, metadata)
            sql = await model_sql(payload.question, catalog)
            sql = safe_select(sql)
            columns, rows = execute_database_select(item, sql)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(502, f"database query failed: {exc.__class__.__name__}") from exc
        source = f"{item.kind}-direct"
    operation = QueryOperation(
        operation_id=f"op-{uuid4().hex[:10]}",
        status="completed",
        question=payload.question,
        sql=sql,
        answer="已完成只读分析。图表类型根据问题意图和结果字段自动选择，可认可后加入大屏。",
        columns=columns,
        rows=rows,
        chart=await chatbi_chart_spec(payload.question, columns, rows),
        evidence=[
            {"type": "datasource", "label": item.name, "ref": item.id},
            {"type": "catalog", "label": catalog.database, "ref": catalog.source},
            {"type": "policy", "label": "read-only SQL guard", "ref": "sql-guard-v1"},
            {"type": "engine", "label": source, "ref": source},
        ],
        created_at=now_iso(),
    )
    OPERATIONS[operation.operation_id] = operation
    return operation


@app.get("/api/v1/chatbi/reports", response_model=list[DashboardReport], tags=["chatbi"])
def chatbi_reports() -> list[DashboardReport]:
    return list(reversed(list(DASHBOARD_REPORTS.values())))


@app.post("/api/v1/chatbi/reports", response_model=DashboardReport, status_code=201, tags=["chatbi"])
def chatbi_create_report(payload: ReportCreate) -> DashboardReport:
    operation = OPERATIONS.get(payload.operation_id)
    item = datasource_or_404(payload.datasource_id)
    if not operation:
        raise HTTPException(404, "query operation not found")
    if operation.status != "completed":
        raise HTTPException(409, "only completed query can be added to dashboard")
    if not any(evidence.get("type") == "datasource" and evidence.get("ref") == item.id for evidence in operation.evidence):
        raise HTTPException(409, "query operation does not belong to datasource")
    existing = next((report for report in DASHBOARD_REPORTS.values() if report.operation_id == operation.operation_id), None)
    if existing:
        return existing
    report = DashboardReport(
        id=f"rpt-{uuid4().hex[:10]}",
        operation_id=operation.operation_id,
        datasource_id=item.id,
        datasource_name=item.name,
        title=payload.title,
        question=operation.question,
        chart=operation.chart or {"type": "table", "title": payload.title, "option": {}},
        columns=operation.columns,
        rows=operation.rows,
        accepted_by="林工",
        created_at=now_iso(),
    )
    DASHBOARD_REPORTS[report.id] = report
    return report


@app.delete("/api/v1/chatbi/reports/{report_id}", status_code=204, tags=["chatbi"])
def chatbi_delete_report(report_id: str) -> None:
    if not DASHBOARD_REPORTS.pop(report_id, None):
        raise HTTPException(404, "dashboard report not found")


@app.post("/api/v1/query/conversations", response_model=QueryOperation, status_code=202, tags=["query"])
async def submit_query(payload: QueryRequest) -> QueryOperation:
    op_id = f"op-{uuid4().hex[:10]}"
    reject_dangerous_intent(payload.question)
    sql = await model_sql(payload.question, CATALOG)
    sql = safe_select(sql)
    rows: list[list[Any]] = [["2026-08-17", 1213000], ["2026-08-18", 1286000]]
    columns = ["stat_date", "total_value"]
    answer = "已基于当前数据目录生成只读查询。请核对指标口径和时间范围后使用结果。"
    active_mcp = payload.mcp_endpoint or (MCP_CONNECTION.endpoint if MCP_CONNECTION else None)
    source = "tidb-mcp" if active_mcp and active_mcp not in ("demo://tidb", "demo") else "demo"
    if payload.source_type == "dataset" and payload.dataset_ids:
        dataset = DATASETS.get(payload.dataset_ids[0])
        if not dataset:
            raise HTTPException(404, "dataset not found")
        sql, columns, rows = dataset_query(dataset, payload.question)
        source = "duckdb"
    elif active_mcp and active_mcp not in ("demo://tidb", "demo"):
        try:
            token = MCP_CONNECTION.token if MCP_CONNECTION and MCP_CONNECTION.endpoint == active_mcp else None
            tool_map = MCP_CONNECTION.tool_map if MCP_CONNECTION and MCP_CONNECTION.endpoint == active_mcp else {}
            raw = await call_mcp(active_mcp, token, tool_map, "query", {"sql": sql})
            records = rows_from_result(raw)
            if records:
                columns = list(records[0].keys())
                rows = [[record.get(column) for column in columns] for record in records[:1000]]
            answer = "TiDB MCP 已执行查询，结果已通过只读策略返回。"
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(502, f"TiDB MCP query failed: {exc.__class__.__name__}") from exc
    operation = QueryOperation(operation_id=op_id, status="completed", question=payload.question, sql=sql, answer=answer, columns=columns, rows=rows, chart=chart_spec(columns, rows, payload.question), evidence=[{"type": "catalog", "label": CATALOG.database, "ref": CATALOG.source}, {"type": "policy", "label": "read-only SQL guard", "ref": "sql-guard-v1"}, {"type": "engine", "label": source, "ref": source}], created_at=now_iso())
    OPERATIONS[op_id] = operation
    return operation


@app.get("/api/v1/query/operations/{operation_id}", response_model=QueryOperation, tags=["query"])
def query_status(operation_id: str) -> QueryOperation:
    operation = OPERATIONS.get(operation_id)
    if not operation:
        raise HTTPException(404, "query operation not found")
    return operation


@app.get("/api/v1/query/operations/{operation_id}/events", tags=["query"])
async def query_operation_events(operation_id: str) -> StreamingResponse:
    """Stream a resumable-friendly execution timeline for a completed operation.

    The MVP query executor completes in one request, but clients still need a
    stable event contract before the executor is moved to a worker queue.  The
    event names and payload shape stay the same when that migration happens.
    """
    operation = OPERATIONS.get(operation_id)
    if not operation:
        raise HTTPException(404, "query operation not found")

    async def events():
        phases = (
            ("PLANNING", "解析自然语言问题", 20),
            ("VALIDATING", "校验只读 SQL 和数据源权限", 45),
            ("EXECUTING", "在目标数据源执行查询", 80),
        )
        for phase, detail, progress in phases:
            yield f"event: progress\ndata: {json.dumps({'phase': phase, 'detail': detail, 'progress': progress}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05)
        yield f"event: completed\ndata: {json.dumps({'phase': 'COMPLETED', 'progress': 100, 'operation': operation.model_dump()}, ensure_ascii=False, default=str)}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@app.post("/api/v1/datasets/upload", response_model=Dataset, status_code=201, tags=["datasets"])
async def upload_dataset(file: UploadFile = File(...)) -> Dataset:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".csv", ".parquet"):
        raise HTTPException(415, "only .csv and .parquet files are supported")
    target = DATASET_DIR / f"{uuid4().hex}{suffix}"
    with target.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    return register_dataset(target, Path(file.filename or target.name).name)


@app.post("/api/v1/datasets/local-directory", response_model=list[Dataset], tags=["datasets"])
def scan_local_directory(payload: LocalDirectoryRequest) -> list[Dataset]:
    directory = Path(payload.path).expanduser()
    if not directory.exists() or not directory.is_dir() or not allowed_local_path(directory):
        raise HTTPException(403, "directory is not allowed")
    files = [item for item in directory.rglob("*") if item.is_file() and item.suffix.lower() in (".csv", ".parquet")][:100]
    return [register_dataset(item) for item in files]


@app.get("/api/v1/datasets", response_model=list[Dataset], tags=["datasets"])
def datasets() -> list[Dataset]:
    return list(DATASETS.values())


@app.post("/api/v1/datasets/analyze", response_model=QueryOperation, status_code=202, tags=["datasets"])
def analyze_dataset(payload: DatasetAnalyzeRequest) -> QueryOperation:
    dataset = DATASETS.get(payload.dataset_ids[0])
    if not dataset:
        raise HTTPException(404, "dataset not found")
    sql, columns, rows = dataset_query(dataset, payload.question)
    operation = QueryOperation(operation_id=f"op-{uuid4().hex[:10]}", status="completed", question=payload.question, sql=sql, answer="已完成文件数据分析，结果可继续转为报表或任务。", columns=columns, rows=rows, chart=chart_spec(columns, rows, payload.question), evidence=[{"type": "dataset", "label": dataset.name, "ref": dataset.id}, {"type": "engine", "label": "DuckDB", "ref": "duckdb"}], created_at=now_iso())
    OPERATIONS[operation.operation_id] = operation
    return operation


@app.get("/api/v1/knowledge-bases", response_model=list[KnowledgeBaseRecord], tags=["knowledge"])
def list_knowledge_bases(search: str | None = Query(None)) -> list[KnowledgeBaseRecord]:
    query = (search or "").strip().lower()
    return [
        item
        for item in reversed(list(KNOWLEDGE_BASES.values()))
        if not query or query in f"{item.name} {item.description}".lower()
    ]


@app.post("/api/v1/knowledge-bases", response_model=KnowledgeBaseRecord, status_code=201, tags=["knowledge"])
def post_knowledge_base(payload: KnowledgeBaseCreate) -> KnowledgeBaseRecord:
    try:
        return create_knowledge_base(payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/v1/knowledge-bases/index-modes", response_model=list[KnowledgeIndexMode], tags=["knowledge"])
def get_knowledge_index_modes() -> list[KnowledgeIndexMode]:
    return KNOWLEDGE_INDEX_MODES


@app.get("/api/v1/knowledge-bases/chunking-modes", response_model=list[KnowledgeChunkingMode], tags=["knowledge"])
def get_knowledge_chunking_modes() -> list[KnowledgeChunkingMode]:
    return KNOWLEDGE_CHUNKING_MODES


@app.get("/api/v1/knowledge-bases/{knowledge_base_id}", response_model=KnowledgeBaseRecord, tags=["knowledge"])
def get_knowledge_base(knowledge_base_id: str) -> KnowledgeBaseRecord:
    knowledge_base = KNOWLEDGE_BASES.get(knowledge_base_id)
    if not knowledge_base:
        raise HTTPException(404, "knowledge base not found")
    return knowledge_base


@app.patch("/api/v1/knowledge-bases/{knowledge_base_id}", response_model=KnowledgeBaseRecord, tags=["knowledge"])
def patch_knowledge_base(
    knowledge_base_id: str,
    payload: KnowledgeBaseUpdate,
) -> KnowledgeBaseRecord:
    try:
        return update_knowledge_base(knowledge_base_id, payload)
    except KeyError as exc:
        raise HTTPException(404, "knowledge base not found") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/v1/knowledge-bases/{knowledge_base_id}/documents", response_model=list[KnowledgeDocument], tags=["knowledge"])
def get_knowledge_documents(knowledge_base_id: str) -> list[KnowledgeDocument]:
    try:
        return list_documents(knowledge_base_id)
    except KeyError as exc:
        raise HTTPException(404, "knowledge base not found") from exc


@app.get("/api/v1/knowledge-bases/{knowledge_base_id}/documents/{document_id}/chunks", response_model=list[KnowledgeChunk], tags=["knowledge"])
def get_knowledge_chunks(knowledge_base_id: str, document_id: str) -> list[KnowledgeChunk]:
    try:
        return list_document_chunks(knowledge_base_id, document_id)
    except KeyError as exc:
        raise HTTPException(404, "knowledge base not found") from exc
    except LookupError as exc:
        raise HTTPException(404, "knowledge document not found") from exc


@app.patch("/api/v1/knowledge-bases/{knowledge_base_id}/documents/{document_id}", response_model=KnowledgeDocument, tags=["knowledge"])
def patch_knowledge_document(
    knowledge_base_id: str,
    document_id: str,
    payload: KnowledgeDocumentUpdate,
) -> KnowledgeDocument:
    try:
        return update_document(knowledge_base_id, document_id, payload)
    except KeyError as exc:
        raise HTTPException(404, "knowledge base not found") from exc
    except LookupError as exc:
        raise HTTPException(404, "knowledge document not found") from exc


@app.post("/api/v1/knowledge-bases/{knowledge_base_id}/documents/{document_id}/reindex", response_model=KnowledgeDocument, tags=["knowledge"])
def post_reindex_knowledge_document(knowledge_base_id: str, document_id: str) -> KnowledgeDocument:
    try:
        return reindex_document(knowledge_base_id, document_id)
    except KeyError as exc:
        raise HTTPException(404, "knowledge base not found") from exc
    except LookupError as exc:
        raise HTTPException(404, "knowledge document not found") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.delete("/api/v1/knowledge-bases/{knowledge_base_id}/documents/{document_id}", tags=["knowledge"])
def delete_knowledge_document(knowledge_base_id: str, document_id: str) -> dict[str, bool]:
    try:
        delete_document(knowledge_base_id, document_id)
    except KeyError as exc:
        raise HTTPException(404, "knowledge base not found") from exc
    except LookupError as exc:
        raise HTTPException(404, "knowledge document not found") from exc
    return {"deleted": True}


@app.post("/api/v1/knowledge-bases/{knowledge_base_id}/documents", response_model=KnowledgeDocument, status_code=201, tags=["knowledge"])
def post_knowledge_document(knowledge_base_id: str, payload: KnowledgeDocumentCreate) -> KnowledgeDocument:
    try:
        return add_document(knowledge_base_id, payload)
    except KeyError as exc:
        raise HTTPException(404, "knowledge base not found") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/v1/knowledge-bases/{knowledge_base_id}/documents/upload", response_model=list[KnowledgeDocument], status_code=201, tags=["knowledge"])
async def upload_knowledge_documents(knowledge_base_id: str, files: list[UploadFile] = File(...)) -> list[KnowledgeDocument]:
    if knowledge_base_id not in KNOWLEDGE_BASES:
        raise HTTPException(404, "knowledge base not found")
    if not files or len(files) > 20:
        raise HTTPException(400, "upload between 1 and 20 knowledge documents")
    documents: list[KnowledgeDocument] = []
    for file in files:
        name = Path(file.filename or "document.txt").name
        raw = await file.read(KNOWLEDGE_MAX_FILE_BYTES + 1)
        if len(raw) > KNOWLEDGE_MAX_FILE_BYTES:
            raise HTTPException(413, f"knowledge document exceeds {KNOWLEDGE_MAX_FILE_BYTES} bytes: {name}")
        content, mime_type = knowledge_file_text(name, raw)
        try:
            documents.append(
                add_document(
                    knowledge_base_id,
                    KnowledgeDocumentCreate(
                        title=Path(name).stem,
                        content=content,
                        source_type="upload",
                        source_uri=f"upload://{name}",
                    ),
                    mime_type=mime_type,
                )
            )
        except ValueError as exc:
            raise HTTPException(422, f"{name}: {exc}") from exc
    return documents


@app.post("/api/v1/knowledge-bases/{knowledge_base_id}/documents/local-directory", response_model=list[KnowledgeDocument], status_code=201, tags=["knowledge"])
def scan_knowledge_directory(knowledge_base_id: str, payload: KnowledgeDirectoryRequest) -> list[KnowledgeDocument]:
    if knowledge_base_id not in KNOWLEDGE_BASES:
        raise HTTPException(404, "knowledge base not found")
    directory = Path(payload.path).expanduser()
    if not directory.exists() or not directory.is_dir() or directory.is_symlink() or not allowed_local_path(directory):
        raise HTTPException(403, "directory is not allowed")
    paths = [
        item
        for item in directory.rglob("*")
        if item.is_file()
        and not item.is_symlink()
        and allowed_local_path(item)
        and item.suffix.lower() in KNOWLEDGE_ALLOWED_SUFFIXES
    ][:100]
    documents: list[KnowledgeDocument] = []
    for path in paths:
        if path.stat().st_size > KNOWLEDGE_MAX_FILE_BYTES:
            raise HTTPException(413, f"knowledge document exceeds {KNOWLEDGE_MAX_FILE_BYTES} bytes: {path.name}")
        content, mime_type = knowledge_file_text(path.name, path.read_bytes())
        try:
            documents.append(
                add_document(
                    knowledge_base_id,
                    KnowledgeDocumentCreate(
                        title=path.stem,
                        content=content,
                        source_type="local_directory",
                        source_uri=str(path.resolve()),
                        tags=payload.tags,
                        metadata={"relative_path": str(path.relative_to(directory))},
                    ),
                    mime_type=mime_type,
                )
            )
        except ValueError as exc:
            raise HTTPException(422, f"{path.name}: {exc}") from exc
    return documents


@app.post("/api/v1/knowledge-bases/{knowledge_base_id}/query", response_model=KnowledgeQueryResult, tags=["knowledge"])
def post_knowledge_query(knowledge_base_id: str, payload: KnowledgeQuery) -> KnowledgeQueryResult:
    try:
        return query_knowledge_base(knowledge_base_id, payload)
    except KeyError as exc:
        raise HTTPException(404, "knowledge base not found") from exc


@app.get("/api/v1/knowledge-bases/{knowledge_base_id}/queries", response_model=list[KnowledgeQueryResult], tags=["knowledge"])
def get_knowledge_queries(knowledge_base_id: str, limit: int = Query(20, ge=1, le=100)) -> list[KnowledgeQueryResult]:
    try:
        return list_queries(knowledge_base_id, limit)
    except KeyError as exc:
        raise HTTPException(404, "knowledge base not found") from exc


@app.post("/api/v1/knowledge-bases/{knowledge_base_id}/queries/{query_id}/feedback", response_model=KnowledgeFeedback, status_code=201, tags=["knowledge"])
def post_knowledge_feedback(knowledge_base_id: str, query_id: str, payload: KnowledgeFeedbackCreate) -> KnowledgeFeedback:
    try:
        return add_feedback(knowledge_base_id, query_id, payload)
    except KeyError as exc:
        raise HTTPException(404, "knowledge base not found") from exc
    except LookupError as exc:
        raise HTTPException(404, "knowledge query not found") from exc


@app.get("/api/v1/aiops/sql-optimizer/versions", tags=["sql-optimizer"])
def sql_optimizer_versions() -> list[dict[str, Any]]:
    return [
        {
            "minor": profile["minor"],
            "label": profile["label"],
            "code_tag": profile["code_tag"],
            "code_commit": profile["code_commit"],
            "features": profile["features"],
            "release_notes": profile["release_notes"],
            "source": profile["source"],
        }
        for profile in TIDB_PROFILES
    ]


@app.post("/api/v1/aiops/sql-optimizer/inputs/upload", response_model=SQLInputBundle, tags=["sql-optimizer"])
async def upload_sql_optimizer_inputs(files: list[UploadFile] = File(...)) -> SQLInputBundle:
    if not files or len(files) > 20:
        raise HTTPException(400, "upload between 1 and 20 SQL/DDL files")
    loaded: list[tuple[str, bytes]] = []
    for file in files:
        name = Path(file.filename or "input.sql").name
        payload = await file.read(MAX_INPUT_BYTES + 1)
        if len(payload) > MAX_INPUT_BYTES:
            raise HTTPException(413, f"SQL input exceeds {MAX_INPUT_BYTES} bytes: {name}")
        loaded.append((name, payload))
    return bundle_from_files(loaded)


@app.post("/api/v1/aiops/sql-optimizer/inputs/local-directory", response_model=SQLInputBundle, tags=["sql-optimizer"])
def scan_sql_optimizer_directory(payload: SQLDirectoryRequest) -> SQLInputBundle:
    directory = Path(payload.path).expanduser()
    if not directory.exists() or not directory.is_dir() or not allowed_local_path(directory):
        raise HTTPException(403, "directory is not allowed")
    files = [
        item
        for item in directory.rglob("*")
        if item.is_file()
        and not item.is_symlink()
        and allowed_local_path(item)
        and item.suffix.lower() in ALLOWED_SQL_SUFFIXES
    ][:100]
    loaded: list[tuple[str, bytes]] = []
    for path in files:
        if path.stat().st_size > MAX_INPUT_BYTES:
            raise HTTPException(413, f"SQL input exceeds {MAX_INPUT_BYTES} bytes: {path.name}")
        loaded.append((str(path.relative_to(directory)), path.read_bytes()))
    return bundle_from_files(loaded)


@app.post("/api/v1/aiops/sql-optimizer/analyze", response_model=SQLOptimizeResponse, tags=["sql-optimizer"])
async def optimize_tidb_sql(payload: SQLOptimizeRequest) -> SQLOptimizeResponse:
    normalize_version(payload.tidb_version)
    if payload.plan_mode == "simulate":
        return analyze_sql(payload)

    analyze_sql(payload)
    configured_mcp = payload.mcp_endpoint or (MCP_CONNECTION.endpoint if MCP_CONNECTION else None) or os.getenv("TIDB_MCP_ENDPOINT", "").strip()
    if not configured_mcp and os.getenv("AEGIS_TIDB_OPTIMIZER_HOST", "").strip():
        actual_version, plan_rows = direct_tidb_optimizer_plan(payload.sql)
        if not version_matches(payload.tidb_version, actual_version):
            raise HTTPException(409, f"selected TiDB version does not match connected cluster: {actual_version}")
        if not plan_rows:
            raise HTTPException(502, "direct TiDB returned an empty EXPLAIN plan")
        return analyze_sql(payload, live_rows=plan_rows, actual_version=actual_version)
    endpoint, token, tool_map = active_mcp_config(payload.mcp_endpoint)
    try:
        actual_version = first_scalar(await call_mcp(endpoint, token, tool_map, "query", {"sql": "SELECT VERSION() AS version"}))
        if not actual_version:
            raise HTTPException(502, "TiDB MCP did not return a database version")
        if not version_matches(payload.tidb_version, actual_version):
            raise HTTPException(409, f"selected TiDB version does not match connected cluster: {actual_version}")
        sql = payload.sql.strip().rstrip(";")
        raw_plan = await call_mcp(endpoint, token, tool_map, "query", {"sql": f"EXPLAIN FORMAT='verbose' {sql}"})
        plan_rows = tabular_rows(raw_plan)
        if not plan_rows:
            raise HTTPException(502, "TiDB MCP returned an empty EXPLAIN plan")
        return analyze_sql(payload, live_rows=plan_rows, actual_version=actual_version)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, f"TiDB live optimization failed: {exc.__class__.__name__}") from exc


@app.get("/api/v1/product/modules", response_model=list[ProductModule], tags=["product"])
def get_product_modules(
    role: str | None = Query(None),
    state: DeliveryState | None = Query(None),
    search: str | None = Query(None, max_length=100),
) -> list[ProductModule]:
    return list_modules(role=role, state=state, search=search)


@app.get("/api/v1/product/features/{feature_id}", response_model=ProductFeature, tags=["product"])
def get_product_feature(feature_id: str) -> ProductFeature:
    item = PRODUCT_FEATURES.get(feature_id)
    if not item:
        raise HTTPException(404, "product feature not found")
    return item


@app.get("/api/v1/scenarios", tags=["scenarios"])
def list_scenarios(category: str | None = Query(None), status: str | None = Query(None)) -> list[dict[str, Any]]:
    return [item.model_dump() for item in SCENARIO_TEMPLATES if (not category or item.category == category) and (not status or item.status == status)]


@app.get("/api/v1/scenarios/{scenario_id}", tags=["scenarios"])
def get_scenario(scenario_id: str) -> dict[str, Any]:
    template = SCENARIO_BY_ID.get(scenario_id)
    if not template:
        raise HTTPException(404, "scenario not found")
    return template.model_dump()


@app.post("/api/v1/scenarios/{scenario_id}/runs", response_model=ScenarioRun, status_code=201, tags=["scenarios"])
def create_scenario_run(scenario_id: str, payload: ScenarioRunCreate) -> ScenarioRun:
    template = SCENARIO_BY_ID.get(scenario_id)
    if not template:
        raise HTTPException(404, "scenario not found")
    run = new_run(template, payload)
    SCENARIO_RUNS[run.run_id] = run
    return run


@app.get("/api/v1/scenario-runs", response_model=list[ScenarioRun], tags=["scenarios"])
def list_scenario_runs(status: str | None = Query(None), scenario_id: str | None = Query(None)) -> list[ScenarioRun]:
    return [item for item in reversed(list(SCENARIO_RUNS.values())) if (not status or item.status == status) and (not scenario_id or item.scenario_id == scenario_id)]


@app.get("/api/v1/scenario-runs/{run_id}", response_model=ScenarioRun, tags=["scenarios"])
def get_scenario_run(run_id: str) -> ScenarioRun:
    run = SCENARIO_RUNS.get(run_id)
    if not run:
        raise HTTPException(404, "scenario run not found")
    return run


@app.post("/api/v1/scenario-runs/{run_id}/advance", response_model=ScenarioRun, tags=["scenarios"])
def advance_scenario_run(run_id: str) -> ScenarioRun:
    run = SCENARIO_RUNS.get(run_id)
    if not run:
        raise HTTPException(404, "scenario run not found")
    if run.status in ("completed", "failed"):
        return run
    current_index = next((index for index, item in enumerate(run.steps) if item.id == run.current_step_id), None)
    if current_index is None:
        run.status = "completed"
        run.updated_at = scenario_now_iso()
        return run
    current = run.steps[current_index]
    approved = any(item.startswith("人工审批通过") for item in current.evidence)
    if current.risk == "high" and not approved:
        if current.status == "waiting_approval":
            raise HTTPException(409, "high-risk step requires approval before execution")
        now = scenario_now_iso()
        current.status = "waiting_approval"
        run.status = "waiting_approval"
        run.updated_at = now
        run.audit.append(f"{now} {current.title} 需要人工审批，已阻断执行")
        return run
    now = scenario_now_iso()
    current.status = "completed"
    current.evidence.append(f"演示执行记录：{current.action}")
    run.audit.append(f"{now} 完成步骤：{current.title}")
    next_step = run.steps[current_index + 1] if current_index + 1 < len(run.steps) else None
    if next_step:
        next_step.status = "running"
        run.current_step_id = next_step.id
        run.status = "running"
    else:
        run.current_step_id = None
        run.status = "completed"
    run.updated_at = now
    return run


@app.post("/api/v1/scenario-runs/{run_id}/approve", response_model=ScenarioRun, tags=["scenarios"])
def approve_scenario_run(run_id: str) -> ScenarioRun:
    run = SCENARIO_RUNS.get(run_id)
    if not run:
        raise HTTPException(404, "scenario run not found")
    current = next((item for item in run.steps if item.id == run.current_step_id), None)
    if run.status != "waiting_approval" or current is None or current.risk != "high":
        raise HTTPException(409, "scenario run is not waiting for a high-risk approval")
    run.approvals_granted += 1
    now = scenario_now_iso()
    current.evidence.append(f"人工审批通过：{now}")
    current.status = "running"
    run.status = "running"
    run.audit.append(f"{now} 人工审批通过：{current.title}")
    run.updated_at = now
    return run


@app.get("/api/v1/incidents", response_model=list[Incident], tags=["aiops"])
def incidents(status: str | None = Query(None), severity: str | None = Query(None)) -> list[Incident]:
    return [i for i in INCIDENTS if (not status or i.status == status) and (not severity or i.severity == severity)]


@app.get("/api/v1/incidents/{incident_id}", response_model=Incident, tags=["aiops"])
def incident_detail(incident_id: str) -> Incident:
    for incident in INCIDENTS:
        if incident.id == incident_id:
            return incident
    raise HTTPException(404, "incident not found")


@app.post("/api/v1/incidents/read", tags=["aiops"])
def mark_incidents_read(payload: IncidentReadRequest) -> dict[str, Any]:
    selected = set(payload.incident_ids)
    candidates = INCIDENTS if not selected else [item for item in INCIDENTS if item.id in selected]
    return {"count": len(candidates), "marked_at": now_iso()}


@app.post("/api/v1/incidents/{incident_id}/claim", response_model=Incident, tags=["aiops"])
def claim_incident(incident_id: str) -> Incident:
    for incident in INCIDENTS:
        if incident.id == incident_id:
            if incident.status not in ("resolved", "closed"):
                incident.status = "investigating"
            return incident
    raise HTTPException(404, "incident not found")


@app.get("/api/v1/assets", response_model=list[Asset], tags=["governance"])
def assets(search: str | None = Query(None), type: str | None = Query(None)) -> list[Asset]:
    return [a for a in ASSETS if (not search or search.lower() in (a.name + a.description).lower()) and (not type or a.type == type)]


@app.get("/api/v1/assets/{asset_id}", response_model=Asset, tags=["governance"])
def asset_detail(asset_id: str) -> Asset:
    for asset in ASSETS:
        if asset.id == asset_id:
            return asset
    raise HTTPException(404, "asset not found")


@app.post("/api/v1/assets/{asset_id}/governance-tasks", response_model=GovernanceTask, status_code=201, tags=["governance"])
def create_governance_task(asset_id: str, payload: GovernanceTaskRequest) -> GovernanceTask:
    asset_detail(asset_id)
    if payload.asset_id != asset_id:
        raise HTTPException(400, "asset_id does not match path")
    task = GovernanceTask(
        task_id=f"gov-{uuid4().hex[:10]}",
        asset_id=asset_id,
        title=payload.title,
        description=payload.description,
        status="draft",
        created_at=now_iso(),
    )
    GOVERNANCE_TASKS[task.task_id] = task
    return task
