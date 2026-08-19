from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlglot import exp, parse
from sqlglot.errors import ParseError


PROFILE_PATH = Path(__file__).with_name("tidb_optimizer_profiles.json")
VERSION_RE = re.compile(r"(?i)^v?(\d+)\.(\d+)(?:\.(\d+))?(?:[-+].*)?$")
MAX_INPUT_BYTES = 2 * 1024 * 1024
ALLOWED_SQL_SUFFIXES = {".sql", ".ddl", ".txt"}


class SQLOptimizeRequest(BaseModel):
    sql: str = Field(min_length=1, max_length=200_000)
    ddl: str = Field(default="", max_length=400_000)
    tidb_version: str = Field(default="8.5", min_length=3, max_length=64)
    plan_mode: Literal["simulate", "live"] = "simulate"
    mcp_endpoint: str | None = Field(default=None, max_length=2048)


class SQLDirectoryRequest(BaseModel):
    path: str = Field(min_length=1, max_length=1024)


class PlanNode(BaseModel):
    id: str
    est_rows: str = "unknown"
    task: str
    access_object: str = ""
    operator_info: str = ""
    risk: Literal["low", "medium", "high"] = "low"


class SQLRecommendation(BaseModel):
    id: str
    severity: Literal["info", "warning", "critical"]
    category: str
    title: str
    rationale: str
    action: str
    evidence: list[str] = Field(default_factory=list)


class SQLInputItem(BaseModel):
    name: str
    sql: str


class SQLInputBundle(BaseModel):
    files: list[str] = Field(default_factory=list)
    sql_items: list[SQLInputItem] = Field(default_factory=list)
    ddl: str = ""


class SQLOptimizeResponse(BaseModel):
    analysis_id: str
    requested_version: str
    profile_version: str
    optimizer_mode: Literal["simulated", "live"]
    confidence: Literal["low", "medium", "high"]
    version_verified: bool
    actual_tidb_version: str | None = None
    summary: str
    tables: list[str] = Field(default_factory=list)
    plan: list[PlanNode] = Field(default_factory=list)
    recommendations: list[SQLRecommendation] = Field(default_factory=list)
    version_features: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    sources: list[dict[str, str]] = Field(default_factory=list)


def load_profiles() -> list[dict[str, Any]]:
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


TIDB_PROFILES = load_profiles()
PROFILE_BY_MINOR = {item["minor"]: item for item in TIDB_PROFILES}


def normalize_version(value: str) -> tuple[str, str]:
    match = VERSION_RE.match(value.strip())
    if not match:
        raise HTTPException(422, "TiDB version must look like 7.5, 7.5.6, v8.5.0, or an equivalent release string")
    major, minor, patch = match.groups()
    profile = f"{major}.{minor}"
    if profile not in PROFILE_BY_MINOR:
        raise HTTPException(422, f"unsupported TiDB optimizer profile: {profile}")
    normalized = f"{major}.{minor}" + (f".{patch}" if patch is not None else "")
    return normalized, profile


def parse_read_query(sql: str) -> exp.Expression:
    try:
        statements = [statement for statement in parse(sql, read="mysql") if statement is not None]
    except ParseError as exc:
        raise HTTPException(422, f"SQL parse failed: {exc.errors[0].get('description', 'invalid SQL')}") from exc
    if len(statements) != 1:
        raise HTTPException(422, "an optimization request must contain exactly one SQL statement")
    statement = statements[0]
    if any(statement.find(kind) for kind in (exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Drop, exp.Alter)):
        raise HTTPException(400, "live or simulated optimization only accepts read-only SELECT/CTE statements")
    if statement.find(exp.Select) is None:
        raise HTTPException(400, "only SELECT/CTE statements can be optimized")
    return statement


