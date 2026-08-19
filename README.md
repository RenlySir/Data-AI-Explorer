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

## 统一技术与交付约定

- 控制面：Java 21 + Spring Boot 3 模块化单体；Python 3.12 AI/采集 Worker。
- 前端：React + TypeScript + Vite；API 前缀为 `/api/v1`。
- 工作流与事件：Temporal + Kafka；异步请求返回 `202 + operation_id`，状态通过 SSE 推送。
- 数据：PostgreSQL、Redis、OpenSearch、S3/MinIO；全链路使用 OpenTelemetry。
- 模型：通过 Model Gateway 统一接入 OpenAI-Compatible、Ollama、vLLM、TGI、云模型和企业自建模型。
- 安全：默认只读、RBAC + ABAC、RLS、SQL AST 校验、Executor 隔离、审批、验证、回滚和全量审计。
- 部署：支持 Docker Compose 本地版、Helm/Kubernetes 内网版和无公网完全离线版。

## 当前状态

当前版本已包含可运行的 Vite 前端、FastAPI 智能问数、AIOps SQL 优化和多场景中心联调切片：支持 TiDB MCP、Text2SQL、ECharts、CSV/Parquet、TiDB 7.5-8.5 SQL 优化；场景中心覆盖《多场景探索》的 12 个 Agent Team 模板，并支持运行实例、步骤推进、证据、审计和高风险审批门禁。真实外部系统 Adapter、模型网关、认证权限和持久化仍需按专项测试报告完成生产集成验收。

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

## 参考资料

- [智能问数场景](https://pingcap-cn.feishu.cn/wiki/JJpUwKZ4FiuI6lkCkCQcHf3bn8f)
- [AIOPS](https://pingcap-cn.feishu.cn/wiki/KiZCwMR9ziz47UkgXbtcekrdnvg)
- [多场景探索](https://pingcap-cn.feishu.cn/wiki/SRmBwpk7QiaXZFkM9bYciwWfnJe)
