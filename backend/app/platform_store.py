"""Small TiDB-backed store for platform settings and audit records.

The feature modules still keep their demo working sets in memory, but settings
and audit events must survive an API restart.  The store is optional for local
unit tests and becomes active when AEGIS_PLATFORM_DB_HOST is configured.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any

import pymysql


IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def enabled() -> bool:
    return bool(os.getenv("AEGIS_PLATFORM_DB_HOST", "").strip())


def _identifier(value: str, fallback: str) -> str:
    candidate = value.strip() or fallback
    if not IDENTIFIER_RE.fullmatch(candidate):
        raise ValueError(f"invalid TiDB identifier: {candidate}")
    return candidate


def _config() -> dict[str, Any]:
    return {
        "host": os.getenv("AEGIS_PLATFORM_DB_HOST", ""),
        "port": int(os.getenv("AEGIS_PLATFORM_DB_PORT", "4000")),
        "user": os.getenv("AEGIS_PLATFORM_DB_USER", "root"),
        "password": os.getenv("AEGIS_PLATFORM_DB_PASSWORD", ""),
        "database": _identifier(os.getenv("AEGIS_PLATFORM_DB_DATABASE", "aegis_platform"), "aegis_platform"),
    }


def _connect(database: str | None = None):
    config = _config()
    return pymysql.connect(
        host=config["host"],
        port=config["port"],
        user=config["user"],
        password=config["password"],
        database=database,
        charset="utf8mb4",
        autocommit=True,
        connect_timeout=5,
        read_timeout=10,
        write_timeout=10,
        cursorclass=pymysql.cursors.DictCursor,
    )


def ensure_schema() -> bool:
    if not enabled():
        return False
    config = _config()
    connection = _connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{config['database']}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        connection.select_db(config["database"])
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS platform_settings (
                    id TINYINT PRIMARY KEY,
                    payload JSON NOT NULL,
                    updated_at DATETIME(6) NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id VARCHAR(40) PRIMARY KEY,
                    actor VARCHAR(160) NOT NULL,
                    action VARCHAR(120) NOT NULL,
                    resource_type VARCHAR(80) NOT NULL,
                    resource_id VARCHAR(160) NULL,
                    payload JSON NOT NULL,
                    created_at DATETIME(6) NOT NULL,
                    KEY idx_audit_created_at (created_at),
                    KEY idx_audit_resource (resource_type, resource_id)
                )
                """
            )
        return True
    finally:
        connection.close()


def load_settings() -> dict[str, Any] | None:
    if not enabled():
        return None
    ensure_schema()
    connection = _connect(_config()["database"])
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT payload FROM platform_settings WHERE id=1")
            row = cursor.fetchone()
            if not row:
                return None
            payload = row["payload"]
            return json.loads(payload) if isinstance(payload, str) else payload
    finally:
        connection.close()


def save_settings(payload: dict[str, Any]) -> None:
    if not enabled():
        return
    ensure_schema()
    connection = _connect(_config()["database"])
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO platform_settings (id, payload, updated_at)
                VALUES (1, %s, UTC_TIMESTAMP(6))
                ON DUPLICATE KEY UPDATE payload=VALUES(payload), updated_at=VALUES(updated_at)
                """,
                (json.dumps(payload, ensure_ascii=False),),
            )
    finally:
        connection.close()


def record_audit(
    event_id: str,
    actor: str,
    action: str,
    resource_type: str,
    resource_id: str | None,
    payload: dict[str, Any] | None = None,
) -> None:
    if not enabled():
        return
    ensure_schema()
    connection = _connect(_config()["database"])
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO audit_events
                    (event_id, actor, action, resource_type, resource_id, payload, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, UTC_TIMESTAMP(6))
                """,
                (
                    event_id,
                    actor[:160],
                    action[:120],
                    resource_type[:80],
                    resource_id[:160] if resource_id else None,
                    json.dumps(payload or {}, ensure_ascii=False),
                ),
            )
    finally:
        connection.close()
