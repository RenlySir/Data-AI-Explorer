# 企业 AI 落地平台部署运维设计方案

版本：v1.0
日期：2026-08-19
适用系统：Aegis AI Control Plane

依据：[详细架构设计方案](企业AI落地平台-详细架构设计方案.md)、[前端开发设计方案](企业AI落地平台-前端开发设计方案.md)和[后端开发设计方案](企业AI落地平台-后端开发设计方案.md)。部署配置、监控指标和应急流程应与代码版本绑定发布。

## 1. 运维目标

保证平台在本地、企业内网和完全离线环境中可安装、可升级、可监控、可备份、可恢复。核心控制面可用性目标 99.9%，RPO ≤15 分钟，RTO ≤60 分钟；生产执行默认受审批和回滚策略约束。

## 2. 交付形态

| 形态 | 适用 | 推荐资源 | 交付方式 |
|---|---|---|---|
| 本地开发版 | 开发、演示、单用户 PoC | 4～8 CPU、16～32GB RAM、100GB | Docker Compose + 可选 Ollama |
| 内网生产版 | 企业私有云、正式试点 | K8s 3 节点起、16 CPU/节点 | Helm + 内部 Registry |
| 完全离线版 | 涉密、无公网 | 按规模配置 GPU/存储 | 签名离线包 + 私有模型权重 |

控制面、数据面、执行面分别部署；生产 Executor Agent 位于目标安全域，主动出站连接 Executor Gateway，不开放入站端口。

## 3. 环境与网络分区

```text
用户区
  → DMZ：WAF / Ingress / SSO 回调
  → 控制区：Web、BFF、PostgreSQL、Redis、Temporal、Kafka
  → 数据区：Connector、OpenSearch、对象存储、数据库只读代理
  → 执行区：Executor Gateway、Executor Agent、目标 K8s/主机
  → 模型区：vLLM/Ollama/TGI/自建模型服务
```

生产 Namespace：`aegis-control`、`aegis-data`、`aegis-execution`、`aegis-model`、`aegis-observability`。NetworkPolicy 默认拒绝；只允许明确端口和服务账号。数据源仅允许来自 Connector/Query Proxy 的只读网络连接；Executor 不访问控制面数据库。

## 4. Docker Compose 本地部署

### 4.1 服务

`web`、`server`、`ai-worker`、`connector-worker`、`postgres`、`redis`、`opensearch`、`minio`、`kafka`、`temporal`。`local-model` Profile 可启动 Ollama；未启用时通过 `.env` 指向自建或云模型。

### 4.2 安装流程

```bash
cp .env.example .env
./bin/aegis config validate
./bin/aegis image verify
./bin/aegis db migrate
./bin/aegis up --profile core
./bin/aegis bootstrap-admin
./bin/aegis health
```

安装向导必须校验 Docker 版本、磁盘、端口、时钟、镜像完整性和 Secret。默认只监听本机；对内网开放前必须配置 TLS、管理员口令、OIDC 或受控本地账号。

### 4.3 本地备份

`aegis backup` 备份 PostgreSQL、配置清单、MinIO 元数据和模型 Provider 配置引用，不导出明文 Secret。默认写入指定目录，生成 manifest、校验和恢复说明；本地模型权重单独备份。

## 5. Kubernetes 生产部署

### 5.1 前置依赖

Kubernetes 1.28+、Ingress Controller、cert-manager（或企业证书系统）、StorageClass、内部 Registry、Vault/OpenBao、Prometheus Operator、Loki/OpenSearch、企业 DNS 和 NTP。

### 5.2 Helm 部署

```bash
helm dependency build deploy/helm/aegis
helm lint deploy/helm/aegis -f values-prod.yaml
helm template aegis deploy/helm/aegis -n aegis-control -f values-prod.yaml > rendered.yaml
kubectl apply --server-side -f rendered.yaml
helm upgrade --install aegis deploy/helm/aegis \
  -n aegis-control --create-namespace -f values-prod.yaml --atomic --timeout 15m
```

生产 values 必须通过 Git 管理，Secret 使用 External Secrets/Vault Agent 注入。禁止把密钥写进 Helm values、镜像或 Git。

### 5.3 资源与高可用基线

Web/Server/AI Worker/Connector 至少 2 副本，配置 requests/limits、HPA、PDB、反亲和和 topology spread。PostgreSQL 使用托管 HA 或 Patroni；Kafka、OpenSearch 至少 3 节点；Temporal 使用 HA 数据库；MinIO/对象存储开启版本化和跨节点冗余。

GPU 模型节点使用污点 `workload=aegis-model`、专用 RuntimeClass、显存指标和独立 HPA。模型权重挂载只读 PVC；升级采用新 Deployment 灰度，不原地覆盖权重。

