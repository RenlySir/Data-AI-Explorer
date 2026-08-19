#!/usr/bin/env python3
"""Verify the TiDB platform database and session capabilities."""

from __future__ import annotations

import os
import sys

import pymysql


def main() -> int:
    host = os.getenv("AEGIS_PLATFORM_DB_HOST", os.getenv("TIDB_HOST", "127.0.0.1"))
    port = int(os.getenv("AEGIS_PLATFORM_DB_PORT", os.getenv("TIDB_PORT", "4000")))
    database = os.getenv("AEGIS_PLATFORM_DB_DATABASE", "aegis_platform")
    connection = pymysql.connect(
        host=host,
        port=port,
        user=os.getenv("AEGIS_PLATFORM_DB_USER", os.getenv("TIDB_USER", "root")),
        password=os.getenv("AEGIS_PLATFORM_DB_PASSWORD", os.getenv("TIDB_PASSWORD", "")),
        database=database,
        charset="utf8mb4",
        autocommit=True,
        connect_timeout=5,
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION() AS version, @@tidb_isolation_read_engines AS read_engines")
            version = cursor.fetchone() or {}
            cursor.execute(
                "SELECT TABLE_NAME FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA=%s ORDER BY TABLE_NAME",
                (database,),
            )
            tables = [row["TABLE_NAME"] for row in cursor.fetchall()]
            print({"host": host, "port": port, "database": database, "version": version, "tables": tables})
            required = {"platform_settings", "audit_events"}
            missing = required.difference(tables)
            if missing:
                print(f"missing TiDB platform tables: {sorted(missing)}", file=sys.stderr)
                return 1
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
