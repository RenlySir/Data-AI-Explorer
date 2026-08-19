# 企业 AI 落地平台后端开发设计方案

版本：v1.0
日期：2026-08-19
对应架构：Aegis AI Control Plane v1.0

依据：[产品设计方案](企业AI落地平台-产品设计方案.md)与[详细架构设计方案](企业AI落地平台-详细架构设计方案.md)。本方案定义后端实现，不替代安全、部署和运维约束。

## 1. 目标与边界

后端负责租户与权限、数据治理、智能问数、AIOps、Agent 编排、Runbook 执行、审批、通知和审计。采用 Java 21 + Spring Boot 3 模块化单体作为控制面，Python 3.12 Worker 承担模型、RAG、SQL 分析和 RCA；Temporal 负责长流程，Kafka 负责事件解耦。

控制面不直接执行生产 Shell，不直接把数据库凭证发给模型；生产动作通过 Executor Gateway 下发给安全域内 Executor Agent。

## 2. 工程组织

```text
apps/server/src/main/java/com/aegis/
├── common/                # tenant、error、trace、outbox、security
├── identity/              # user、role、policy、workspace
├── catalog/               # datasource、asset、schema、lineage
├── semantic/              # metric、glossary、metric version
├── query/                 # conversation、planner、execution、feedback
├── incident/              # event、incident、RCA、evidence
├── runbook/               # DSL、版本、policy、execution
├── approval/              # approval workflow
├── agent/                 # definition、run、decision
├── notification/          # outbox、channel、template
├── audit/                 # append-only audit
└── admin/                 # connectors、models、system config
```

每个模块包含 `api`、`application`、`domain`、`infrastructure` 四层。Controller 只处理协议；Application 编排事务；Domain 保存状态机和规则；Infrastructure 访问数据库、消息和外部系统。禁止跨模块直接调用 Repository。

AI Worker：`workers/ai_worker/{gateway,rag,query,rca,evaluation}`；Connector Worker：`workers/connector_worker/{database,observability,scheduler,lineage}`；Executor Agent：`agents/executor_agent/{transport,policy,plugins,verify}`。

## 3. 运行时与基础依赖

| 组件 | 版本基线 | 用途 |
|---|---|---|
| Java/Spring | Java 21、Spring Boot 3.4、Spring Security 6 | 控制面 API |
| Python | 3.12、FastAPI、Pydantic 2 | AI/采集 Worker |
| 数据库 | PostgreSQL 16 | 控制面权威数据 |
| 搜索 | OpenSearch 2.x | 资产、日志、事件检索 |
| 缓存 | Redis 7.x | 会话、限流、短期状态 |
| 消息 | Kafka 3.x | 事件流、Outbox 消费 |
| 工作流 | Temporal | 查询、RCA、审批、执行长流程 |
| 对象存储 | S3/MinIO | 证据、结果、模型评测、导出 |
| 密钥 | Vault/OpenBao | Secret 引用和短期凭证 |
| 迁移 | Flyway | 版本化数据库迁移 |

依赖版本统一由 Renovate/内部依赖平台管理；生产禁用浮动镜像标签。

## 4. 领域模型与数据库设计

### 4.1 公共字段与约束

所有业务表包含：`id uuidv7`、`tenant_id`、`created_at`、`updated_at`、`created_by`、`version`、`deleted_at`（适用时）。时间以 UTC `timestamptz` 保存。启用 PostgreSQL RLS，应用层每个事务设置 `app.tenant_id`。

所有状态变化写 `domain_event` 或专用历史表；删除优先逻辑删除。敏感字段使用 envelope encryption，数据库内只保存密文和 key_version。

### 4.2 关键表

```sql
create table metric (
  id uuid primary key,
  tenant_id uuid not null,
  workspace_id uuid not null,
  code varchar(128) not null,
  name varchar(256) not null,
  definition_json jsonb not null,
  owner_id uuid not null,
  status varchar(32) not null,
  current_version int not null default 1,
  created_at timestamptz not null,
  updated_at timestamptz not null,
  unique (tenant_id, workspace_id, code)
);

create table asset (
  id uuid primary key,
  tenant_id uuid not null,
  urn varchar(1024) not null,
  asset_type varchar(32) not null,
  source_id uuid not null,
  classification varchar(32) not null,
  owner_id uuid,
  metadata_json jsonb not null,
  observed_at timestamptz,
  unique (tenant_id, urn)
);

create table audit_event (
  id uuid primary key,
  tenant_id uuid not null,
  trace_id varchar(64) not null,
  actor_type varchar(32) not null,
  actor_id varchar(128),
  action varchar(128) not null,
  resource_type varchar(64) not null,
  resource_id varchar(256) not null,
  policy_result varchar(32) not null,
  payload_hash char(64) not null,
  payload_ref varchar(1024),
  occurred_at timestamptz not null
);
```

高频表按 `tenant_id + occurred_at` 或时间范围分区；audit、event、query_execution 超过 180 天归档对象存储。大 JSON 只存摘要和对象存储引用。

