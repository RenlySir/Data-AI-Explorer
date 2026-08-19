# 开源项目引入决策

版本：v1.0

评审日期：2026-08-20

适用范围：Data AI Explorer 当前 React/Vite + FastAPI 可运行基线，以及后续 Java/Spring Boot 企业控制面

## 1. 结论

本项目不直接 Fork 多套脚手架，也不因功能相似就复制社区示例代码。开源项目必须经过“身份可确认、许可证允许、仍在维护、与当前技术栈兼容、能够被测试和升级”五项准入检查。当前优先采用官方项目和标准协议，社区示例只学习设计，不进入生产依赖。

本轮实际引入 [Microsoft Playwright](https://github.com/microsoft/playwright) 的官方测试包，建立桌面和移动端 Chromium E2E 门禁。Ant Design Pro、Temporal、Spring Security、OpenTelemetry 和 TiDB 生态按下面的边界分批引入。

## 2. 选型决策

| 能力 | 候选项目 | 决策 | 原因与落地边界 |
|---|---|---|---|
| 前端中后台 | [Ant Design Pro](https://github.com/ant-design/ant-design-pro) | 参考，暂不替换 | MIT、活跃且基于 React 19；但当前产品已有可运行 Vite 页面，整体替换会同时改写路由、样式和状态。先学习布局、权限路由和表单模式，后续以 `@ant-design/pro-components` 做页面级 PoC。 |
| 前端模板 | `react-antd-pro` | 阻止引入 | 名称无法唯一对应用户描述的仓库；未给出 URL 前不能确认许可证、维护者和供应链。 |
| Redux 脚手架 | [react-redux-boilerplate](https://github.com/flexdinesh/react-redux-boilerplate) | 拒绝 | 仓库已归档且多年未维护；当前状态规模也不需要额外 Redux。服务端状态后续优先评估 TanStack Query。 |
| DDD/Clean Architecture | `developer-kit/clean-architecture` | 参考原则，阻止复制 | 无法按名称确认唯一仓库。Java 控制面启动时以架构测试约束 `api -> application -> domain <- infrastructure`，不复制来源不明模板。 |
| 长流程编排 | `temporal-boot` | 拒绝作为基线 | 检索到的社区仓库缺少明确许可证且采用信号弱。Java 阶段使用 [Temporal Java SDK](https://github.com/temporalio/sdk-java) 和官方文档，自行实现 Query/AIOps Workflow 与 Activity。 |
| Saga 示例 | `temporal-event-driven-saga` | 仅学习概念 | 不能替代本项目的审批、幂等和补偿设计；不复制无明确许可证的示例。生产实现使用 Temporal 官方 SDK，Kafka 事件继续保留业务幂等键。 |
| E2E | 社区 `playwright-e2e-framework` | 用官方 Playwright 替代，已落地 | 社区候选缺少明确许可证；官方 Playwright 为 Apache-2.0。本轮已实现 Page Object、桌面/移动端项目、失败 Trace/截图/视频和 CI 报告。 |
| 可观测标准 | [OpenTelemetry](https://github.com/open-telemetry) | P1 采用 | 作为 Metrics/Logs/Traces 的统一语义和导出标准；当前手写 `/metrics` 保留，下一步接入 FastAPI/HTTPX 自动埋点和 OTLP Collector。 |
| APM 后端 | [Apache SkyWalking](https://github.com/apache/skywalking) | 可选适配 | Apache-2.0。与 Tempo/Jaeger 二选一验证，不在同一环境重复建设全套链路后端。 |
| 零侵入观测 | [Coroot](https://github.com/coroot/coroot) | 可选 PoC | Apache-2.0。仅在具备 eBPF/Kubernetes 条件的测试集群评估，不能替代应用业务指标和审计。 |
| Java 认证 | `SpringSecurityAuthentication` | 拒绝作为基线 | 名称对应多个低维护、零星社区仓库。Java 控制面使用 Spring Security 官方能力和官方 samples，自行实现 OIDC/JWT/RBAC。当前 FastAPI 演示登录不应被描述为生产认证。 |
| 平台数据库 | [TiDB](https://github.com/pingcap/tidb) | 已采用 | 平台权威关系数据统一 TiDB；外部 MySQL 仅作为用户数据源。生产启用 TiKV/PD/TiFlash，Compose `mocktikv` 只用于开发演示。 |
| CDC/迁移 | [TiFlow](https://github.com/pingcap/tiflow) | 按职责采用 | TiCDC 捕获数据库事实变更；DM 只用于 MySQL/MariaDB 到 TiDB，不能声称支持 PostgreSQL 源。PostgreSQL 迁移使用 ETL/CDC 适配链路并单独校验。 |
| TiDB 导入/备份 | TiDB Lightning / BR | 按官方发行物采用 | 使用目标 TiDB 版本随附工具和官方文档，不引用已经归档、迁移过的旧独立仓库作为依赖来源。 |
| K8s TiDB | [TiDB Operator](https://github.com/pingcap/tidb-operator) | P2 采用 | Kubernetes 生产部署使用 Operator；本地和三节点演示仍使用 Compose/systemd，避免为了工具统一改变部署边界。 |
| CI/CD | GitHub Actions | 已采用 | 已执行前端静态门禁、后端测试和 Playwright E2E；镜像扫描、SBOM、签名和部署审批后续补齐。 |

## 3. 当前代码落地

```text
apps/web/e2e/
├── core-journeys.spec.ts       # 登录、模型引导、数据源、ChatBI
└── pages/
    ├── app-shell.ts            # 侧栏层级与页面入口
    └── login-page.ts           # 登录 Page Object

apps/web/playwright.config.ts   # 双视口、独立测试端口、失败证据
.github/workflows/ci.yml        # 构建和后端测试通过后执行 E2E
```

E2E 使用独立端口 `15173/18182` 启动前后端，避免污染开发服务。CI 失败时保存 HTML 报告；Trace、截图和视频只在失败时保留。测试没有绕过登录 API，验证真实会话 ID、首次模型接入引导、侧栏点击路径和 ChatBI 只读门禁。

## 4. 分阶段引入计划

### P0：当前基线

1. 保持 React 19 + Vite，不做 Ant Design Pro 整体换壳。
2. Playwright 覆盖登录、模型接入、数据源、ChatBI、知识库、SQL 优化核心旅程。
3. 建立依赖锁文件、许可证清单、漏洞扫描和 PR 门禁。
4. 生产认证未完成前，演示登录只允许内网环境，不开放公网。

### P1：企业控制面

1. Java/Spring Boot 模块立项后引入 Spring Security 官方栈和 Temporal Java SDK。
2. 用架构测试保证 DDD 依赖方向，用 Testcontainers 验证 TiDB、Redis、Kafka 集成。
3. 接入 OpenTelemetry Collector；Trace 后端在 Tempo、Jaeger、SkyWalking 中只选一套主方案。
4. 部署 TiCDC 前先定义事件契约：领域事件继续由 Outbox 表达，TiCDC 只传播数据库事实变更。

### P2：生产交付

1. TiDB Operator + Helm 完成安装、扩缩容、升级和回滚演练。
2. BR 备份恢复、TiCDC 位点恢复、DM 迁移和 `sync-diff-inspector` 一致性形成自动化验收。
3. GitHub Actions 增加 SBOM、镜像漏洞扫描、签名、环境审批和离线制品发布。
4. 在 Kubernetes 测试集群评估 Coroot 或 SkyWalking，未达到故障定位收益前不增加生产组件。

## 5. 开源准入门禁

每个新增开源依赖必须在 PR 中记录以下内容：

1. 精确仓库 URL、包坐标、固定版本和许可证；名称相似不能视为同一项目。
2. 最近维护时间、发布节奏、安全公告渠道和可替代方案。
3. 只通过包管理器或官方发行物引入，不直接复制许可证不明的代码。
4. 生成 SBOM，执行依赖漏洞和 Secret 扫描；高危漏洞未豁免不得发布。
5. 提供退出方案：数据可导出、配置可迁移、接口有适配层，避免核心领域被单一项目 API 锁死。

## 6. TiDB 专项纠偏

- DM 的源端是 MySQL/MariaDB 生态，不是 PostgreSQL 通用迁移工具。
- TiCDC 输出表级变更事实，不能替代带审批、权限和业务语义的领域 Outbox。
- TiDB Lightning、BR、TiCDC、DM 必须与目标 TiDB 版本配套验证，不能只凭 GitHub `master` 分支设计生产流程。
- TiFlash、资源组和分区并非默认全开；必须由真实 SQL、容量和恢复演练决定。
