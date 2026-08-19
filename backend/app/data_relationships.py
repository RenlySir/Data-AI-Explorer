from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from itertools import combinations
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlglot import exp, parse
from sqlglot.errors import ParseError


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


NodeKind = Literal["schema", "table", "column"]
EdgeLevel = Literal["structure", "table", "field"]


class RelationshipNode(BaseModel):
    id: str
    label: str
    kind: NodeKind
    parent_id: str | None = None
    schema_name: str | None = None
    table_name: str | None = None
    data_type: str | None = None
    comment: str | None = None


class RelationshipEdge(BaseModel):
    id: str
    source: str
    target: str
    kind: str
    level: EdgeLevel
    source_type: Literal["metadata", "sql", "structure"]
    observation_count: int = 1
    confidence: float = Field(ge=0, le=1)
    first_seen_at: str
    last_seen_at: str


class SqlObservationRequest(BaseModel):
    sql: str = Field(min_length=1, max_length=100_000)
    source: str = Field(default="manual", min_length=1, max_length=100)


class SqlObservationRecord(BaseModel):
    id: str
    digest: str
    sql_preview: str
    source: str
    execution_count: int
    relationship_ids: list[str]
    first_seen_at: str
    last_seen_at: str


class SqlCollectorUpdate(BaseModel):
    enabled: bool
    interval_seconds: int = Field(default=30, ge=30, le=86_400)


class SqlCollectorStatus(BaseModel):
    datasource_id: str
    enabled: bool
    interval_seconds: int
    last_collected_at: str | None = None
    last_error: str | None = None


class RelationshipSnapshot(BaseModel):
    datasource_id: str
    datasource_name: str
    database: str
    source: str
    schemas: list[dict[str, Any]]
    nodes: list[RelationshipNode]
    edges: list[RelationshipEdge]
    sql_observations: list[SqlObservationRecord]
    collected_at: str


SQL_OBSERVATIONS: dict[str, dict[str, SqlObservationRecord]] = {}
SQL_EDGES: dict[str, dict[str, RelationshipEdge]] = {}
QUERY_LOG_COUNTS: dict[str, dict[str, int]] = {}


def clear_datasource_relationships(datasource_id: str) -> None:
    SQL_OBSERVATIONS.pop(datasource_id, None)
    SQL_EDGES.pop(datasource_id, None)
    QUERY_LOG_COUNTS.pop(datasource_id, None)


def _edge_id(source: str, target: str, kind: str, level: str) -> str:
    raw = f"{source}|{target}|{kind}|{level}"
    return "rel-" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:14]


def _canonical_table(table: exp.Table, default_schema: str) -> str:
    schema = table.db or default_schema
    return f"{schema}.{table.name}" if schema else table.name


def _table_from_field(field: str) -> str:
    parts = field.split(".")
    return ".".join(parts[:-1]) if len(parts) >= 3 else field


def _normalized_redacted_sql(sql: str) -> str:
    statements = parse(sql, read="mysql")
    return "; ".join(
        statement.transform(
            lambda node: exp.Placeholder() if isinstance(node, exp.Literal) else node
        ).sql(dialect="mysql")
        for statement in statements
    )


def parse_sql_edges(sql: str, default_schema: str) -> list[tuple[str, str, str, EdgeLevel]]:
    try:
        statements = parse(sql, read="mysql")
    except ParseError as exc:
        raise ValueError(f"SQL cannot be parsed: {exc}") from exc

    discovered: set[tuple[str, str, str, EdgeLevel]] = set()
    query_count = 0
    for statement in statements:
        if not isinstance(statement, (exp.Query, exp.Select, exp.Union)):
            continue
        query_count += 1
        cte_names = {cte.alias_or_name.lower() for cte in statement.find_all(exp.CTE)}
        alias_map: dict[str, str] = {}
        table_names: list[str] = []
        for table in statement.find_all(exp.Table):
            if table.name.lower() in cte_names:
                continue
            canonical = _canonical_table(table, default_schema)
            alias_map[table.alias_or_name.lower()] = canonical
            alias_map[table.name.lower()] = canonical
            if canonical not in table_names:
                table_names.append(canonical)

        explicit_table_pairs: set[tuple[str, str]] = set()
        for equality in statement.find_all(exp.EQ):
            left, right = equality.this, equality.expression
            if not isinstance(left, exp.Column) or not isinstance(right, exp.Column):
                continue
            if not left.table or not right.table:
                continue
            left_table = alias_map.get(left.table.lower())
            right_table = alias_map.get(right.table.lower())
            if not left_table or not right_table or left_table == right_table:
                continue
            left_field = f"{left_table}.{left.name}"
            right_field = f"{right_table}.{right.name}"
            discovered.add((left_field, right_field, "sql_join", "field"))
            pair = tuple(sorted((left_table, right_table)))
            explicit_table_pairs.add(pair)
            discovered.add((pair[0], pair[1], "sql_join", "table"))

        for left_table, right_table in combinations(sorted(table_names), 2):
            pair = (left_table, right_table)
            if pair not in explicit_table_pairs:
                discovered.add((left_table, right_table, "co_query", "table"))
    if not query_count:
        raise ValueError("only SELECT or WITH queries can be collected")
    return sorted(discovered)