## 6. 完全离线交付

离线包包含 OCI 镜像 tar/镜像清单、Helm/Compose、SBOM、签名、SHA256、数据库迁移、前端静态资源、Python wheel、模型权重、默认配置和操作手册。

交付流程：联网构建机生成并签名 manifest → 安全介质转移 → 离线环境验签 → 导入内部 Registry → 导入模型与依赖 → dry-run → 部署。每次导入记录版本、来源、操作者和 hash。

离线模式设置 `egressPolicy=deny`：关闭云 Provider、在线更新、外部遥测和公网回调；模型、漏洞库、许可证和时钟支持离线导入。启动自检必须明确显示“离线模式”，不得因网络探测失败阻断平台核心功能。

## 7. 配置、密钥与证书

配置分为公开 ConfigMap、Secret/Vault 引用和租户配置。启动时执行 JSON Schema 校验；缺少关键配置直接失败，不用危险默认值。

密钥策略：

- 数据源、模型、通知和 Executor 凭证只保存 Vault path。
- Connector/Query Proxy 获取短期动态凭证，使用后清理内存。
- Vault Token 通过 Kubernetes Auth 获取并自动轮换。
- TLS 证书由 cert-manager 或内部 CA 管理，提前 30 天告警。
- 生产环境禁止使用本地账号作为日常登录，保留 break-glass 账号并双人保管。

## 8. 监控与告警

### 8.1 观测栈

OpenTelemetry Collector 接收 Trace/Metric/Log；Prometheus 采集指标；Grafana 展示；Loki 或 OpenSearch 保存日志；Alertmanager 发送飞书/企微/钉钉通知。

### 8.2 核心指标

| 类别 | 指标 |
|---|---|
| 可用性 | API 5xx、Ingress 错误、登录成功率、SSE 断开 |
| 性能 | API P95、问数首 token、查询耗时、血缘查询耗时 |
| 队列 | Kafka lag、Temporal pending workflow、Connector backlog |
| 模型 | 请求量、P95、Token、错误、降级、GPU 显存、吞吐 |
| 数据 | 采集延迟、血缘解析失败、资产数量、索引失败 |
| 执行 | Runbook 成功、失败、回滚、审批超时、Executor 在线数 |
| 安全 | 认证失败、越权拒绝、SQL 拦截、策略拒绝、Secret 轮换 |

### 8.3 告警分级

P0：控制面不可用、数据泄露、Executor 未授权执行；立即电话/升级。P1：问数大面积失败、Kafka/Temporal 堵塞、审计落盘中断；15 分钟响应。P2：单连接器故障、模型延迟升高、索引滞后；工作时间处理。P3：容量趋势、证书即将到期、评测下降；计划处理。

告警必须带服务、环境、租户影响、开始时间、Runbook、负责人和升级路径；相同 fingerprint 合并并设置静默窗口。

## 9. 日常运维流程

### 9.1 每日巡检

检查控制面健康、Kafka lag、Temporal workflow、数据库连接/锁/磁盘、OpenSearch 集群、对象存储容量、模型健康、证书、备份结果、Executor 在线和高风险审计事件。

### 9.2 每周维护

复盘问数正确率、SQL 拦截、RCA 采纳率、Runbook 成功/回滚、模型成本与延迟；清理过期 Query Result；检查未发布指标、失败血缘和长期运行任务；抽查审计完整性。

数据关系采集 Worker 使用独立只读数据库账号：允许读取业务 `INFORMATION_SCHEMA.TABLES/COLUMNS/KEY_COLUMN_USAGE`，TiDB SQL 关系采集再按版本授予 `STATEMENTS_SUMMARY_HISTORY` 所需的最小监控权限。禁止授予 DDL/DML 权限。PoC 使用 API 进程内常驻任务，页面关闭后仍运行，但服务重启会丢失调度状态；生产由持有任务租约的调度器按 `collector_checkpoint` 执行，建议默认 5 分钟，失败指数退避，按 Digest 幂等。SQL Literal 入库前脱敏，观察记录设置租户级保留期。

### 9.3 月度维护

执行漏洞扫描、依赖更新评估、权限回收、备份恢复抽测、容量预测、模型离线评测和 Runbook 过期复审。高风险动作和模型路由变更必须走变更单。

## 10. 备份、恢复与容灾

备份对象：PostgreSQL 全量/WAL、MinIO 对象、Kafka 关键 Topic、Temporal 数据、OpenSearch 可重建索引、Helm values、模型 Provider 配置、审计归档。

建议策略：每日全量、15 分钟 WAL；对象存储版本化；审计 WORM；OpenSearch 以主数据重建为主。每季度进行跨节点恢复和完整业务演练，验证登录、问数、Incident、审批、审计和回滚。

