# 企业 AI 落地平台前端开发设计方案

版本：v1.0
日期：2026-08-19
适用系统：Aegis AI Control Plane

依据：[产品设计方案](企业AI落地平台-产品设计方案.md)与[详细架构设计方案](企业AI落地平台-详细架构设计方案.md)。接口、状态机、部署和模型能力不得偏离架构基线；变更需记录 ADR。

## 1. 目标与范围

本文定义 Aegis Web 前端的工程架构、页面结构、组件边界、状态管理、接口协作、权限、安全、性能、测试和交付标准，可直接用于任务拆分和编码评审。

首期覆盖工作台、智能问数、AIOps、数据治理、智能指挥、任务审批和管理中心。桌面端为主，移动端仅支持告警查看、任务跟进和审批。

## 2. 技术基线

| 类别 | 选型 | 约束 |
|---|---|---|
| 框架 | React 19 + TypeScript 5 | 启用 strict，不使用隐式 any |
| 构建 | Vite | 环境变量只注入公开配置 |
| 路由 | React Router | 路由懒加载、错误边界 |
| 服务端状态 | TanStack Query | 统一缓存键和失效策略 |
| 本地状态 | Zustand | 只保存 UI、草稿和临时偏好 |
| UI | Ant Design + Design Tokens | 业务组件封装，禁止页面散落硬编码颜色 |
| 图表 | ECharts | 图表配置通过适配层生成 |
| 血缘 | React Flow | 大图虚拟化、分层加载 |
| 编辑器 | Monaco Editor | SQL/YAML 只展示允许功能 |
| 通信 | Fetch SDK + SSE | WebSocket 仅用于未来协同编辑 |
| 测试 | Vitest + Testing Library + Playwright | 关键流程必须 E2E |

支持 Chrome/Edge 最近两个大版本，最低宽度 1280px；1024～1279px 折叠证据栏；移动端采用独立简化布局。

## 3. 前端总体结构

```text
Browser
├─ AppShell：导航、工作区、通知、用户
├─ Route Modules：按业务领域懒加载
├─ Domain Components：问数、Incident、血缘、审批
├─ Shared Components：表格、状态、空态、错误、证据
├─ API SDK：由 OpenAPI 自动生成
├─ Query Cache：服务端状态
├─ UI Store：界面和草稿状态
└─ Telemetry：日志、性能、Trace Context
```

浏览器不直连模型、数据库、Kafka、对象存储或 Executor。下载文件使用服务端签发的短期 URL；SSE Token 通过同源 Cookie 或短期票据传递，禁止放在查询参数日志中。

## 4. 工程目录

```text
apps/web/src/
├── app/                 # bootstrap、router、providers、layout
├── routes/              # 路由入口与loader
├── features/
│   ├── workbench/
│   ├── query-copilot/
│   ├── aiops/
│   ├── governance/
│   ├── command/
│   ├── task-approval/
│   └── admin/
├── entities/            # User、Asset、Incident等实体展示模型
├── shared/
│   ├── api/             # generated SDK、interceptors、query keys
│   ├── auth/            # Session、Permission、RouteGuard
│   ├── components/      # 通用组件
│   ├── hooks/
│   ├── lib/
│   ├── styles/
│   └── telemetry/
├── stores/              # 少量跨域 UI 状态
└── test/
```

依赖方向：`app/routes → features → entities → shared`。feature 之间不得引用内部实现；跨域交互通过公开 index、URL 或服务端状态完成。

## 5. 路由与页面

| 路由 | 页面 | 主要区域 |
|---|---|---|
| `/workbench` | 工作台 | 待办、P0/P1 Incident、关键指标、最近会话 |
| `/query` | 问数会话列表 | 会话、模板、收藏 |
| `/query/:id` | 问数工作区 | 会话、结果、图表、SQL、证据 |
| `/governance/assets` | 数据目录 | 筛选树、资产表格、批量治理 |
| `/governance/assets/:urn` | 资产详情 | Schema、血缘、SQL、质量、负责人 |
| `/governance/metrics` | 指标目录 | 指标版本、口径、维度、审批 |
| `/aiops/incidents` | 事件中心 | 列表、状态、等级、负责人 |
| `/aiops/incidents/:id` | Incident 详情 | 时间线、证据、RCA、Runbook、执行 |
| `/command/rooms/:id` | 智能作战室 | 根任务、Agent、决策、证据流 |
| `/tasks` | 任务中心 | 我的任务、团队任务、依赖 |
| `/approvals` | 审批中心 | 待我审批、已处理、风险信息 |
| `/admin/*` | 管理中心 | 数据源、模型、连接器、权限、审计 |

路由元信息包含 title、breadcrumb、requiredPermissions、environmentPolicy。无权访问返回 403 页面，不通过隐藏菜单假装安全。

## 6. AppShell 与通用交互

AppShell 包含 64px 顶栏、可收起侧栏、内容区和全局抽屉。顶栏提供工作区/环境切换、全局搜索、通知和用户菜单。生产环境使用持续可见的红色环境标识，任何执行动作再次显示环境和目标。