def split_sql_document(name: str, content: str) -> tuple[list[SQLInputItem], list[str]]:
    queries: list[SQLInputItem] = []
    ddl: list[str] = []
    try:
        statements = [statement for statement in parse(content, read="mysql") if statement is not None]
    except ParseError:
        if Path(name).suffix.lower() == ".ddl" or re.match(r"(?is)^\s*(create|alter)\s+table\b", content):
            return [], [content.strip()]
        return [SQLInputItem(name=name, sql=content.strip())], []
    query_number = 0
    for statement in statements:
        rendered = statement.sql(dialect="mysql", pretty=True)
        if isinstance(statement, (exp.Create, exp.Alter)):
            ddl.append(rendered + ";")
        elif statement.find(exp.Select) is not None:
            query_number += 1
            label = name if len(statements) == 1 else f"{name} #{query_number}"
            queries.append(SQLInputItem(name=label, sql=rendered + ";"))
    return queries, ddl


def bundle_from_files(files: list[tuple[str, bytes]]) -> SQLInputBundle:
    names: list[str] = []
    queries: list[SQLInputItem] = []
    ddl_parts: list[str] = []
    total_size = 0
    for name, payload in files:
        suffix = Path(name).suffix.lower()
        if suffix not in ALLOWED_SQL_SUFFIXES:
            raise HTTPException(415, f"unsupported SQL input file: {name}")
        total_size += len(payload)
        if len(payload) > MAX_INPUT_BYTES or total_size > MAX_INPUT_BYTES * 10:
            raise HTTPException(413, "SQL input exceeds the configured size limit")
        try:
            content = payload.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise HTTPException(400, f"SQL input must be UTF-8: {name}") from exc
        file_queries, file_ddl = split_sql_document(name, content)
        names.append(name)
        queries.extend(file_queries)
        ddl_parts.extend(file_ddl)
    return SQLInputBundle(files=names, sql_items=queries, ddl="\n\n".join(ddl_parts))


def version_matches(requested: str, actual: str) -> bool:
    requested_match = VERSION_RE.match(requested.lstrip("v").split("-")[0])
    actual_matches = re.findall(r"(?i)v?(\d+)\.(\d+)\.(\d+)", actual)
    if not requested_match or not actual_matches:
        return False
    requested_parts = requested_match.groups()
    actual_parts = actual_matches[-1]
    if requested_parts[2] is None:
        return requested_parts[:2] == actual_parts[:2]
    return requested_parts == actual_parts


def extract_columns(node: exp.Expression | None) -> list[exp.Column]:
    if node is None:
        return []
    return list(node.find_all(exp.Column))


def qualified_column(column: exp.Column) -> tuple[str, str]:
    return (column.table or "", column.name)


def existing_indexes(ddl: str) -> dict[str, list[tuple[str, ...]]]:
    indexes: dict[str, list[tuple[str, ...]]] = {}
    for table_match in re.finditer(r"(?is)create\s+table\s+`?([\w.]+)`?\s*\((.*?)(?:;|\Z)", ddl):
        table, body = table_match.groups()
        found: list[tuple[str, ...]] = []
        for index_match in re.finditer(r"(?is)(?:primary\s+key|unique\s+(?:key|index)(?:\s+`?\w+`?)?|(?:key|index)\s+`?\w+`?)\s*\(([^)]+)\)", body):
            columns = tuple(re.sub(r"\(\d+\)$", "", item.strip().strip("`")) for item in index_match.group(1).split(","))
            found.append(columns)
        indexes[table.lower()] = found
    return indexes


def table_aliases(statement: exp.Expression) -> tuple[list[str], dict[str, str]]:
    tables: list[str] = []
    aliases: dict[str, str] = {}
    for table in statement.find_all(exp.Table):
        name = ".".join(part for part in (table.catalog, table.db, table.name) if part)
        if name not in tables:
            tables.append(name)
        aliases[table.alias_or_name] = name
        aliases[table.name] = name
    return tables, aliases


def columns_by_table(columns: list[exp.Column], aliases: dict[str, str], default_table: str) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for column in columns:
        table = aliases.get(column.table, column.table) if column.table else default_table
        grouped.setdefault(table or default_table, [])
        if column.name not in grouped[table or default_table]:
            grouped[table or default_table].append(column.name)
    return grouped


def recommendation(
    rec_id: str,
    severity: Literal["info", "warning", "critical"],
    category: str,
    title: str,
    rationale: str,
    action: str,
    evidence: list[str],
) -> SQLRecommendation:
    return SQLRecommendation(id=rec_id, severity=severity, category=category, title=title, rationale=rationale, action=action, evidence=evidence)


