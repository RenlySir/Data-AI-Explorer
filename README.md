# Data AI Explorer

企业 AI 落地平台 Aegis AI Control Plane 的产品与工程设计文档。

本仓库当前以设计基线为主，覆盖智能问数、AIOps、数据关系治理、智能指挥/决策、多模型接入、本地部署和完全离线部署。文档按“产品 → 架构 → 开发 → 交付运维”组织，可直接作为研发立项和 Sprint 拆分输入。

## 文档导航

| 顺序 | 文档 | 用途 |
|---|---|---|
| 1 | [产品设计方案](企业AI落地平台-产品设计方案.md) | 产品定位、用户、模块、原型、MVP 和路线图 |
| 2 | [详细架构设计方案](企业AI落地平台-详细架构设计方案.md) | 控制面/数据面/执行面、数据模型、接口、模型网关和容量基线 |
| 3 | [前端开发设计方案](企业AI落地平台-前端开发设计方案.md) | React 工程、页面、组件、状态、交互、测试 |
| 4 | [后端开发设计方案](企业AI落地平台-后端开发设计方案.md) | Spring Boot、AI Worker、API、事件、数据库、执行链路 |
| 5 | [部署运维设计方案](企业AI落地平台-部署运维设计方案.md) | 本地、内网 Kubernetes、完全离线、监控、备份、升级和应急 |

## 统一技术与交付约定

- 控制面：Java 21 + Spring Boot 3 模块化单体；Python 3.12 AI/采集 Worker。
- 前端：React + TypeScript + Vite；API 前缀为 `/api/v1`。
- 工作流与事件：Temporal + Kafka；异步请求返回 `202 + operation_id`，状态通过 SSE 推送。
- 数据：PostgreSQL、Redis、OpenSearch、S3/MinIO；全链路使用 OpenTelemetry。
- 模型：通过 Model Gateway 统一接入 OpenAI-Compatible、Ollama、vLLM、TGI、云模型和企业自建模型。
- 安全：默认只读、RBAC + ABAC、RLS、SQL AST 校验、Executor 隔离、审批、验证、回滚和全量审计。
- 部署：支持 Docker Compose 本地版、Helm/Kubernetes 内网版和无公网完全离线版。

## 当前状态

当前版本为设计基线 v1.0，尚未包含可运行代码。建议下一步按三个首期场景启动实现：夜间跑批值守、20 个核心指标智能问数、数据目录与基础血缘。

## 参考资料

- [智能问数场景](https://pingcap-cn.feishu.cn/wiki/JJpUwKZ4FiuI6lkCkCQcHf3bn8f)
- [AIOPS](https://pingcap-cn.feishu.cn/wiki/KiZCwMR9ziz47UkgXbtcekrdnvg)
- [多场景探索](https://pingcap-cn.feishu.cn/wiki/SRmBwpk7QiaXZFkM9bYciwWfnJe)
