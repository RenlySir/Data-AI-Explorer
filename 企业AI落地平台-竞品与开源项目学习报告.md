# 企业 AI 落地平台竞品与开源项目学习报告

版本：v1.0
日期：2026-08-19
调研范围：智能问数、数据治理、AIOps、自动执行、企业 AI 控制平面

## 1. 调研结论

Aegis 不应复制某一个产品，而应组合五类成熟模式：

1. WrenAI/SuperSonic：语义层先于 Text-to-SQL，回答必须受指标和关系约束。
2. SQLBot：中文用户低门槛，问数入口简单，结果自然衔接图表。
3. OpenMetadata/DataHub：以资产对象页组织 Schema、血缘、质量、负责人和讨论。
4. HolmesGPT + Dynatrace/Datadog：规则、拓扑和观测证据优先，LLM 负责归纳和下一步行动。
5. StackStorm/Rundeck：AI 不直接执行任意命令，动作必须来自版本化、授权和可审计的 Runbook。

因此 Aegis 的差异化不应是“更多聊天框”，而是跨问数、资产、Incident、任务、审批和执行的统一对象与证据链。

## 2. 值得学习的开源项目

GitHub Star 和更新时间为 2026-08-19 调研快照，只用于判断生态活跃度，不等于技术或商业适配度。