def static_recommendations(statement: exp.Expression, ddl: str, profile: dict[str, Any], tables: list[str], aliases: dict[str, str]) -> list[SQLRecommendation]:
    recs: list[SQLRecommendation] = []
    select = statement.find(exp.Select)
    where = statement.find(exp.Where)
    joins = list(statement.find_all(exp.Join))
    group = statement.find(exp.Group)
    order = statement.find(exp.Order)
    default_table = tables[0] if len(tables) == 1 else ""
    equality_columns: list[exp.Column] = []
    range_columns: list[exp.Column] = []
    for condition in statement.find_all(exp.EQ):
        equality_columns.extend(extract_columns(condition))
    for condition_type in (exp.GT, exp.GTE, exp.LT, exp.LTE, exp.Between, exp.Like):
        for condition in statement.find_all(condition_type):
            range_columns.extend(extract_columns(condition))
    group_order_columns = extract_columns(group) if group is not None else extract_columns(order)
    candidates = columns_by_table(equality_columns + group_order_columns + range_columns, aliases, default_table)
    known_indexes = existing_indexes(ddl)
    for table, columns in candidates.items():
        if not table or not columns:
            continue
        candidate = tuple(columns[:5])
        table_indexes = known_indexes.get(table.lower(), []) + known_indexes.get(table.split(".")[-1].lower(), [])
        covered = any(index[: len(candidate)] == candidate for index in table_indexes)
        if not covered:
            index_name = "idx_ai_" + "_".join(candidate)[:48]
            quoted = ", ".join(f"`{column}`" for column in candidate)
            qualified_table = ".".join(f"`{part}`" for part in table.split("."))
            recs.append(recommendation(
                f"index-{table}", "warning", "index", f"评估 {table} 的复合索引",
                "沿用 SQLAdvisor 的等值条件优先、GROUP/ORDER 次之、范围条件最后的候选列排序，并结合 TiDB 执行计划再验证。",
                f"CREATE INDEX `{index_name}` ON {qualified_table} ({quoted});",
                [f"候选列: {', '.join(candidate)}", "DDL 中未发现相同左前缀索引"],
            ))
    if select is not None and any(isinstance(item, exp.Star) or item.find(exp.Star) for item in select.expressions):
        recs.append(recommendation("select-star", "warning", "rewrite", "避免 SELECT *", "多余列会增加 TiKV/TiFlash 扫描、网络传输和解码开销，也降低覆盖索引机会。", "只保留业务实际需要的列。", ["SELECT 列表包含 *"]))
    if where is None and tables:
        recs.append(recommendation("full-scan", "critical", "scan", "确认全表扫描是否符合预期", "缺少过滤条件时，优化器通常只能扫描完整访问对象；大表会放大 TiKV IO 和网络开销。", "增加可选择的谓词、分区范围或业务 LIMIT，并用真实 EXPLAIN ANALYZE 验证。", ["未检测到 WHERE 条件"]))
    if joins and any(join.args.get("on") is None and not join.args.get("using") for join in joins):
        recs.append(recommendation("cartesian-join", "critical", "join", "消除笛卡尔连接", "JOIN 缺少 ON/USING 会放大中间结果集并导致高内存和网络消耗。", "补充明确的关联条件，并为被驱动表关联列评估索引。", ["存在无 ON/USING 的 JOIN"]))
    leading_like = [item.sql(dialect="mysql") for item in statement.find_all(exp.Like) if isinstance(item.expression, exp.Literal) and str(item.expression.this).startswith("%")]
    if leading_like:
        recs.append(recommendation("leading-like", "warning", "predicate", "前导通配 LIKE 难以使用普通 B-Tree 索引", "SQLAdvisor 同样会丢弃非前缀 LIKE 条件；TiDB 通常需要扫描后过滤。", "改为前缀匹配，或评估全文检索/业务倒排索引。", leading_like))
    wrapped = []
    for predicate in list(statement.find_all(exp.EQ)) + list(statement.find_all(exp.GT)) + list(statement.find_all(exp.GTE)) + list(statement.find_all(exp.LT)) + list(statement.find_all(exp.LTE)):
        if isinstance(predicate.this, exp.Func):
            wrapped.append(predicate.sql(dialect="mysql"))
    if wrapped:
        recs.append(recommendation("function-column", "warning", "predicate", "避免在过滤列外层包裹函数", "函数计算可能阻碍普通索引 Range 构造和分区裁剪。", "将函数移到常量侧，或评估生成列及其索引。", wrapped[:5]))
    sql_upper = statement.sql(dialect="mysql").upper()
    if "INL_MERGE_JOIN" in sql_upper and profile["minor"] >= "8.3":
        recs.append(recommendation("deprecated-hint", "critical", "version", "移除 INL_MERGE_JOIN Hint", "该 Hint 从 TiDB 8.3 起废弃且不再生效。", "删除 Hint，并根据真实计划选择 INL_JOIN、HASH_JOIN 或 Plan Binding。", [profile["label"]]))
    if statement.find(exp.Or) is not None:
        if profile["minor"] >= "8.0":
            action = "检查 Index Merge 候选路径、统计信息和回表成本；在 8.1+ 可结合 Optimizer Fix Controls 验证选择差异。"
        else:
            action = "考虑拆分为 UNION ALL 或建立能覆盖主要分支的复合索引，并对比真实 EXPLAIN。"
        recs.append(recommendation("or-index-merge", "info", "version", "验证 OR 谓词的 Index Merge 行为", "不同 TiDB minor 对 Index Merge、排序要求和多值索引的支持不同。", action, [profile["label"]]))
    if profile["minor"] >= "8.3" and (where is not None or joins or group is not None):
        predicate_columns = [column.name for column in extract_columns(where) + [column for join in joins for column in extract_columns(join.args.get("on"))] + extract_columns(group)]
        if predicate_columns:
            recs.append(recommendation("predicate-stats", "info", "statistics", "确保谓词与关联列具有新鲜统计信息", "TiDB 8.3+ 新集群默认按 PREDICATE 收集必要列统计；临时 SQL 或升级集群可能仍缺少关键列统计。", "检查 SHOW STATS_HEALTHY / SHOW STATS_HISTOGRAMS，必要时 ANALYZE TABLE 并显式指定列。", list(dict.fromkeys(predicate_columns))[:8]))
    else:
        recs.append(recommendation("stats-health", "info", "statistics", "先验证统计信息健康度", "TiDB 的基数估算直接影响访问路径、Join 顺序和算子选择。", "检查统计健康度、修改行数和全局分区统计，避免仅凭模拟计划创建索引。", [profile["label"]]))
    if not recs:
        recs.append(recommendation("verify-live", "info", "verification", "使用真实 EXPLAIN ANALYZE 做最终验证", "静态分析未发现明显结构问题，但模拟器没有真实数据分布、统计信息和集群拓扑。", "在预发布或只读副本执行 EXPLAIN ANALYZE，并比较 actRows、execution info 与 memory/disk。", []))
    return recs


