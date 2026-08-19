# Data AI Explorer

企业 AI 落地平台 Aegis AI Control Plane 的产品与工程设计文档。

本仓库当前以设计基线为主，覆盖智能问数、AIOps、数据关系治理、智能指挥/决策、多模型接入、本地部署和完全离线部署。文档按“产品 → 架构 → 开发 → 交付运维”组织，可直接作为研发立项和 Sprint 拆分输入。

## 文档导航

| 顺序 | 文档 | 用途 |
|---|---|---|
| 1 | [产品设计方案](企业AI落地平台-产品设计方案.md) | 产品定位、用户、模块、原型、MVP 和路线图 |
| 2 | [原型设计方案](企业AI落地平台-原型设计方案.md) | 登录后主流程、页面线框、点击行为、状态和跳转关系 |
| 3 | [竞品与开源项目学习报告](企业AI落地平台-竞品与开源项目学习报告.md) | 优秀产品模式、开源选型、可借鉴点和 PoC 建议 |
| 4 | [详细架构设计方案](企业AI落地平台-详细架构设计方案.md) | 控制面/数据面/执行面、数据模型、接口、模型网关和容量基线 |
| 5 | [前端开发设计方案](企业AI落地平台-前端开发设计方案.md) | React 工程、页面、组件、状态、交互、测试 |
| 6 | [后端开发设计方案](企业AI落地平台-后端开发设计方案.md) | Spring Boot、AI Worker、API、事件、数据库、执行链路 |
| 7 | [部署运维设计方案](企业AI落地平台-部署运维设计方案.md) | 本地、内网 Kubernetes、完全离线、监控、备份、升级和应急 |
| 8 | [专项测试方案与执行报告](企业AI落地平台-专项测试方案与执行报告.md) | 功能、接口、安全、性能、部署、E2E 测试和当前缺陷 |
| 9 | [智能问数模块开发说明](智能问数模块开发说明.md) | TiDB MCP、Text2SQL、ECharts、CSV/Parquet 和目录分析 |
| 10 | [智能问数模块专项测试方案与执行报告](智能问数模块-专项测试方案与执行报告.md) | 功能、接口、安全、浏览器联调、集成测试边界和生产退出标准 |
| 11 | [SQL 优化模块开发说明](SQL优化模块开发说明.md) | TiDB 版本画像、SQLAdvisor 方法、模拟/真实 EXPLAIN、接口与安全边界 |
| 12 | [SQL 优化模块专项测试方案与执行报告](SQL优化模块-专项测试方案与执行报告.md) | 版本差异、规则、输入、真实计划门禁和生产验收标准 |
| 13 | [多场景中心开发说明](多场景中心开发说明.md) | 12 个 Agent Team 场景、运行状态机、审批门禁和外部适配器规划 |
| 14 | [多场景中心专项测试方案与执行报告](多场景中心-专项测试方案与执行报告.md) | 场景完整性、运行推进、审批安全和生产验收边界 |
| 15 | [知识库模块产品与研发设计方案](知识库模块产品与研发设计方案.md) | LangChain/RAG 产品、架构、前后端、部署与演进设计 |
| 16 | [知识库模块专项测试方案与执行报告](知识库模块-专项测试方案与执行报告.md) | 入库、检索、引用、安全、回归与生产测试基线 |
| 17 | [场景功能与用户操作手册](企业AI落地平台-场景功能与用户操作手册.md) | 业务场景到具体模块、功能、点击路径、结果和风险边界 |
| 18 | [模块与功能详细设计方案](企业AI落地平台-模块与功能详细设计方案.md) | 8 个一级模块、63 项功能、输入产出、门禁、状态与代码追踪 |
| 19 | [模块 Agent 功能开发说明](模块Agent功能开发说明.md) | 一键装配、模型绑定、工具白名单、审批策略、接口与验收边界 |
| 20 | [七阶段实施状态](企业AI落地平台-七阶段实施状态.md) | 附件实施清单与当前可运行代码、验证结果、生产化边界对照 |

## 统一技术与交付约定

- 控制面：Java 21 + Spring Boot 3 模块化单体；Python 3.12 AI/采集 Worker。
- 前端：React + TypeScript + Vite；API 前缀为 `/api/v1`。
- 工作流与事件：Temporal + Kafka；异步请求返回 `202 + operation_id`，状态通过 SSE 推送。
- 数据：优先使用 TiDB 保存平台元数据和可查询业务数据；本地 Compose 仍提供 PostgreSQL、Redis、OpenSearch、S3/MinIO 作为后续生产扩展位，全链路使用 OpenTelemetry。
- 模型：通过 Model Gateway 统一接入 OpenAI-Compatible、Ollama、vLLM、TGI、云模型和企业自建模型。
- 安全：默认只读、RBAC + ABAC、RLS、SQL AST 校验、Executor 隔离、审批、验证、回滚和全量审计。
- 部署：支持 Docker Compose 本地版、Helm/Kubernetes 内网版和无公网完全离线版。
- 工程门禁：前端 `npm run lint`、`npm run typecheck`、`npm run format:check`、`npm run build`；后端 `pytest`、`compileall`；GitHub Actions 在 PR 和主干推送时自动执行。
- 镜像：提供 [backend/Dockerfile](backend/Dockerfile) 和 [apps/web/Dockerfile](apps/web/Dockerfile)，Web 镜像使用 Nginx SPA fallback，API 镜像以非开发 reload 模式启动。

