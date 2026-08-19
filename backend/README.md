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

OpenAPI is available at http://localhost:8080/docs. The API is prefixed with `/api/v1`. Localhost origins and dynamic development ports are enabled by default; production deployments should set `CORS_ALLOW_LOCALHOST=false` and provide exact HTTPS origins in `CORS_ALLOW_ORIGINS`.

## Model registry APIs

- `GET /api/v1/models/providers`: list supported public and private provider templates.
- `GET/POST /api/v1/models/connections`: list or register model connections; API Keys are never returned.
- `POST /api/v1/models/connections/{id}/test`: probe `/models` or Ollama `/api/tags`, then run a minimal Chat Completion before marking the connection ready.
- `POST /api/v1/models/connections/{id}/activate`: select a verified connection as the platform default.
- `DELETE /api/v1/models/connections/{id}`: remove the connection and its in-memory secret.

The active connection is used by Text2SQL and chart selection before environment-based gateway settings. Public hosts require HTTPS; private hosts require `MODEL_ALLOW_PRIVATE_HOSTS=true` or an exact `MODEL_ALLOWED_HOSTS` entry. Production must disable the broad private-host fallback and replace in-memory secrets with Vault/OpenBao/KMS references.

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

### ChatBI operational flow

- `GET/POST /api/v1/chatbi/datasources`: list or add TiDB/MySQL connections. Passwords are held separately in process memory and never returned by the API.
- `POST /api/v1/chatbi/datasources/{id}/test`: read `information_schema` to verify access and collect table/column comments.
- `POST /api/v1/chatbi/datasources/upload`: register a CSV/Parquet file as a selectable ChatBI datasource.
- `POST /api/v1/chatbi/query`: generate guarded read-only SQL, execute it through TiDB/MySQL or DuckDB, and return an AI-selected ECharts specification.
- `GET/POST /api/v1/chatbi/reports`: list or accept a completed analysis for the dashboard. `DELETE /api/v1/chatbi/reports/{id}` removes it.

Direct database hosts must match `CHATBI_ALLOWED_DB_HOSTS`, or resolve only to private/loopback addresses when `CHATBI_ALLOW_PRIVATE_HOSTS=true`. Production deployments should set the private-host fallback to `false`, configure exact hosts, store credentials in a secret manager, and replace the in-memory records with persistent encrypted storage.

## TiDB SQL Optimizer APIs

- `GET /api/v1/aiops/sql-optimizer/versions`: list the version profiles for TiDB 7.5 and 8.0-8.5, including source tag, commit and relevant optimizer capabilities.
- `POST /api/v1/aiops/sql-optimizer/inputs/upload`: load one or more UTF-8 `.sql`, `.ddl` or `.txt` files.
- `POST /api/v1/aiops/sql-optimizer/inputs/local-directory`: load SQL/DDL files from a directory under `DATASET_ALLOWED_ROOTS`.
- `POST /api/v1/aiops/sql-optimizer/analyze`: return a version-aware simulated plan, or verify `SELECT VERSION()` and run `EXPLAIN FORMAT='verbose'` through TiDB MCP in `live` mode.

Simulation is an explainable hypothesis based on the SQL AST, DDL, SQLAdvisor-style index ordering and TiDB minor-version profiles. It is deliberately labelled as simulated and never presented as TiDB optimizer output. Production validation requires `live` mode against the requested TiDB version.

## Scenario Center APIs

- `GET /api/v1/scenarios`: list the 12 versioned Agent Team scenario templates, optionally filtered by category or status.
- `POST /api/v1/scenarios/{scenario_id}/runs`: create a traceable scenario run with an objective and context.
- `GET /api/v1/scenario-runs`: list current run instances and states.
- `POST /api/v1/scenario-runs/{run_id}/advance`: complete one low/medium-risk step or stop at a high-risk approval gate.
- `POST /api/v1/scenario-runs/{run_id}/approve`: approve only the current high-risk step. Advancing without approval returns HTTP 409.

Local runs record deterministic demo evidence and do not claim that Prometheus, Airflow, GitLab, Rundeck or other production systems were called. Those systems are connected through deployment-specific adapters.

MCP tool names are discovered from the server and matched against aliases (`list_schemas`, `list_tables`, `describe_table`, `execute_query`). If a server uses different names, pass a `tool_map` in the introspection request.
