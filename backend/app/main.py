from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeDocumentCreate,
    KnowledgeFeedback,
    KnowledgeFeedbackCreate,
    KnowledgeQuery,
    KnowledgeQueryResult,
    add_feedback,
    add_document,
    create_knowledge_base,
    list_document_chunks,
    list_documents,
    list_queries,
    query_knowledge_base,
)


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
    Asset(id="asset-orders", name="dwd_orders", type="table", owner="数据平台组", status="certified", database="warehouse", description="订单明细事实表，供经营分析和履约监控使用。", columns=[{"name": "order_id", "type": "bigint", "sensitivity": "internal"}, {"name": "customer_id", "type": "bigint", "sensitivity": "restricted"}, {"name": "amount", "type": "decimal", "sensitivity": "internal"}], upstream=["ods_orders"], downstream=["ads_sales_daily", "rpt_order_fulfillment"]),
    Asset(id="asset-sales", name="ads_sales_daily", type="table", owner="经营分析组", status="certified", database="warehouse", description="按日汇总销售指标宽表。", columns=[{"name": "stat_date", "type": "date", "sensitivity": "public"}, {"name": "gmv", "type": "decimal", "sensitivity": "internal"}], upstream=["dwd_orders"], downstream=["dashboard_sales"]),
    Asset(id="asset-order-sync", name="order_sync_lag", type="metric", owner="SRE", status="active", database="observability", description="订单同步 Kafka consumer lag 指标。", columns=[{"name": "value", "type": "gauge", "sensitivity": "internal"}], upstream=[], downstream=["inc-1001"]),
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
DATASET_DIR = Path(os.getenv("DATASET_STORAGE_DIR", tempfile.gettempdir() + "/aegis-datasets"))
DATASET_DIR.mkdir(parents=True, exist_ok=True)

KNOWLEDGE_ALLOWED_SUFFIXES = {".txt", ".md", ".markdown", ".html", ".htm", ".json", ".sql", ".ddl"}
KNOWLEDGE_MAX_FILE_BYTES = 4 * 1024 * 1024

app = FastAPI(title="Data AI Explorer API", version="0.2.0", description="企业 AI 落地平台的智能问数和数据目录 API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def chart_spec(columns: list[str], rows: list[list[Any]], title: str) -> dict[str, Any]:
    if not columns or not rows:
        return {"type": "table", "title": title, "option": {}}
    x = columns[0]
    numeric_index = next((i for i, name in enumerate(columns[1:], start=1) if any(isinstance(row[i], (int, float)) for row in rows)), 1 if len(columns) > 1 else 0)
    y = columns[numeric_index]
    return {"type": "line", "title": title, "xField": x, "yField": y, "option": {"xAxis": {"type": "category", "data": [row[0] for row in rows]}, "yAxis": {"type": "value"}, "series": [{"type": "line", "smooth": True, "data": [row[numeric_index] for row in rows]}]}}


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
    for schema in catalog.schemas:
        for item in schema.tables:
            names = {column.name.lower() for column in item.columns}
            if "gmv" in names or "amount" in names:
                table = f"{schema.name}.{item.name}"
                value_column = "gmv" if "gmv" in names else "amount"
                date_column = next((name for name in names if "date" in name or "created" in name), date_column)
                break
    if any(word in question.lower() for word in ("趋势", "trend", "每天", "按日")):
        return f"SELECT {date_column}, SUM({value_column}) AS total_value FROM {table} GROUP BY {date_column} ORDER BY {date_column}"
    return f"SELECT {date_column}, SUM({value_column}) AS total_value FROM {table} GROUP BY {date_column} ORDER BY {date_column} LIMIT 100"


def catalog_context(catalog: TidbCatalog) -> str:
    return "\n".join(f"{schema.name}.{table.name}: " + ", ".join(f"{column.name} {column.data_type} -- {column.comment or ''}" for column in table.columns) for schema in catalog.schemas for table in schema.tables)


async def model_sql(question: str, catalog: TidbCatalog) -> str:
    endpoint = os.getenv("MODEL_GATEWAY_BASE_URL", "").strip()
    model = os.getenv("MODEL_GATEWAY_MODEL", "")
    if not endpoint or not model:
        return heuristic_sql(question, catalog)
    payload = {"model": model, "temperature": 0, "messages": [{"role": "system", "content": "You generate one read-only TiDB SELECT statement. Return SQL only."}, {"role": "user", "content": f"Schema:\n{catalog_context(catalog)}\nQuestion: {question}"}]}
    headers = {}
    if os.getenv("MODEL_GATEWAY_API_KEY"):
        headers["Authorization"] = f"Bearer {os.environ['MODEL_GATEWAY_API_KEY']}"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(endpoint.rstrip("/") + "/v1/chat/completions", json=payload, headers=headers)
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


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "data-ai-explorer", "time": now_iso()}


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


@app.get("/api/v1/knowledge-bases/{knowledge_base_id}", response_model=KnowledgeBaseRecord, tags=["knowledge"])
def get_knowledge_base(knowledge_base_id: str) -> KnowledgeBaseRecord:
    knowledge_base = KNOWLEDGE_BASES.get(knowledge_base_id)
    if not knowledge_base:
        raise HTTPException(404, "knowledge base not found")
    return knowledge_base


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


@app.get("/api/v1/assets", response_model=list[Asset], tags=["governance"])
def assets(search: str | None = Query(None), type: str | None = Query(None)) -> list[Asset]:
    return [a for a in ASSETS if (not search or search.lower() in (a.name + a.description).lower()) and (not type or a.type == type)]


@app.get("/api/v1/assets/{asset_id}", response_model=Asset, tags=["governance"])
def asset_detail(asset_id: str) -> Asset:
    for asset in ASSETS:
        if asset.id == asset_id:
            return asset
    raise HTTPException(404, "asset not found")