def simulated_plan(statement: exp.Expression, tables: list[str], recommendations: list[SQLRecommendation]) -> list[PlanNode]:
    nodes: list[PlanNode] = []
    if statement.find(exp.Limit) is not None:
        nodes.append(PlanNode(id="Limit", est_rows="bounded", task="root", operator_info=statement.find(exp.Limit).sql(dialect="mysql")))
    if statement.find(exp.Order) is not None:
        nodes.append(PlanNode(id="Sort", task="root", operator_info=statement.find(exp.Order).sql(dialect="mysql"), risk="medium"))
    if statement.find(exp.Group) is not None:
        nodes.append(PlanNode(id="HashAgg", task="root", operator_info=statement.find(exp.Group).sql(dialect="mysql"), risk="medium"))
    joins = list(statement.find_all(exp.Join))
    if joins:
        cartesian = any(join.args.get("on") is None and not join.args.get("using") for join in joins)
        nodes.append(PlanNode(id="HashJoin", task="root", access_object=", ".join(tables), operator_info="inner join; build/probe order requires statistics", risk="high" if cartesian else "medium"))
    has_index_candidate = any(item.category == "index" for item in recommendations)
    for table in tables or ["derived result"]:
        if statement.find(exp.Where) is not None and has_index_candidate:
            nodes.append(PlanNode(id="IndexRangeScan (hypothesis)", est_rows="stats required", task="cop[tikv]", access_object=table, operator_info="range derived from equality/range predicates", risk="medium"))
        else:
            nodes.append(PlanNode(id="TableFullScan (hypothesis)", est_rows="table stats required", task="cop[tikv]", access_object=table, operator_info="no verified usable index path", risk="high"))
    return nodes


