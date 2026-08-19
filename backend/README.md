# Data AI Explorer backend MVP

Python/FastAPI backend for the smart query product slice. It keeps demo catalog data in memory, while supporting TiDB MCP metadata/query calls, an OpenAI-compatible Text2SQL gateway, and CSV/Parquet analysis.

Python 3.12+ is recommended for the Compose backend image and MCP SDK. The
three-node CentOS 8 deployment also supports Python 3.9: MCP is optional there,
and TiDB metadata/query/optimizer demos use the direct read-only connector.

The knowledge base uses the modular LangChain Text Splitters package
(`langchain-text-splitters>=0.3.11,<0.4`) for recursive, separator-aware chunks.
If a minimal offline environment cannot install it, the same API falls back to
the built-in recursive splitter. Full LangChain agents and cloud integrations
are intentionally not required by the local MVP.

## Run locally

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

OpenAPI is available at http://localhost:8080/docs. The API is prefixed with `/api/v1`. Localhost origins and dynamic development ports are enabled by default; production deployments should set `CORS_ALLOW_LOCALHOST=false` and provide exact HTTPS origins in `CORS_ALLOW_ORIGINS`.

For the three-node TiDB demo, set `AEGIS_NODE_ROLE`, `AEGIS_TIDB_ENDPOINTS`, `AEGIS_TIDB_SQL_PORT=4100`, and `AEGIS_TIDB_STATUS_PORT=11080`. `/health` reports the node role and deployment version; `/api/v1/deployment/status` probes all configured TiDB status endpoints without exposing credentials.

## Model registry APIs

- `GET /api/v1/models/providers`: list supported public and private provider templates.
- `GET/POST /api/v1/models/connections`: list or register model connections; API Keys are never returned.
- `POST /api/v1/models/connections/{id}/test`: probe `/models` or Ollama `/api/tags`, then run a minimal Chat Completion before marking the connection ready.
- `POST /api/v1/models/connections/{id}/activate`: select a verified connection as the platform default.
- `DELETE /api/v1/models/connections/{id}`: remove the connection and its in-memory secret.

The active connection is used by Text2SQL and chart selection before environment-based gateway settings. Public hosts require HTTPS; private hosts require `MODEL_ALLOW_PRIVATE_HOSTS=true` or an exact `MODEL_ALLOWED_HOSTS` entry. Production must disable the broad private-host fallback and replace in-memory secrets with Vault/OpenBao/KMS references.

## Platform metadata APIs

- `POST /api/v1/auth/login`: validates the demo account shape and records a login audit event.
- `GET/PATCH /api/v1/settings`: read or update workspace, connector and security settings.
- When `AEGIS_PLATFORM_DB_HOST` is set, startup creates the TiDB database named by `AEGIS_PLATFORM_DB_DATABASE` (default `aegis_platform`) and the `platform_settings` / `audit_events` tables. `scripts/migrate_platform_tidb.py` is an idempotent explicit migration command.
- The platform store intentionally keeps business feature working sets in memory for the demo; production should move datasource credentials, Agent state, relationship snapshots and workflow checkpoints into tenant-scoped TiDB tables/object storage.

## Module Agent APIs

- `GET /api/v1/agents/templates`: list the 8 templates generated from the product module catalog.
- `POST /api/v1/agents/provision`: idempotently create all templates, or only supplied `template_ids`, and bind them to the verified default model.
- `GET/POST /api/v1/agents`: list agents or create one template.
- `PUT /api/v1/agents/{id}/enabled`: enable or disable an Agent.
- `POST /api/v1/agents/{id}/test`: check enabled state, bound model, capability assembly, and approval policy without consuming a model call.
- `POST /api/v1/agents/{id}/invoke`: run a model-only advisory test. It receives the tool allowlist but never executes a tool.
- `DELETE /api/v1/agents/{id}`: remove an Agent so its template can be created again.

Agent instances store a model connection reference, never its API Key. Removing the bound model marks its Agents unavailable. AIOps, SQL optimization, command, and approval templates retain human-approval policy; provisioning an Agent never grants production executor access. The local registry is in memory and must be moved to tenant/workspace-isolated TiDB tables before production.

