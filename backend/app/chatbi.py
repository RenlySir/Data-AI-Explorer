from __future__ import annotations

import ipaddress
import os
import socket
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, SecretStr

from app.tidb import configure_session


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


DataSourceKind = Literal["mysql", "tidb", "csv"]


class DataSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    kind: Literal["mysql", "tidb"]
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(ge=1, le=65535)
    database: str = Field(min_length=1, max_length=128)
    username: str = Field(min_length=1, max_length=128)
    password: SecretStr | None = None
    test_on_create: bool = True


class DataSourceRecord(BaseModel):
    id: str
    name: str
    kind: DataSourceKind
    status: Literal["ready", "unverified", "error"]
    host: str | None = None
    port: int | None = None
    database: str | None = None
    username: str | None = None
    dataset_id: str | None = None
    table_count: int = 0
    row_count: int | None = None
    last_error: str | None = None
    created_at: str
    last_tested_at: str | None = None


class ChatBIQuery(BaseModel):
    datasource_id: str
    question: str = Field(min_length=1, max_length=2000)


class ReportCreate(BaseModel):
    operation_id: str
    datasource_id: str
    title: str = Field(min_length=1, max_length=120)


class DashboardReport(BaseModel):
    id: str
    operation_id: str
    datasource_id: str
    datasource_name: str
    title: str
    question: str
    chart: dict[str, Any]
    columns: list[str]
    rows: list[list[Any]]
    accepted_by: str
    created_at: str


DATA_SOURCES: dict[str, DataSourceRecord] = {
    "ds-demo-tidb": DataSourceRecord(
        id="ds-demo-tidb",
        name="演示 TiDB 经营库",
        kind="tidb",
        status="ready",
        host=None,
        port=None,
        database="demo_tidb",
        username=None,
        table_count=3,
        created_at=now_iso(),
        last_tested_at=now_iso(),
    )
}
DATA_SOURCE_SECRETS: dict[str, str] = {}
DASHBOARD_REPORTS: dict[str, DashboardReport] = {}


def create_database_source(payload: DataSourceCreate) -> DataSourceRecord:
    datasource_id = f"src-{uuid4().hex[:10]}"
    item = DataSourceRecord(
        id=datasource_id,
        name=payload.name,
        kind=payload.kind,
        status="unverified",
        host=payload.host,
        port=payload.port,
        database=payload.database,
        username=payload.username,
        created_at=now_iso(),
    )
    DATA_SOURCES[item.id] = item
    DATA_SOURCE_SECRETS[item.id] = payload.password.get_secret_value() if payload.password else ""
    return item


def create_csv_source(name: str, dataset_id: str, row_count: int) -> DataSourceRecord:
    item = DataSourceRecord(
        id=f"src-{uuid4().hex[:10]}",
        name=name,
        kind="csv",
        status="ready",
        dataset_id=dataset_id,
        row_count=row_count,
        table_count=1,
        created_at=now_iso(),
        last_tested_at=now_iso(),
    )
    DATA_SOURCES[item.id] = item
    return item


def _host_allowed(host: str) -> bool:
    exact = {item.strip().lower() for item in os.getenv("CHATBI_ALLOWED_DB_HOSTS", "").split(",") if item.strip()}
    if host.lower() in exact:
        return True
    if os.getenv("CHATBI_ALLOW_PRIVATE_HOSTS", "true").lower() not in {"1", "true", "yes"}:
        return False
    try:
        addresses = {ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(host, None)}
    except (OSError, ValueError):
        return False
    return bool(addresses) and all(address.is_private or address.is_loopback for address in addresses)


def connect_database(item: DataSourceRecord):
    if item.kind not in {"mysql", "tidb"} or not item.host or not item.port or not item.database or not item.username:
        raise ValueError("database datasource configuration is incomplete")
    if not _host_allowed(item.host):
        raise PermissionError("database host is not allowlisted")
    try:
        import pymysql
    except ImportError as exc:
        raise RuntimeError("PyMySQL is not installed") from exc
    connection = pymysql.connect(
        host=item.host,
        port=item.port,
        user=item.username,
        password=DATA_SOURCE_SECRETS.get(item.id, ""),
        database=item.database,
        charset="utf8mb4",
        autocommit=True,
        connect_timeout=5,
        read_timeout=15,
        write_timeout=5,
        cursorclass=pymysql.cursors.DictCursor,
    )
    with connection.cursor() as cursor:
        configure_session(cursor, tidb=item.kind == "tidb")
    return connection