def ingest_sql(
    datasource_id: str,
    sql: str,
    default_schema: str,
    source: str,
    execution_count: int = 1,
    cumulative: bool = False,
) -> SqlObservationRecord:
    try:
        normalized = _normalized_redacted_sql(sql)
    except ParseError as exc:
        raise ValueError(f"SQL cannot be parsed: {exc}") from exc
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    count = max(int(execution_count), 1)
    if cumulative:
        previous_count = QUERY_LOG_COUNTS.setdefault(datasource_id, {}).get(digest, 0)
        QUERY_LOG_COUNTS[datasource_id][digest] = count
        count = max(count - previous_count, 0)

    now = now_iso()
    observations = SQL_OBSERVATIONS.setdefault(datasource_id, {})
    existing = observations.get(digest)
    edges = parse_sql_edges(sql, default_schema)
    relation_ids: list[str] = []
    edge_store = SQL_EDGES.setdefault(datasource_id, {})
    for source_id, target_id, kind, level in edges:
        edge_id = _edge_id(source_id, target_id, kind, level)
        relation_ids.append(edge_id)
        current = edge_store.get(edge_id)
        confidence = min(0.96, 0.68 + 0.04 * max((current.observation_count if current else 0) + count, 1))
        edge_store[edge_id] = RelationshipEdge(
            id=edge_id,
            source=source_id,
            target=target_id,
            kind=kind,
            level=level,
            source_type="sql",
            observation_count=(current.observation_count if current else 0) + count,
            confidence=confidence,
            first_seen_at=current.first_seen_at if current else now,
            last_seen_at=now if count else (current.last_seen_at if current else now),
        )

    record = SqlObservationRecord(
        id="sql-" + digest[:12],
        digest=digest,
        sql_preview=normalized[:500],
        source=source,
        execution_count=(existing.execution_count if existing else 0) + count,
        relationship_ids=sorted(set((existing.relationship_ids if existing else []) + relation_ids)),
        first_seen_at=existing.first_seen_at if existing else now,
        last_seen_at=now if count else (existing.last_seen_at if existing else now),
    )
    observations[digest] = record
    return record


def _metadata_edge(source: str, target: str, kind: str, level: EdgeLevel) -> RelationshipEdge:
    now = now_iso()
    confidence = 0.99 if kind == "foreign_key" else 0.86
    return RelationshipEdge(
        id=_edge_id(source, target, kind, level),
        source=source,
        target=target,
        kind=kind,
        level=level,
        source_type="metadata",
        observation_count=1,
        confidence=confidence,
        first_seen_at=now,
        last_seen_at=now,
    )


def build_snapshot(datasource_id: str, datasource_name: str, catalog: Any) -> RelationshipSnapshot:
    nodes: dict[str, RelationshipNode] = {}
    edges: dict[str, RelationshipEdge] = {}
    for schema in catalog.schemas:
        schema_id = schema.name
        nodes[schema_id] = RelationshipNode(id=schema_id, label=schema.name, kind="schema", schema_name=schema.name)
        for table in schema.tables:
            table_id = f"{schema.name}.{table.name}"
            nodes[table_id] = RelationshipNode(
                id=table_id,
                label=table.name,
                kind="table",
                parent_id=schema_id,
                schema_name=schema.name,
                table_name=table.name,
                comment=table.comment,
            )
            structure = RelationshipEdge(
                id=_edge_id(schema_id, table_id, "contains", "structure"),
                source=schema_id,
                target=table_id,
                kind="contains",
                level="structure",
                source_type="structure",
                confidence=1,
                first_seen_at=catalog.collected_at,
                last_seen_at=catalog.collected_at,
            )
            edges[structure.id] = structure
            for column in table.columns:
                column_id = f"{table_id}.{column.name}"
                nodes[column_id] = RelationshipNode(
                    id=column_id,
                    label=column.name,
                    kind="column",
                    parent_id=table_id,
                    schema_name=schema.name,
                    table_name=table.name,
                    data_type=column.data_type,
                    comment=column.comment,
                )
                contains = RelationshipEdge(
                    id=_edge_id(table_id, column_id, "contains", "structure"),
                    source=table_id,
                    target=column_id,
                    kind="contains",
                    level="structure",
                    source_type="structure",
                    confidence=1,
                    first_seen_at=catalog.collected_at,
                    last_seen_at=catalog.collected_at,
                )
                edges[contains.id] = contains

    for relation in catalog.relationships:
        source = str(relation.get("from", ""))
        target = str(relation.get("to", ""))
        if not source or not target:
            continue
        level: EdgeLevel = "field" if len(source.split(".")) >= 3 and len(target.split(".")) >= 3 else "table"
        edge = _metadata_edge(source, target, str(relation.get("type") or "relationship"), level)
        edges[edge.id] = edge
        if level == "field":
            source_table, target_table = _table_from_field(source), _table_from_field(target)
            if source_table != target_table:
                table_edge = _metadata_edge(source_table, target_table, str(relation.get("type") or "relationship"), "table")
                edges[table_edge.id] = table_edge

    for edge in SQL_EDGES.get(datasource_id, {}).values():
        edges[edge.id] = edge

    return RelationshipSnapshot(
        datasource_id=datasource_id,
        datasource_name=datasource_name,
        database=catalog.database,
        source=catalog.source,
        schemas=[schema.model_dump() for schema in catalog.schemas],
        nodes=list(nodes.values()),
        edges=list(edges.values()),
        sql_observations=sorted(
            SQL_OBSERVATIONS.get(datasource_id, {}).values(),
            key=lambda item: item.last_seen_at,
            reverse=True,
        ),
        collected_at=catalog.collected_at,
    )