### 4.3 状态机

状态转换必须由领域方法完成，禁止 Controller 直接更新 status。非法转换返回 `409 STATE_TRANSITION_INVALID`。

- Query：`RECEIVED → PLANNING → NEED_CLARIFICATION | VALIDATING → EXECUTING → VERIFYING → COMPLETED | REJECTED | FAILED`
- Incident：`OPEN → TRIAGING → DIAGNOSED → PENDING_APPROVAL → MITIGATING → VERIFYING → RESOLVED → CLOSED`
- Approval：`PENDING → APPROVED | REJECTED | EXPIRED | CANCELLED`
- Execution：`CREATED → DRY_RUN → WAITING_APPROVAL → RUNNING → VERIFYING → SUCCEEDED | FAILED | ROLLED_BACK | HUMAN_REQUIRED`

## 5. API 设计

### 5.1 通用约定

前缀 `/api/v1`；认证使用 OIDC Bearer；写操作支持 `Idempotency-Key`；分页使用 `next_cursor`；异步返回 `202` 和 `operation_id`；错误遵循 RFC 9457。所有响应包含 `trace_id`。

### 5.2 代表性接口

```http
POST /api/v1/query/conversations/{id}/messages
Content-Type: application/json
Idempotency-Key: 4f...

{"content":"本月华东收入同比？","attachments":[],"context":{"period":"2026-08"}}
```

```json
{"operation_id":"op_01...","query_id":"qry_01...","status":"PLANNING","sse_url":"/api/v1/operations/op_01/events"}
```

```http
GET /api/v1/assets/{urn}/lineage?direction=both&depth=2
POST /api/v1/incidents/{id}/diagnose
POST /api/v1/executions/{id}/dry-run
POST /api/v1/approvals/{id}/decisions
```

API 分层：Controller → DTO Validator → Application Service → Domain → Repository/Port。外部连接器通过 Port 接口，禁止在领域层依赖厂商 SDK。

### 5.3 SSE 协议

事件统一：

```text
event: operation.status
id: 37
data: {"operation_id":"op_01","status":"EXECUTING","progress":65,"trace_id":"..."}
```

事件序列号单调递增；服务端保留 24 小时事件；重连使用 `Last-Event-ID`。前端断线后以 `GET /operations/{id}` 校准，不能只依赖流。

## 6. 智能问数后端实现

### 6.1 编排

QueryApplicationService 创建消息和 Query Aggregate，提交 Temporal `QueryWorkflow`。Workflow 调用 AI Worker：意图识别、语义检索、SQL 规划、Guard、执行和验证。

已发布指标走 Deterministic Metric Compiler；开放分析才调用 LLM。Context Builder 在服务端根据用户权限过滤资产，发送给模型的上下文记录 `context_snapshot_id`。

### 6.2 SQL Guard

执行前顺序固定：解析 AST → 多语句检查 → 语句类型白名单 → 表/列授权 → 函数黑名单 → LIMIT 注入/行数上限 → 估算扫描量 → 数据源策略。解析失败直接拒绝，不尝试正则绕过。

Query Proxy 使用只读账号、只读事务、超时、最大扫描量、最大结果行数和租户并发信号量。所有实际执行 SQL 记录 canonical SQL、参数 hash、资产集合、耗时、扫描量和审计 ID；不记录敏感值。

### 6.3 结果验证

Verifier 执行空值、数量级、时间完整性、同比复算、单位和异常值规则。验证失败返回 `NEEDS_REVIEW`，结论模板必须出现限制说明。置信度由规则计算，模型输出只能作为解释文本。

## 7. 数据治理后端实现

Connector Worker 使用 Connector SPI：`testConnection`、`discoverSchemas`、`discoverColumns`、`discoverQueryLogs`、`discoverLineage`。采集任务由 Temporal 定时触发，结果写入 staging 表，经过 diff、去重、版本化后提交资产。

数据库 SQL 解析优先使用 SQLGlot/Apache Calcite；解析结果包含表级和字段级关系。OpenLineage 事件作为补充来源。边合并使用 `(tenant_id, source_urn, target_urn, edge_type)` 唯一键和可信度更新规则。

OpenSearch 索引按 `aegis-assets-v{n}`、`aegis-events-v{n}`；mapping 固定、禁止 dynamic mapping 扩散。重建索引采用新索引 + alias 原子切换。

## 8. AIOps 后端实现

接入层将 Alertmanager、OTel、Loki、Kubernetes、调度平台转换为 `ObservabilityEvent`，写入 Kafka `observability.raw.v1`。消费者必须幂等，使用 event_id 去重。

聚合器按 fingerprint、服务、环境和时间窗合并 Incident；策略引擎按事件等级、影响范围、维护窗口和历史成功率选择动作。RCA 先查拓扑、最近变更和时序异常，再调用 AI Worker 生成有证据的假设。