def inspect_database(item: DataSourceRecord) -> tuple[list[dict[str, Any]], int]:
    connection = connect_database(item)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION() AS version")
            version = cursor.fetchone()["version"]
            cursor.execute(
                """
                SELECT t.TABLE_SCHEMA, t.TABLE_NAME, t.TABLE_COMMENT,
                       c.COLUMN_NAME, c.COLUMN_TYPE,
                       c.COLUMN_COMMENT, c.IS_NULLABLE
                FROM information_schema.TABLES t
                JOIN information_schema.COLUMNS c
                  ON c.TABLE_SCHEMA=t.TABLE_SCHEMA AND c.TABLE_NAME=t.TABLE_NAME
                WHERE t.TABLE_TYPE='BASE TABLE'
                  AND t.TABLE_SCHEMA NOT IN
                      ('INFORMATION_SCHEMA', 'PERFORMANCE_SCHEMA', 'METRICS_SCHEMA',
                       'mysql', 'sys')
                ORDER BY t.TABLE_SCHEMA, t.TABLE_NAME, c.ORDINAL_POSITION
                """
            )
            rows = list(cursor.fetchall())
    finally:
        connection.close()
    return rows, len({(row["TABLE_SCHEMA"], row["TABLE_NAME"]) for row in rows}) if rows else 0


def inspect_database_relationships(item: DataSourceRecord) -> list[dict[str, str]]:
    connection = connect_database(item)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME,
                       REFERENCED_TABLE_SCHEMA, REFERENCED_TABLE_NAME,
                       REFERENCED_COLUMN_NAME
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE REFERENCED_TABLE_NAME IS NOT NULL
                  AND TABLE_SCHEMA NOT IN
                      ('INFORMATION_SCHEMA', 'PERFORMANCE_SCHEMA', 'METRICS_SCHEMA',
                       'mysql', 'sys')
                ORDER BY TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME
                """
            )
            rows = list(cursor.fetchall())
    finally:
        connection.close()
    return [
        {
            "from": f"{row['TABLE_SCHEMA']}.{row['TABLE_NAME']}.{row['COLUMN_NAME']}",
            "to": (
                f"{row['REFERENCED_TABLE_SCHEMA']}.{row['REFERENCED_TABLE_NAME']}."
                f"{row['REFERENCED_COLUMN_NAME']}"
            ),
            "type": "foreign_key",
        }
        for row in rows
    ]


def collect_recent_sql(item: DataSourceRecord, limit: int = 200) -> list[dict[str, Any]]:
    connection = connect_database(item)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT DIGEST, DIGEST_TEXT, SUM(EXEC_COUNT) AS EXEC_COUNT,
                       MIN(FIRST_SEEN) AS FIRST_SEEN, MAX(LAST_SEEN) AS LAST_SEEN
                FROM information_schema.STATEMENTS_SUMMARY_HISTORY
                WHERE STMT_TYPE='Select' AND DIGEST_TEXT IS NOT NULL
                GROUP BY DIGEST, DIGEST_TEXT
                ORDER BY LAST_SEEN DESC
                LIMIT %s
                """,
                (limit,),
            )
            return list(cursor.fetchall())
    finally:
        connection.close()


def test_database_source(item: DataSourceRecord) -> DataSourceRecord:
    try:
        rows, table_count = inspect_database(item)
        updated = item.model_copy(
            update={
                "status": "ready",
                "table_count": table_count,
                "last_error": None,
                "last_tested_at": now_iso(),
            }
        )
    except Exception as exc:
        updated = item.model_copy(
            update={
                "status": "error",
                "last_error": str(exc)[:240],
                "last_tested_at": now_iso(),
            }
        )
    DATA_SOURCES[item.id] = updated
    return updated


def execute_database_select(item: DataSourceRecord, sql: str) -> tuple[list[str], list[list[Any]]]:
    connection = connect_database(item)
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            records = list(cursor.fetchmany(1000))
            columns = list(records[0].keys()) if records else [description[0] for description in cursor.description or []]
            rows = [[record.get(column) for column in columns] for record in records]
    finally:
        connection.close()
    return columns, rows