恢复顺序：基础设施 → Vault/CA → PostgreSQL → Kafka/Temporal → Redis → OpenSearch/MinIO → Server/Worker → Model Gateway → Executor Gateway。恢复后暂停自动执行，人工确认数据一致性和审批状态后再开放。

## 11. 发布与升级

场景中心生产部署需要额外配置外部系统 Adapter、短期凭证和 Runbook 白名单。建议先启用只读模式和报告模式，再按场景逐项开放低风险动作；所有高风险动作必须验证审批人权限、双人审批（如适用）、幂等键、超时撤销、执行证据和回滚。场景运行状态迁移到 PostgreSQL/Temporal 后，升级演练需验证服务重启恢复、重复消息去重和审批等待不丢失。

发布流水线：代码检查 → 单测/契约/安全 → 镜像构建与 SBOM → AI 评测 → 测试环境 → 预生产 → Canary/Blue-Green → 生产。

数据库采用 expand/contract：先新增兼容字段/表，再发布应用，确认无旧版本读写后删除旧结构。Helm 使用 `--atomic`；升级前自动备份和 health check；失败自动回滚应用，但数据库迁移回滚需使用兼容迁移脚本。

模型升级：新模型先注册 `DRAFT`，通过能力探测和离线评测，影子流量对比质量/延迟/成本，最后切换路由；保留旧模型和 Prompt 版本，可一键回退。

## 12. 安全运维与审计

运维人员使用 SSO + MFA + 堡垒机；生产 kubectl、数据库和 Executor 操作全部审计。禁止共享账号、复制生产数据到开发环境、直接改生产容器和绕过审批执行 Runbook。

生产动作必须有变更窗口、风险等级、前置检查、审批、dry-run、执行日志、验证和回滚。Critical 动作永久禁止无人值守；异常时优先冻结自动执行、保留证据、通知值班长。

## 13. 故障处理 Runbook

### 13.1 控制面不可用

确认 Ingress、Server Pod、数据库和依赖健康；若发布引起则回滚镜像；若数据库故障切换 HA；保持告警接收和审计队列；恢复后核对未完成 Workflow，不自动重放有副作用动作。

### 13.2 Kafka/Temporal 堵塞

查看 lag、失败原因、死信；扩容消费者；暂停低优先级采集；修复后按 event_id 重放。执行类 Workflow 必须人工确认，不用简单重试解决不确定状态。

### 13.3 模型不可用

确认 Model Gateway、Provider、GPU、限流和网络；按数据边界切换已验证备用模型；若无合规备用，问数转指标目录/人工审核，RCA 转规则模式；禁止自动切公网。

### 13.4 Executor/动作状态不明

停止重试，查询 Agent 和目标系统真实状态；标记 `HUMAN_REQUIRED`；确认是否已执行、是否需要回滚；补齐证据后关闭或重新审批。

## 14. 容量与扩容

当 API P95 连续 15 分钟超过 500ms，扩容 Web/Server；Kafka lag 超阈值扩容消费者；模型 GPU 显存超过 85% 或首 token 超 SLO 扩容 GPU/切换模型；OpenSearch 磁盘 70% 触发扩容或生命周期清理；PostgreSQL 连接池超过 70% 评估读副本/拆分查询。

租户限额：并发问数、Token、扫描量、结果存储、事件速率和 Agent 预算。超额返回可解释的配额错误，不允许通过重试绕过。

## 15. 运维交付物

必须随版本交付：Helm/Compose、values 示例、端口与依赖清单、配置 Schema、数据库迁移、备份恢复脚本、监控 Dashboard、告警规则、Runbook、SBOM、漏洞报告、变更记录和回滚说明。

## 16. 运维验收标准

- 本地版在无公网环境可安装、启动、健康检查、备份和恢复。
- K8s 生产版可滚动升级、Canary、回滚，Pod 故障自动拉起。
- RPO/RTO 演练达标，审计和审批状态不丢失。
- P0/P1 告警在 5 分钟内可发现并通知责任人。
- 模型 Provider、GPU、Connector、Executor 具备健康检查和降级路径。
- 任何高风险动作均能追溯发起人、审批、参数、执行、验证和回滚。
- 离线包可验签，公网 egress 关闭后核心功能仍可用。

## 17. 知识库部署补充

本地知识库随 FastAPI 运行；允许目录由只读卷和 DATASET_ALLOWED_ROOTS 控制。生产新增 knowledge-worker、对象存储、全文索引、向量库和本地 Embedding/Reranker。监控入库队列、解析/Embedding 失败、Chunk 分布、召回延迟、无结果率、Citation Coverage 和索引版本；恢复时先还原元数据与原文，再恢复或重建索引并做 checksum 对账。