通用状态必须完整实现：首次加载 Skeleton、局部刷新、空数据、无权限、连接断开、超时、部分成功、错误重试和只读降级。页面不能只用 Toast 表达关键失败；操作结果需保留在当前上下文。

### 6.1 登录后首屏规范

首屏按以下优先级渲染：工作区/环境确认 → 待处理任务 → 高优先级事件 → 关注指标 → 最近工作 → 快捷入口。无待办时展示 3 个明确动作：`开始第一个问数`、`查看数据目录`、`配置我的关注`。

每个工作台卡片必须包含：标题、对象类型、状态、影响/收益、负责人、更新时间和唯一主操作。卡片点击进入详情，主操作直接进入下一步；不使用只有装饰信息而没有动作的卡片。

### 6.2 页面操作区规范

详情页顶部固定对象头：返回、对象名称、状态、环境、负责人、更新时间、关联对象。底部固定操作栏仅放当前状态允许的动作；危险动作使用红色并显示目标、风险和回滚。页面滚动时对象头和操作栏保持可见。

所有异步动作采用统一 `OperationProgress`：当前阶段、已耗时、取消、重试、查看日志。失败状态提供“重试”“修改参数”“转人工”“返回上一步”之一，不能只显示错误文本。

## 7. 智能问数前端设计

### 7.1 页面组成

三栏布局：左栏会话；中栏消息与结果；右栏证据。中栏消息单元由 Question、Plan、Clarification、QueryProgress、Result、Conclusion、Feedback 组成。

结果区固定 Tabs：`结论`、`图表`、`数据`、`SQL`、`执行计划`。证据栏展示指标版本、数据源、表/字段、时间范围、权限检查、验证项、模型和审计 ID。

### 7.2 状态与流式协议

提交问题后：

1. `POST /api/v1/query/conversations/{id}/messages` 返回 `202 operation_id`。
2. 订阅 `/api/v1/operations/{id}/events`。
3. 按 `PLANNING/VALIDATING/EXECUTING/VERIFYING/COMPLETED` 更新固定进度区。
4. 收到 `NEED_CLARIFICATION` 显示结构化选项，不继续执行。
5. SSE 中断后按 last-event-id 重连；最终以 GET 状态为准。

禁止把 Token 流直接拼为 HTML；Markdown 使用白名单渲染并关闭原始 HTML。结果表格默认最多展示 500 行，大结果走分页或导出。

### 7.3 图表和反馈

服务端返回 ChartSpec，前端适配为 ECharts Option。字段、单位、排序和数据集由服务端提供，前端不得自行改变指标含义。支持正误反馈、错误类型、口径纠正建议；反馈提交后显示处理状态。

### 7.4 页面点击脚本

| 页面状态 | 用户看到的主操作 | 点击后 |
|---|---|---|
| 空会话 | 开始分析 | 创建问题并进入规划 |
| 需要澄清 | 确认并继续 | 提交时间/维度条件 |
| 执行中 | 查看进度 | 展开阶段日志，可取消 |
| 有结果 | 转为报表/转为任务 | 创建报表或任务并跳转 |
| 被拒绝 | 修改问题 | 回到输入框并保留拒绝原因 |

## 8. AIOps 前端设计

Incident 列表支持状态、等级、服务、环境、负责人和时间筛选，查询条件同步 URL。详情页采用：顶部影响摘要；左侧时间线；中部指标/日志/链路证据；右侧 RCA 与 Runbook；底部执行日志。

RCA 候选必须同时显示置信度、支持证据和反证。Runbook 卡片显示版本、风险、目标环境、参数、前置条件、验证与回滚。执行按钮按风险变为“执行”“申请审批”或“禁止自动执行”。

执行过程使用 Stepper 呈现 `DRY_RUN → APPROVAL → EXECUTION → VERIFY → ROLLBACK`。高风险确认弹窗必须要求用户复核环境、对象、影响和回滚，不使用仅有“确定”的通用弹窗。

事件页面主按钮由状态机驱动，前端只展示服务端返回的 allowedActions。执行、审批和关闭按钮在接口返回 409 后刷新状态，不乐观更新为成功。

## 9. 数据治理前端设计

资产目录使用服务端筛选和游标分页。资产详情包含概要、Schema、血缘、关联 SQL、质量和治理记录。

血缘图采用按需扩展：首次只加载上下游一跳，用户展开节点后请求新边；500 节点以上提示缩小范围。提供方向、深度、资产类型、置信度筛选和影响分析模式。画布节点选择不会改变 URL 时，状态放本地；资产和深度放 URL 以便分享。

指标编辑采用草稿、校验、提交审批、发布四阶段。编辑器离开前提示未保存内容，版本发布后不可原位修改。

## 10. 智能指挥、任务与审批

作战室布局为里程碑主线、子任务看板、Agent 状态栏和决策面板。Agent 调用必须显示运行中、等待工具、等待审批、完成、失败、人工接管，不用拟人化动画替代真实状态。

审批页面固定展示请求快照、发起人、风险、证据、参数差异、目标环境、回滚和过期时间。批准/拒绝均要求填写意见；高风险批准支持 MFA/二次认证。

