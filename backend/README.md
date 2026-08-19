# Data AI Explorer backend MVP

Python/FastAPI backend for the smart query product slice. It keeps demo catalog data in memory, while supporting TiDB MCP metadata/query calls, an OpenAI-compatible Text2SQL gateway, and CSV/Parquet analysis.

Python 3.12+ is required for the MCP SDK and the Compose backend image.

## Run locally

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

OpenAPI is available at http://localhost:8080/docs. The API is prefixed with `/api/v1`; CORS allows local frontend development origins.

## Demo flow

1. `GET /api/v1/workbench/summary` loads the dashboard.
2. `POST /api/v1/query/conversations` submits a natural-language question and returns an operation id.
3. `GET /api/v1/query/operations/{operation_id}` reads the generated SQL, answer and evidence.
4. Browse `GET /api/v1/incidents` and `GET /api/v1/assets` for operations and governance views.

## Smart Query APIs

- `POST /api/v1/tidb/mcp/introspect`: connect to a Streamable HTTP MCP server and collect schemas, tables, columns and comments. For local UI demos use `{ "endpoint": "demo://tidb" }`.
- `GET /api/v1/tidb/catalog`: return the current visualizable catalog.
- `POST /api/v1/query/conversations`: use an OpenAI-compatible model gateway for Text2SQL when `MODEL_GATEWAY_BASE_URL` and `MODEL_GATEWAY_MODEL` are configured; otherwise use a deterministic read-only fallback. TiDB execution uses the MCP `execute_query`-style tool.
- `POST /api/v1/datasets/upload`: upload CSV or Parquet.
- `POST /api/v1/datasets/local-directory`: scan an allowlisted machine directory. Configure `DATASET_ALLOWED_ROOTS`; arbitrary paths are rejected.
- `POST /api/v1/datasets/analyze`: query registered files through DuckDB and return rows plus an ECharts option.

MCP tool names are discovered from the server and matched against aliases (`list_schemas`, `list_tables`, `describe_table`, `execute_query`). If a server uses different names, pass a `tool_map` in the introspection request.
