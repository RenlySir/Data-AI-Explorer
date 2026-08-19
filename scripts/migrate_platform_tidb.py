#!/usr/bin/env python3
"""Create the TiDB metadata schema used by the Aegis platform API.

The API also runs this idempotently at startup.  Keeping a small explicit
migration command makes deployment verification and disaster recovery easier.
"""

from __future__ import annotations

import os
import sys


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "backend"))

from app.platform_store import ensure_schema  # noqa: E402


def main() -> int:
    if not os.getenv("AEGIS_PLATFORM_DB_HOST", "").strip():
        raise SystemExit("AEGIS_PLATFORM_DB_HOST is required")
    created = ensure_schema()
    print(
        "platform metadata schema ready"
        if created
        else "platform metadata store is disabled"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