## Demo flow

1. `GET /api/v1/workbench/summary` loads the dashboard.
2. `POST /api/v1/query/conversations` submits a natural-language question and returns an operation id.
3. `GET /api/v1/query/operations/{operation_id}` reads the generated SQL, answer and evidence.
4. Browse `GET /api/v1/incidents` and `GET /api/v1/assets` for operations and governance views.

## Smart Query APIs

- `POST /api/v1/tidb/mcp/introspect`: connect to a Streamable HTTP MCP server and collect schemas, tables, columns and comments. For local UI demos use `{ "endpoint": "demo://tidb" }`.
- `GET /api/v1/tidb/catalog`: return the current visualizable catalog.
- `POST /api/v1/query/conversations`: use an OpenAI-compatible model gateway for Text2SQL when `MODEL_GATEWAY_BASE_URL` and `MODEL_GATEWAY_MODEL` are configured; otherwise use a deterministic read-only fallback. TiDB execution uses the MCP `execute_query`-style tool.
- `GET /api/v1/query/operations/{operation_id}/events`: SSE execution timeline with `PLANNING`, `VALIDATING`, `EXECUTING` and `COMPLETED` events. The current synchronous executor emits the same contract that the future worker-backed executor will use.
- `POST /api/v1/datasets/upload`: upload CSV or Parquet.
- `POST /api/v1/datasets/local-directory`: scan an allowlisted machine directory. Configure `DATASET_ALLOWED_ROOTS`; arbitrary paths are rejected.
- `POST /api/v1/datasets/analyze`: query registered files through DuckDB and return rows plus an ECharts option.

### ChatBI operational flow

- `GET/POST /api/v1/chatbi/datasources`: list or add TiDB/MySQL connections. Passwords are held separately in process memory and never returned by the API.
- `POST /api/v1/chatbi/datasources/{id}/test`: read `information_schema` to verify access and collect table/column comments.
- `POST /api/v1/chatbi/datasources/upload`: register a CSV/Parquet file as a selectable ChatBI datasource.
- `POST /api/v1/chatbi/query`: generate guarded read-only SQL, execute it through TiDB/MySQL or DuckDB, and return an AI-selected ECharts specification.
- `GET/POST /api/v1/chatbi/reports`: list or accept a completed analysis for the dashboard. `DELETE /api/v1/chatbi/reports/{id}` removes it.

### Operations and observability

- Every response includes `X-Request-ID` (caller supplied or generated) plus baseline security headers. `GET /metrics` exposes Prometheus-compatible request/error counters and active operation count.
- The frontend uses the operation SSE contract with bounded reconnect attempts and renders the phase timeline instead of relying on a transient toast.

Direct database hosts must match `CHATBI_ALLOWED_DB_HOSTS`, or resolve only to private/loopback addresses when `CHATBI_ALLOW_PRIVATE_HOSTS=true`. Production deployments should set the private-host fallback to `false`, configure exact hosts, store credentials in a secret manager, and replace the in-memory records with persistent encrypted storage.

## Data Relationship APIs

- `POST /api/v1/data-relationships/{datasource_id}/collect`: collect all accessible business schemas, tables, column types/comments and foreign keys from a registered TiDB/MySQL source.
- `GET /api/v1/data-relationships/{datasource_id}`: return graph nodes, table/field edges, provenance, confidence and SQL observations.
- `POST /api/v1/data-relationships/{datasource_id}/sql-observations`: parse a submitted SELECT/WITH statement with SQLGlot and learn table/field JOIN relationships without executing it.
- `POST /api/v1/data-relationships/{datasource_id}/collect-sql`: pull TiDB `STATEMENTS_SUMMARY_HISTORY`, redact literals, deduplicate by digest and increment relationship observation counts.
- `GET /api/v1/data-relationships/{datasource_id}/sql-collector`: read the server-side collector switch, interval, latest collection time and latest error.
- `PUT /api/v1/data-relationships/{datasource_id}/sql-collector`: start or stop the in-process collector. It keeps running after the browser page closes while the API process remains alive.

