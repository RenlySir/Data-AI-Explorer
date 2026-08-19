from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    datasource_id: str = "demo-warehouse"


class QueryOperation(BaseModel):
    operation_id: str
    status: str
    question: str
    sql: str | None = None
    answer: str | None = None
    columns: list[str] = []
    rows: list[list[Any]] = []
    evidence: list[dict[str, str]] = []
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

OPERATIONS: dict[str, QueryOperation] = {}

app = FastAPI(title="Data AI Explorer API", version="0.1.0", description="企业 AI 落地平台的可运行 MVP API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "data-ai-explorer", "time": now_iso()}


@app.get("/api/v1/workbench/summary", tags=["workbench"])
def workbench_summary() -> dict[str, Any]:
    open_incidents = [i for i in INCIDENTS if i.status not in ("resolved", "closed")]
    return {"metrics": {"open_incidents": len(open_incidents), "critical_incidents": sum(i.severity == "P1" for i in open_incidents), "managed_assets": len(ASSETS), "query_success_rate": 98.6}, "incidents": [i.model_dump() for i in open_incidents[:3]], "recent_queries": list(OPERATIONS.values())[-5:]}


@app.post("/api/v1/query/conversations", response_model=QueryOperation, status_code=202, tags=["query"])
def submit_query(payload: QueryRequest) -> QueryOperation:
    op_id = f"op-{uuid4().hex[:10]}"
    q = payload.question
    sql = "SELECT stat_date, SUM(gmv) AS gmv FROM ads_sales_daily WHERE stat_date >= CURRENT_DATE - INTERVAL '30 days' GROUP BY stat_date ORDER BY stat_date"
    operation = QueryOperation(operation_id=op_id, status="completed", question=q, sql=sql, answer="近30天销售额总体保持平稳，最近一天 GMV 为 128.6 万。", columns=["stat_date", "gmv"], rows=[["2026-08-17", 1213000], ["2026-08-18", 1286000]], evidence=[{"type": "asset", "label": "ads_sales_daily", "ref": "asset-sales"}, {"type": "policy", "label": "经营分析数据权限", "ref": "policy-sales-read"}], created_at=now_iso())
    OPERATIONS[op_id] = operation
    return operation


@app.get("/api/v1/query/operations/{operation_id}", response_model=QueryOperation, tags=["query"])
def query_status(operation_id: str) -> QueryOperation:
    operation = OPERATIONS.get(operation_id)
    if not operation:
        raise HTTPException(404, "query operation not found")
    return operation


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