Evidence 只保存引用和摘要，原始日志/指标通过 connector 临时查询或对象存储快照获取；敏感日志脱敏后才能进入模型上下文。

## 9. Runbook、Executor 与审批

Runbook YAML 经 JSON Schema 校验，解析为不可变 `RunbookVersion`。动作插件包含输入 Schema、风险等级、权限、dry-run、执行、验证和回滚方法。

执行 Workflow：创建快照 → Policy Evaluate → Dry Run → 创建审批 → 等待审批 → 签名任务 → Executor 执行 → 回传证据 → 验证 → 成功或回滚。Executor 只接受任务签名、租户、目标环境和 plugin/action，不执行任意命令字符串。

Executor Gateway 与 Agent 使用 mTLS，Agent 主动出站长轮询；控制面永不保存生产永久凭证。每一步使用最小权限短凭证，结果含开始/结束时间、输出 hash、退出码和验证指标。

## 10. Agent 与模型网关

AgentDefinition 包含工具白名单、数据范围、模型策略、最大步数、Token 预算、超时、升级条件和输出 JSON Schema。Temporal 负责重试和人工等待；每次工具调用写 `tool_call` 和审计。

Model Gateway 提供统一 `chat/streamChat/embed/rerank/health` Port，适配 OpenAI-compatible、Ollama、vLLM、TGI、云模型和自建 HTTP/gRPC。模型注册时探测 JSON Schema、Tool Calling、上下文、Embedding 维度、并发和数据边界。

路由先按数据等级过滤，再按能力、健康、质量、延迟和成本评分。`local-only` 工作区禁止降级到公网。模型和 Prompt 版本写入每次 AI 输出。

## 11. 消息、事务与一致性

业务事务和 Outbox 写入同一数据库事务；Outbox Publisher 投递 Kafka，成功后标记 sent。消费者使用 inbox/event_id 幂等。跨资源操作使用 Saga/Temporal 补偿，不使用分布式两阶段提交。

Topic：`metadata.changed.v1`、`query.completed.v1`、`observability.raw.v1`、`incident.changed.v1`、`execution.requested.v1`、`audit.created.v1`。分区键优先 `tenant_id` 或 `incident_id`，保证同一聚合有序。

## 12. 安全与租户隔离

IAM 计算 `RBAC ∩ ABAC ∩ environment_policy ∩ datasource_acl`。Repository 查询必须带 tenant 条件，RLS 二次兜底。数据源凭证为 Vault 引用；Worker 获取短期凭证后内存使用，禁止写磁盘。

模型上下文只包含用户有权资产；Prompt Injection 内容视为不可信数据。工具参数必须结构化校验，模型无网络、数据库和 Secret 直连权限。

审计采用 append-only，记录 actor、action、资源、策略结果、模型/Prompt 版本、工具调用、参数 hash、证据和 trace_id。关键审计异步失败进入本地持久队列，不能静默丢失。

## 13. 可观测性与故障处理

Java、Python、Connector、Executor 统一 OpenTelemetry。指标包括 API 延迟/错误、Kafka lag、Temporal workflow、模型延迟/Token、查询扫描量、RCA 成功率、Runbook 成功/回滚率和审计延迟。

外部调用必须设置连接/读取/总超时、指数退避、熔断和 bulkhead。模型不可用时 Query 降级为指标目录/历史结果，AIOps 降级为规则 RCA，Executor 不自动重试有副作用动作。

## 14. 测试与质量门禁

- 单元：领域状态机、策略、SQL Guard、置信度、脱敏，覆盖率 ≥80%。
- 集成：Testcontainers PostgreSQL/Kafka/Redis/OpenSearch/Temporal。
- 契约：OpenAPI、SSE、Kafka Schema、Connector SPI。
- 安全：越权、SQL 注入、Prompt Injection、任意命令、租户串读。
- AI：固定问数集、SQL 正确性、结果一致性、引用完整性、历史 Incident 回放。
- 压测：普通 API P95 <500ms、告警峰值 1,000 event/s、简单问数 P95 <15s。

## 15. 后端实施任务

| Sprint | 任务 |
|---|---|
| 1 | 工程骨架、OIDC、租户、异常模型、迁移和审计 |
| 2 | 数据源、资产、指标、Connector SPI、OpenSearch 索引 |
| 3 | Query Workflow、Semantic Registry、SQL Guard、Query Proxy |
| 4 | 事件接入、Incident 聚合、Evidence、规则 RCA |
| 5 | Runbook DSL、Policy、Temporal 审批、Executor Agent |
| 6 | Model Gateway、Agent Team、通知、压测、安全和容灾 |

## 16. 后端验收

所有接口具备 OpenAPI；所有状态机拒绝非法转换；写 SQL/越权查询 100% 拦截；异步流程可恢复、可取消、可审计；消息重复不造成重复执行；生产 Executor 不支持任意 Shell；至少一个本地模型、一个 OpenAI-compatible 模型和一个云模型通过能力探测、路由和故障降级测试。