The local MVP stores graph snapshots, collector configuration and checkpoints in process memory. Production must use tenant/workspace-isolated TiDB tables and a singleton scheduled Connector Worker, and grant the collector account read-only metadata plus the minimum TiDB statement-summary privilege.

## TiDB SQL Optimizer APIs

- `GET /api/v1/aiops/sql-optimizer/versions`: list the version profiles for TiDB 7.5 and 8.0-8.5, including source tag, commit and relevant optimizer capabilities.
- `POST /api/v1/aiops/sql-optimizer/inputs/upload`: load one or more UTF-8 `.sql`, `.ddl` or `.txt` files.
- `POST /api/v1/aiops/sql-optimizer/inputs/local-directory`: load SQL/DDL files from a directory under `DATASET_ALLOWED_ROOTS`.
- `POST /api/v1/aiops/sql-optimizer/analyze`: return a version-aware simulated plan, or verify `SELECT VERSION()` and run `EXPLAIN FORMAT='verbose'` through TiDB MCP in `live` mode. On the Python 3.9 three-node deployment, set `AEGIS_TIDB_OPTIMIZER_HOST/PORT/DATABASE` to enable the same live plan through the restricted direct TiDB connector when MCP is unavailable.

Simulation is an explainable hypothesis based on the SQL AST, DDL, SQLAdvisor-style index ordering and TiDB minor-version profiles. It is deliberately labelled as simulated and never presented as TiDB optimizer output. Production validation requires `live` mode against the requested TiDB version.

## Knowledge Base APIs

- `GET/POST /api/v1/knowledge-bases`: list or create a workspace knowledge base. The default is hybrid retrieval with LangChain's recursive splitter when `langchain-text-splitters` is installed.
- `GET /api/v1/knowledge-bases/index-modes`: list the supported `hybrid`, `lexical`, and `semantic` index modes and their local providers.
- `GET /api/v1/knowledge-bases/chunking-modes`: list recursive and Markdown-header chunking adapters and the provider active in the local runtime.
- `PATCH /api/v1/knowledge-bases/{id}`: update the index mode, chunking mode, chunk size, and overlap. Chunk-setting changes rebuild the existing document chunks while preserving document identities.
- `POST /api/v1/knowledge-bases/{id}/documents`, `/documents/upload`, `/documents/local-directory`: ingest text, UTF-8 text files, or an allowlisted local directory.
- `PATCH /api/v1/knowledge-bases/{id}/documents/{document_id}`: enable or suspend a document from retrieval without deleting it.
- `POST /api/v1/knowledge-bases/{id}/documents/{document_id}/reindex`: rebuild one document with the current chunking configuration. `DELETE` on the same document path removes its source cache and chunks.
- `POST /api/v1/knowledge-bases/{id}/query`: retrieve with optional `tags`, `top_k`, `score_threshold`, and `generate_answer`. The response includes citations, matched terms, retrieval reasons, candidate count, applied threshold, latency, and model/extractive generation mode.
- `GET /api/v1/knowledge-bases/{id}/documents/{document_id}/chunks`: inspect and verify chunks before production use.
- The optional Model Gateway is called only after retrieval. Model output must cite the returned `[n]` evidence; invalid or unavailable model output falls back to extractive citations. No evidence produces an explicit low-confidence refusal.

## Scenario Center APIs

- `GET /api/v1/scenarios`: list the 12 versioned Agent Team scenario templates, optionally filtered by category or status.
- `POST /api/v1/scenarios/{scenario_id}/runs`: create a traceable scenario run with an objective and context.
- `GET /api/v1/scenario-runs`: list current run instances and states.
- `POST /api/v1/scenario-runs/{run_id}/advance`: complete one low/medium-risk step or stop at a high-risk approval gate.
- `POST /api/v1/scenario-runs/{run_id}/approve`: approve only the current high-risk step. Advancing without approval returns HTTP 409.

Local runs record deterministic demo evidence and do not claim that Prometheus, Airflow, GitLab, Rundeck or other production systems were called. Those systems are connected through deployment-specific adapters.

MCP tool names are discovered from the server and matched against aliases (`list_schemas`, `list_tables`, `describe_table`, `execute_query`). If a server uses different names, pass a `tool_map` in the introspection request.