## 当前状态

本轮按附件七阶段清单完成了可在当前仓库直接运行的工程化切片。实现边界和未完成的企业生产化事项见[七阶段实施状态](企业AI落地平台-七阶段实施状态.md)；当前可运行后端是 FastAPI，设计文档中的 Spring Boot/Temporal/Kafka 是后续迁移目标。

知识库现已支持 LangChain 递归/Markdown 标题分块、关键词/字符语义/混合索引、可调相似度阈值，以及文档启停、重建、删除和引用核验。

当前版本已包含可运行的 Vite 前端、FastAPI 智能问数、数据关系、AIOps SQL 优化、多场景中心和知识库联调切片。“功能中心”作为 8 个模块、63 项功能的统一操作入口；首次登录会引导接入公有或私有大模型。模型验证后可一键创建 8 个模块 Agent，系统自动绑定当前模型、装配模块能力与工具白名单，并提供启停、配置自检和建议模式对话测试；高风险模块默认要求人工审批。平台管理提供唯一的数据源管理页，已打通 TiDB/MySQL 手动添加、CSV/Parquet 上传、连接测试、删除以及带选中数据源进入 ChatBI；智能问数只在聊天框顶部选择已配置数据源。数据关系页可选择数据库，采集全量业务 Schema、表、字段 Comment、外键和 TiDB 关联查询 SQL，并以表级/字段级力导向网络图展示；服务端进程内采集任务在页面关闭后仍可运行。智能问数已提供 SSE 阶段事件、断线重连、统一执行进度和请求追踪 ID。三节点部署已将工作空间设置和操作审计落入 TiDB `aegis_platform.platform_settings`、`aegis_platform.audit_events`，API 重启后可恢复；当前无需额外部署向量数据库，知识库演示使用本地可降级检索，生产接入 TiDB 向量索引或 OpenSearch 时再按专项方案扩展。生产凭证库、Agent/关系持久化、认证权限和具备持久化检查点及多实例互斥的独立 Worker 仍需按专项测试报告完成集成验收。

## 本地开发

环境要求：Docker Desktop（含 Compose v2）或 Node.js 22+；直接运行后端需要 Python 3.12+。

```bash
./scripts/dev.sh
```

打开 <http://localhost:5173> 访问前端；API 文档为 <http://localhost:8080/docs>。基础设施端口为 PostgreSQL `5432`、Redis `6379`、MinIO API `9000`，MinIO 控制台为 <http://localhost:9001>。首次启动会自动创建 `.env`；可按需修改后重新运行。

停止服务：

```bash
docker compose down
```

删除本地持久化数据（仅用于重置开发环境）：

```bash
docker compose down -v
```

直接运行前端（不启动基础设施）可执行 `cd apps/web && npm install && npm run dev`。

## 三节点演示部署

目标环境若已有 `10.2.106.5`、`10.2.106.124`、`10.2.106.182` 三节点 TiDB，可按 [三节点部署说明](企业AI落地平台-部署运维设计方案.md#44-三节点-tidb-演示部署已提供脚本) 使用 systemd 部署。脚本会把控制面、AI Worker 和运维 Worker 分配到三台主机，并提供模块状态与 TiDB 连通性检查；不会修改已有 `/opt/tidb-v91` 数据。平台元数据数据库由 API 启动时幂等创建，也可运行 `AEGIS_PLATFORM_DB_*` 环境变量配合 `scripts/migrate_platform_tidb.py` 显式初始化。

## 参考资料

- [智能问数场景](https://pingcap-cn.feishu.cn/wiki/JJpUwKZ4FiuI6lkCkCQcHf3bn8f)
- [AIOPS](https://pingcap-cn.feishu.cn/wiki/KiZCwMR9ziz47UkgXbtcekrdnvg)
- [多场景探索](https://pingcap-cn.feishu.cn/wiki/SRmBwpk7QiaXZFkM9bYciwWfnJe)
- [LangChain Retrieval](https://docs.langchain.com/oss/python/langchain/retrieval)
- [LangChain Text Splitters](https://github.com/langchain-ai/langchain/tree/master/libs/text-splitters)（MIT；当前知识库使用 Python 3.9 兼容的 `langchain-text-splitters` 0.3.x，并保留离线降级）