| 项目 | 方向 | 快照 | 重点学习 | 对 Aegis 的建议 |
|---|---|---:|---|---|
| [WrenAI](https://github.com/Canner/WrenAI) | GenBI、语义/上下文层 | 17.3k | 受治理的 Text-to-SQL、可信 Dashboard、多数据源 | 借鉴语义模型和回答证据，不直接绑定其完整产品 |
| [SQLBot](https://github.com/dataease/SQLBot) | 中文智能问数 | 6.6k | 快速问数、RAG、可视化、本地部署体验 | 学习中文开箱体验和问题模板 |
| [SuperSonic](https://github.com/tencentmusic/supersonic) | Chat BI + Headless BI | 5.0k | Chat 与语义层统一、指标 API 化 | 学习确定性指标编译和开放分析分流 |
| [DB-GPT](https://github.com/eosphoros-ai/DB-GPT) | 数据 Agent 平台 | 19.7k | Agent、RAG、数据库工具和多模型 | 作为 AI Worker/Agent 能力参考，不作为治理与权限底座 |
| [OpenMetadata](https://github.com/open-metadata/OpenMetadata) | 数据目录、治理、AI Context | 14.9k | 资产页、字段血缘、质量、术语、130+ Connector | 优先研究其元数据模型和 Connector，可考虑集成而非重写全部 |
| [DataHub](https://github.com/datahub-project/datahub) | 数据与 AI Context Platform | 12.5k | 搜索、Graph、元数据事件、治理工作流 | 学习元数据事件和搜索体验，与 OpenMetadata 二选一 PoC |
| [OpenLineage](https://github.com/OpenLineage/OpenLineage) | 运行时血缘标准 | 2.6k | Job、Run、Dataset 标准事件 | 直接采用为血缘输入标准，不自创协议 |
| [HolmesGPT](https://github.com/HolmesGPT/holmesgpt) | SRE Agent | 3.1k | Kubernetes/可观测数据调查、工具集、证据化诊断 | 可作为 RCA Worker 或设计参考，仍需 Aegis 权限审批层 |
| [PyRCA](https://github.com/salesforce/PyRCA) | 根因分析算法 | 566 | 图模型、时序异常、可解释 RCA | 用于统计 RCA 补充，避免全部依赖 LLM |
| [StackStorm](https://github.com/StackStorm/st2) | 事件驱动自动化 | 6.5k | Rule、Workflow、Integration Pack、ChatOps | 适合事件到动作底座，Aegis 负责 AI 决策和审批 |
| [Rundeck](https://github.com/rundeck/rundeck) | Runbook 自动化 | 6.3k | 自助运维、ACL、作业执行、日志 | 适合首期执行层 PoC，页面和权限成熟 |

许可注意：OpenMetadata、DataHub、OpenLineage、HolmesGPT、StackStorm 和 Rundeck 仓库标识为 Apache-2.0；WrenAI、SQLBot、SuperSonic 的 GitHub API 许可字段未能统一识别，实际复用代码前必须逐仓库和具体版本进行法律审核。

## 3. 商业产品体验参照

| 产品 | 官方定位 | 值得学习 | 不应照搬 |
|---|---|---|---|
| [Datadog Bits AI](https://www.datadoghq.com/product/bits-ai/) | 对话探索可观测数据并采取行动 | AI 嵌入现有监控对象、从问题到动作距离短 | 高度依赖 Datadog 自身数据生态 |
| [Dynatrace Intelligence](https://www.dynatrace.com/platform/artificial-intelligence/) | 确定性洞察与 Agent 行动结合 | 确定性因果/拓扑在前，生成式解释在后 | 大而全平台复杂度不适合 MVP |
| [ThoughtSpot Spotter](https://www.thoughtspot.com/product/spotter) | 可验证的企业分析 Agent | 强调可信、可验证和业务语义 | 不应只做管理驾驶舱，需保留专业用户深度 |
| ServiceNow AI/Workflow | AI Agent 与企业工作流结合 | 任务、审批、责任链和系统记录统一 | 首期不建设庞大的 ITSM 平台 |
| Atlan | 现代数据目录和协作治理 | 搜索优先、资产上下文、责任人和协作 | 不复制营销式主页和卡片堆叠 |

## 4. 产品模式对比

### 4.1 智能问数

优秀产品的共同结构是：问题输入 → 语义理解 → 可见的执行过程 → 结论/图表 → SQL/证据 → 追问或分享。Aegis 应把“为什么这样算”放在结果旁，不藏在高级设置里。

采用：语义层、问题模板、澄清选项、结果与证据并列、反馈闭环。避免：空白聊天首屏、模型自报置信度、只展示 SQL、不说明指标口径。

### 4.2 数据治理

OpenMetadata/DataHub 证明“资产详情页”比单独的血缘大屏更实用。资产页应统一承载 Schema、业务描述、负责人、敏感级别、血缘、质量和查询使用情况。

采用：搜索优先、对象页、渐进展开血缘、治理任务。避免：用户一进入就面对巨大关系画布；为了图谱技术而引入图数据库。

### 4.3 AIOps

HolmesGPT、Datadog 和 Dynatrace 的方向是一致的：AI 必须读取真实观测数据和变更上下文，输出带证据的假设；动作入口应与 Incident 同页。

采用：影响摘要、时间线、证据、RCA、Runbook、验证同页；规则/拓扑优先。避免：让 LLM 直接看一段日志就宣布根因；诊断完成后要求用户跳外部系统执行。

### 4.4 自动执行

StackStorm/Rundeck 的核心价值不是脚本执行本身，而是动作注册、参数 Schema、权限、计划、历史和日志。Aegis 应把它们作为 Executor 后端，而不是重新开发通用远程执行平台。

采用：版本化动作、dry-run、审批、签名任务、验证、回滚。避免：任意 Shell 输入框、Agent 获取永久生产凭证、网络失败后盲目重试。

## 5. 对页面原型的直接改进

1. 工作台按“待办优先”排序，不做纯指标大屏。
2. 问数页将结论、图表、数据、SQL 和证据放在同一任务上下文。
3. 资产详情默认展示摘要，血缘按需展开。
4. Incident 详情合并影响、证据、RCA、Runbook 和执行进度。
5. 作战室默认展示问题和决策，Agent 技术过程作为可展开证据。
6. 管理中心的模型和数据源采用向导式配置与能力探测。
7. AI 助手不单独占据一级导航，而是嵌入问数、事件、资产和任务页面。

## 6. 建议的技术 PoC

| PoC | 组合 | 验证目标 |
|---|---|---|
| 智能问数 | WrenAI 或 SuperSonic + Aegis Query Workflow | 20 个指标正确率、口径治理、权限和证据 |
| 数据治理 | OpenMetadata 与 DataHub 各做一周接入 | Connector、字段血缘、搜索、二次开发成本 |
| AIOps | HolmesGPT + Prometheus/Loki + Aegis Incident | 5 类历史事故证据化 RCA |
| 自动执行 | Rundeck 或 StackStorm + Executor Gateway | 10 个 Runbook 的权限、dry-run、回滚和审计 |

PoC 选择标准：接口开放性 25%、安全与权限 20%、功能适配 20%、二次开发成本 15%、社区/维护 10%、部署运维 10%。不要仅按 Star 数或 Demo 效果决策。

## 7. 最终产品取舍

### 应直接采用标准或成熟底座

- OpenLineage 事件标准、OpenTelemetry 可观测标准。
- Rundeck/StackStorm 类型的执行底座。
- OpenMetadata/DataHub 的元数据连接能力择一集成。

### 应由 Aegis 自己建设

- 跨模块统一工作台和对象导航。
- 企业权限、数据边界、审批、证据和审计控制面。
- 问数、Incident、治理任务和决策之间的流程联动。
- 模型网关、任务级路由、评测和合规降级。

### 暂不建设

- 通用 BI 报表设计器、完整 ITSM、通用 CMDB、通用远程执行平台、自研大模型训练平台。

这些取舍能让首期产品保持简洁，同时通过成熟开源底座获得可落地能力。

## 8. 2026-08 知识库与任务体验专项学习

本轮进一步阅读了 RAGFlow、Dify、FastGPT、MaxKB、AnythingLLM 和 LangChain 的官方文档/仓库，重点观察首次使用路径、检索可解释性、文档处理和企业部署边界。

| 项目 | 官方体验重点 | Aegis 的落地决定 |
|---|---|---|
| [RAGFlow](https://github.com/infiniflow/ragflow) | 深度解析、模板分块、Chunk 可视化、人工核验、混合召回、引用 | 增加文档 Chunk 检查、引用优先和可评测检索；复杂解析接入生产 Worker |
| [Dify](https://github.com/langgenius/dify) | 知识库创建向导、分块预览、索引/检索分步配置、工作流编排 | 页面拆为问答/文档/检索测试/配置四个任务视图；配置与日常问答分离 |
| [FastGPT](https://github.com/labring/FastGPT) | 单点检索测试、Chunk 编辑、引用反馈、调用日志和应用评测 | 增加最近查询、Chunk 预览、回答反馈；生产版增加评测集和回归门禁 |
| [MaxKB](https://github.com/1Panel-dev/MaxKB) | 企业 Agent、RAG Pipeline、工作流、MCP、私有模型和快速集成 | 让知识库作为问数、AIOps、SQL 优化、场景中心的 Retriever Tool |
| [AnythingLLM](https://github.com/Mintplex-Labs/anything-llm) | Workspace 隔离、上传即问、来源引用、本地优先、低配置 | 用知识库范围和权限边界替代无边界聊天；保留本地部署和上传即问体验 |
| [LangChain Retrieval](https://docs.langchain.com/oss/python/langchain/retrieval) | Loader、Splitter、Embedding、Vector Store、Retriever 组件边界；2-Step/Agentic/Hybrid RAG 分流 | 保持适配器边界，MVP 用确定性词法检索，生产替换为 BM25+向量+重排 |

### 8.1 已整合的产品改进

1. 工作台以四个高频任务入口降低首次使用成本：经营数据分析、查询企业知识、诊断 SQL 性能、发起协同任务。
2. 左侧导航按“数据分析 → 运维治理 → 协同执行”排序，用户先按目标找入口，再进入技术详情。
3. 知识库改为问答、文档、检索测试、配置四个任务视图，并补充 Chunk 检查、查询历史和回答反馈。
4. 全系统操作手册用“场景 → 功能 → 输入 → 点击步骤 → 结果 → 风险”描述具体用法，区分已实现、演示闭环和生产接入。

### 8.2 明确不照搬的模式

- 不把所有能力做成一个空白聊天框；企业用户需要对象、权限、证据和下一步动作。
- 不把模型生成的回答或置信度当作事实；结果必须追溯到 SQL、资产、文档片段、监控证据或执行记录。
- 不让 Agent 直接获得任意 Shell、数据库写权限或永久密钥；生产动作必须经过白名单、审批、短期凭证、验证和回滚。
- 不因开源产品功能丰富就同时引入多个重量级底座；先用接口和 PoC 验证，再按连接器、召回质量、权限和运维成本选择。

### 8.3 官方资料

- RAGFlow 文档：https://ragflow.io/docs/dev/
- Dify 知识库创建：https://docs.dify.ai/en/cloud/use-dify/knowledge/create-knowledge/readme
- Dify 分块与清洗：https://docs.dify.ai/en/cloud/use-dify/knowledge/create-knowledge/chunking-and-cleaning-text
- FastGPT 文档：https://doc.fastgpt.io/
- MaxKB 文档：https://maxkb.cn/docs/
- AnythingLLM 文档：https://docs.anythingllm.com/