## 18. 模块化部署单元

| 部署单元 | 本地 Compose | 内网 Kubernetes | 资源/扩容依据 |
|---|---|---|---|
| Web/BFF | `web` | web + gateway | 页面请求、API P95 |
| API 控制面 | FastAPI MVP | api 多副本 | API P95、连接池 |
| Query/SQL Worker | API 内置 | query-worker、sql-worker | 问数并发、EXPLAIN 延迟 |
| Knowledge Worker | 可选关闭 | parser/index/embed/rerank | 文档队列、Chunk 吞吐、GPU |
| Scenario/Temporal | 演示内存 | temporal server/worker | 运行实例、步骤耗时 |
| Connector/Executor | 不连接生产 | adapter、executor-gateway | 外部调用速率、动作队列 |
| 数据底座 | PostgreSQL、Redis、MinIO | HA PostgreSQL、Redis、S3/OpenSearch/Vector | 数据量、索引、保留期 |

本地环境默认只开放 Web、API、PostgreSQL、Redis、MinIO；生产 Adapter、模型 Provider 和 Executor 必须通过环境变量显式启用，默认关闭。

## 19. 配置与密钥边界

配置分为 `platform`、`datasource`、`model`、`connector`、`policy`、`observability` 六类。配置文件只存引用和非敏感参数；密钥、数据库密码、模型 Token 和机器凭证存 Vault/OpenBao，通过短期租约注入。前端只显示 Provider 名称、能力和健康，不回显密钥。

关键环境变量：`API_BASE_URL`、`DATABASE_URL`、`REDIS_URL`、`S3_ENDPOINT`、`DATASET_ALLOWED_ROOTS`、`MODEL_GATEWAY_URL`、`MODEL_LOCAL_ONLY`、`EXECUTOR_ENABLED`、`CORS_ALLOW_LOCALHOST`、`CORS_ALLOW_ORIGINS`、`OTEL_EXPORTER_OTLP_ENDPOINT`。生产启动前执行配置 Schema 校验，缺少安全边界直接阻断。

本地版本默认 `CORS_ALLOW_LOCALHOST=true`，支持 localhost/127.0.0.1 动态开发端口。预生产和生产必须设置为 `false`，并在 `CORS_ALLOW_ORIGINS` 中列出网关实际 HTTPS Origin；不得使用 `*` 与凭证模式组合。变更 Origin 后需要执行 OPTIONS 预检和登录、问数、功能目录三条浏览器回归。

## 20. 发布、回滚和数据保护

发布顺序：数据库向前兼容迁移 → API → Worker → Web → Connector/Executor。产品目录和策略先在测试租户发布，完成契约测试后灰度。回滚只回滚镜像和配置，不回滚已写入的审计；数据库迁移使用 expand/contract，索引使用版本别名。

备份：PostgreSQL 每日全备 + WAL，MinIO 版本与跨节点副本，OpenSearch/Vector DB 保存快照；每月演练恢复并校验资产、知识文档、审批和审计数量。目标基线：控制面 RPO ≤15 分钟、RTO ≤60 分钟；索引可重建但原文不可丢失。

## 21. 按模块的运行手册

| 模块 | 关键健康指标 | 降级策略 | 禁止动作 |
|---|---|---|---|
| 智能问数 | SQL P95、拦截率、模型延迟、空结果率 | 只读指标目录/历史结果 | 模型故障时切公网 |
| 知识库 | 入库队列、索引失败、Recall、Citation Coverage | 词法检索/人工查询 | 无 ACL 召回 |
| 数据治理 | 元数据采集延迟、血缘失败、质量规则延迟 | 保留最近快照 | 直接覆盖资产事实 |
| AIOps | 告警延迟、RCA 证据覆盖、事件堆积 | 规则 RCA、人工接管 | 状态不明自动重试 |
| SQL 优化 | 版本画像加载、分析耗时、真实计划错误 | 仅模拟并明确标记 | 冒充真实 EXPLAIN |
| 场景/执行 | Workflow 失败、审批超时、动作状态不明 | 冻结动作、人工处理 | 任意 Shell、永久凭证 |
| 平台管理 | Provider/Connector 健康、审计延迟、策略版本 | 只读模式、禁止高风险 | 绕过审批或审计 |

## 22. 运维验收新增项

- 功能目录接口在 200ms 内返回，过滤结果与页面功能数量一致。
- 每个生产启用功能都有 Owner、SLO、健康检查、降级和回滚 Runbook。
- 每个场景运行至少验证一次重复消息、Worker 重启、审批超时、执行状态不明。
- 离线部署关闭公网 egress 后，功能目录、知识库本地检索、SQL 模拟和场景演示仍可运行。