作战室首次进入默认聚焦“问题与影响”面板，Agent 列表折叠为辅助信息；用户点击“查看证据”或“查看分工”后展开。决策卡片使用单选候选方案，选中后显示影响、风险、回滚和审批链，避免用户在多个 Agent 消息中拼接结论。

## 11. 管理中心

数据源向导：类型 → 网络 → 凭证引用 → 连通性测试 → 权限检测 → 采集范围 → 调度。页面不接收或回显已保存密钥。

模型向导：Provider → Endpoint → 凭证 → 能力探测 → 评测 → 路由策略 → 发布。明确标识 `local-only`、可处理的数据等级、上下文和工具调用能力。

审计页面只读，支持 actor、资源、动作、策略结果、时间和 trace_id 检索；导出是受审计操作。

## 12. 状态管理规范

- TanStack Query：用户、资产、Incident、任务、审批等服务端权威状态。
- Zustand：侧栏、主题、草稿、临时筛选和未提交画布状态。
- URL：可分享的筛选、分页游标前置条件、选中 Tab 和时间范围。
- React local state：组件内部交互。

Query Key 示例：`['assets', workspaceId, filters]`、`['incident', tenantId, id]`。Mutation 成功后精确失效相关键，禁止清空全部缓存。跨租户/工作区切换必须清除缓存和 SSE 连接。

## 13. API SDK 与错误处理

`packages/api-contract/openapi.yaml` 生成 TypeScript SDK，CI 检查生成物未漂移。Request interceptor 注入 traceparent、workspace 和 locale；401 触发一次静默刷新，失败后回登录；403 不重试；409 显示版本冲突；429 使用 Retry-After；5xx 提供 request_id。

错误对象统一解析 RFC 9457：`type/title/status/detail/instance/errorCode/fieldErrors/traceId`。用户文案与技术细节分离，技术详情放可复制的诊断面板。

## 14. 权限与前端安全

- 使用 OIDC Authorization Code + PKCE；优先 HttpOnly、Secure、SameSite Cookie。
- CSP 禁止任意脚本；禁用 `dangerouslySetInnerHTML`，富文本严格消毒。
- 下载 URL 短期有效；前端日志不记录 Prompt、SQL 结果、Token、Secret。
- `PermissionGate` 只改善体验，服务端始终重新鉴权。
- 生产执行页面空闲超时后要求重新认证。
- 防止 CSV Formula Injection，导出由服务端转义。

## 15. 可访问性与国际化

目标 WCAG 2.1 AA：键盘可达、焦点可见、状态不只依赖颜色、图表有表格替代、动态更新使用 aria-live。文本走 i18n key，首期简体中文，预留英文；时间按用户时区展示但 API 使用 UTC ISO-8601。

## 16. 性能设计

- 首屏 JS gzip ≤350KB（不含按需图表/Monaco）；路由级拆包。
- LCP P75 <2.5s，INP P75 <200ms，CLS <0.1。
- Monaco、React Flow、ECharts 动态加载；表格和消息列表虚拟化。
- 搜索输入 300ms debounce；请求可取消；后台页面降低轮询频率。
- SSE 连接按页面建立，离开即释放；同一 operation 只允许一个连接实例。

## 17. 测试策略

| 层级 | 内容 | 门槛 |
|---|---|---|
| 单元 | formatter、权限、状态机、ChartSpec 适配 | 核心逻辑覆盖 ≥80% |
| 组件 | 表单、证据、审批、错误状态 | 行为与可访问性 |
| 契约 | OpenAPI Mock、错误模型、SSE 事件 | 每次 CI |
| E2E | 登录、问数、血缘、Incident、审批 | 主链路 100% |
| 视觉 | 核心页面桌面/平板截图 | 无溢出、遮挡和布局跳变 |
| 安全 | XSS、越权展示、敏感日志 | 阻断发布 |

Playwright 最少覆盖：问题澄清、SQL 被拒绝、大结果导出、SSE 重连、Incident 审批执行、Runbook 失效、跨工作区缓存隔离。

## 18. 前端交付与任务拆分

| Sprint | 交付 |
|---|---|
| 1 | 工程骨架、AppShell、OIDC、SDK、Design Tokens |
| 2 | 工作台、数据源/模型管理基础页、资产目录 |
| 3 | 问数会话、SSE、结果/SQL/证据、反馈 |
| 4 | Incident 列表详情、RCA、Runbook 和执行流 |
| 5 | 血缘图、指标版本、任务审批、作战室 |
| 6 | 响应式、可访问性、性能、安全和 E2E 收口 |

## 19. 前端验收标准

核心页面与产品原型一致；所有权限、加载、空态、错误和部分成功状态可用；主链路 E2E 全通过；SSE 可断线恢复；跨租户无缓存泄漏；生产高风险操作完成二次确认；关键性能和可访问性达到本方案指标。

补充体验验收：新用户登录后无需阅读说明即可找到首个任务；工作台、问数、Incident、资产和审批页面均有可执行的主按钮；每条主流程可通过点击完成，不要求用户手工拼接 ID、复制 SQL 或跳转外部系统；页面截图在 1280px、1440px 和平板宽度下无重叠、截断或操作栏丢失。
