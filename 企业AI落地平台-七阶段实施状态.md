# 七阶段实施状态

本文将附件中的“代码质量与工程规范、前端体验、后端稳定性、测试、部署运维、安全、项目管理”实施清单，与当前仓库中已经可以运行和验证的内容对齐，作为研发交付边界说明。

## 已落地并验证

| 阶段 | 当前实现 | 验证方式 |
|---|---|---|
| 工程规范 | 前端 ESLint 9、TypeScript typecheck、Prettier；后端 compileall；GitHub Actions CI | `npm run lint`、`npm run typecheck`、`npm run format:check`、`npm run build`、`pytest` |
| 前端体验 | 可收起侧栏、64px 顶栏、环境标识、登录错误态；ChatBI 三栏结果区；统一 OperationProgress；SSE 断线有限重连 | Vite 构建通过；远端控制节点页面返回最新静态包 |
| 后端稳定性 | 请求 ID、安全响应头、Prometheus 文本指标、ChatBI SSE 阶段事件；只读 SQL 防护与数据源访问控制 | 52 个后端测试；远端 `/health`、`/metrics`、ChatBI/SSE 实测 |
| 部署运维 | Compose、本地开发脚本、前后端 Dockerfile、Nginx SPA 配置、Helm chart、三节点 systemd 部署脚本 | Compose 配置校验、脚本语法检查、三节点健康验证 |
| 数据与演示 | TiDB 元数据和审计表、演示业务数据、MCP/直连降级路径、CSV/Parquet/DuckDB；默认 Compose 已切换 TiDB | 三台 TiDB 均返回 ready，版本为 `v9.1.0`；真实 `aegis_demo` 数据源、关系采集和 ChatBI 通过 |

## 当前运行形态

当前可运行交付基线使用 React/Vite 前端和 FastAPI/Python 后端，原因是仓库现有代码与三节点演示环境已经按该形态部署。产品、架构和后端设计文档仍保留 Java 21/Spring Boot 3 控制面、Temporal、Kafka/Outbox 等企业级目标架构；这些内容是迁移与生产演进目标，不应视为本次 FastAPI MVP 已经实现的事实。

三节点演示入口：

- Web：`http://10.2.106.5:18081`
- API 文档：`http://10.2.106.5:18082/docs`
- API 指标：`http://10.2.106.5:18082/metrics`

## 尚未达到企业生产退出标准

以下事项仍需在生产化迭代中完成，并应单独建立验收任务：

1. 将 FastAPI 控制面按设计拆分为 Spring Boot 领域模块和独立 Python AI/Connector Worker。
2. 用 Temporal 持久化长流程检查点，用 Kafka/Outbox 解耦审计和通知，并实现多实例互斥。
3. 将模型密钥、数据源凭证和 Agent 配置迁移到 Vault/OpenBao/KMS 加密存储，接入完整 RBAC/ABAC 与租户隔离。
4. 将当前进程内工作集迁移到租户化 TiDB 表和对象存储；知识库生产检索接入 TiDB 向量索引或 OpenSearch。
5. 补齐 Playwright 浏览器旅程、Testcontainers 集成测试、JMeter/Gatling 压测，以及真实 Prometheus/OpenTelemetry/Jaeger 验收。
6. 在具备 Docker daemon 的构建机上完成镜像构建、漏洞扫描、签名和离线镜像仓库发布；在具备 Helm CLI/Kubernetes 集群的环境执行 `helm template`、安装、升级和回滚演练。

## 生产验收原则

任何页面功能必须有对应 API、权限和审计记录；任何模型生成的 SQL 必须经过 AST 只读校验、数据源权限校验和超时/行数限制；任何高风险 AIOps 或指挥动作必须停在人工审批门禁。模拟的 TiDB 优化计划只能作为假设，只有在目标 TiDB 版本的真实 `EXPLAIN` 验证后才可用于生产建议。