def live_plan_nodes(rows: list[dict[str, Any]]) -> list[PlanNode]:
    nodes: list[PlanNode] = []
    for row in rows:
        lowered = {str(key).lower(): value for key, value in row.items()}
        identifier = lowered.get("id") or lowered.get("operator") or next(iter(row.values()), "Plan")
        task = lowered.get("task") or "root"
        access = lowered.get("access object") or lowered.get("access_object") or ""
        info = lowered.get("operator info") or lowered.get("operator_info") or ""
        est_rows = lowered.get("estrows") or lowered.get("est rows") or lowered.get("est_rows") or "unknown"
        identifier_text = str(identifier)
        risk: Literal["low", "medium", "high"] = "high" if "FullScan" in identifier_text else "medium" if any(token in identifier_text for token in ("HashJoin", "Sort", "HashAgg")) else "low"
        nodes.append(PlanNode(id=identifier_text, est_rows=str(est_rows), task=str(task), access_object=str(access), operator_info=str(info), risk=risk))
    return nodes


def analyze_sql(request: SQLOptimizeRequest, live_rows: list[dict[str, Any]] | None = None, actual_version: str | None = None) -> SQLOptimizeResponse:
    normalized_version, profile_minor = normalize_version(request.tidb_version)
    profile = PROFILE_BY_MINOR[profile_minor]
    statement = parse_read_query(request.sql)
    tables, aliases = table_aliases(statement)
    recommendations = static_recommendations(statement, request.ddl, profile, tables, aliases)
    is_live = live_rows is not None and actual_version is not None
    plan = live_plan_nodes(live_rows or []) if is_live else simulated_plan(statement, tables, recommendations)
    assumptions = [] if is_live else [
        "这是版本感知的计划假设，不是 TiDB 编译器或真实 EXPLAIN 输出。",
        "模拟器没有真实统计信息、索引可见性、分区元数据、TiFlash 副本、会话变量和集群拓扑。",
        "输入具体 patch 版本时仍使用对应 minor 规则包；patch 级优化器修复必须连接同版本 TiDB 验证。",
    ]
    mode: Literal["simulated", "live"] = "live" if is_live else "simulated"
    critical = sum(item.severity == "critical" for item in recommendations)
    warnings = sum(item.severity == "warning" for item in recommendations)
    summary = f"识别 {len(tables)} 张表，生成 {len(plan)} 个计划节点和 {len(recommendations)} 条建议"
    if critical or warnings:
        summary += f"，其中 {critical} 条高风险、{warnings} 条需评估"
    return SQLOptimizeResponse(
        analysis_id=f"sqlo-{uuid4().hex[:10]}",
        requested_version=normalized_version,
        profile_version=profile_minor,
        optimizer_mode=mode,
        confidence="high" if is_live else "medium",
        version_verified=is_live,
        actual_tidb_version=actual_version,
        summary=summary,
        tables=tables,
        plan=plan,
        recommendations=recommendations,
        version_features=profile["features"],
        assumptions=assumptions,
        sources=[
            {"label": "TiDB planner source", "url": profile["source"], "ref": profile["code_commit"]},
            {"label": "TiDB release notes", "url": profile["release_notes"], "ref": profile["code_tag"]},
            {"label": "SQLAdvisor methodology", "url": "https://github.com/Meituan-Dianping/SQLAdvisor", "ref": "where/join/group/order/cardinality/index"},
        ],
    )
