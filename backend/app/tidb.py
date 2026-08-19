"""TiDB session policy for MySQL-protocol connections."""

from __future__ import annotations

import os
import re
from typing import Any


RESOURCE_GROUP_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]{0,63}$")
READ_ENGINES_RE = re.compile(r"^(?:tikv|tiflash)(?:,(?:tikv|tiflash))*$")


def _setting(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def configure_session(cursor: Any, *, tidb: bool, read_only: bool = True) -> None:
    """Apply TiDB engine and optional resource-group settings.

    TiDB currently exposes ``SET TRANSACTION READ ONLY`` as a no-op function
    that raises unless noop functions are enabled. Read-only enforcement is
    therefore implemented by the application SQL AST guard and a database
    account without write privileges, while this helper only applies settings
    supported by the target TiDB versions.
    """

    if not tidb:
        return
    read_engines = _setting("TIDB_READ_ENGINES", "tikv,tiflash")
    if not READ_ENGINES_RE.fullmatch(read_engines):
        raise ValueError("TIDB_READ_ENGINES must contain tikv and/or tiflash")
    cursor.execute("SET SESSION tidb_isolation_read_engines=%s", (read_engines,))
    resource_group = _setting("TIDB_RESOURCE_GROUP")
    if resource_group:
        if not RESOURCE_GROUP_RE.fullmatch(resource_group):
            raise ValueError("TIDB_RESOURCE_GROUP is not a valid identifier")
        cursor.execute(f"SET RESOURCE GROUP `{resource_group}`")


def platform_connection_settings() -> dict[str, str]:
    return {
        "engine": "tidb",
        "read_engines": _setting("TIDB_READ_ENGINES", "tikv,tiflash"),
        "resource_group": _setting("TIDB_RESOURCE_GROUP") or "default",
        "platform_database": _setting("AEGIS_PLATFORM_DB_DATABASE", "aegis_platform"),
    }
