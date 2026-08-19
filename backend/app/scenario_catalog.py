from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


ScenarioStatus = Literal["ready", "running", "waiting_approval", "completed", "failed"]
StepStatus = Literal["queued", "running", "waiting_approval", "completed", "skipped"]


class ScenarioStep(BaseModel):
    id: str
    title: str
    role: str
    description: str
    action: str
    risk: Literal["low", "medium", "high"] = "low"
    status: StepStatus = "queued"
    evidence: list[str] = Field(default_factory=list)


class ScenarioTemplate(BaseModel):
    id: str
    name: str
    category: str
    summary: str
    value: str
    agents: list[str]
    triggers: list[str]
    integrations: list[str]
    approval_policy: str
    metrics: list[str]
    steps: list[ScenarioStep]
    status: ScenarioStatus = "ready"


class ScenarioRunCreate(BaseModel):
    objective: str = Field(min_length=3, max_length=2000)
    context: str = Field(default="", max_length=5000)


class ScenarioRun(BaseModel):
    run_id: str
    scenario_id: str
    scenario_name: str
    objective: str
    context: str
    status: ScenarioStatus
    created_at: str
    updated_at: str
    current_step_id: str | None = None
    steps: list[ScenarioStep]
    approvals_required: int = 0
    approvals_granted: int = 0
    audit: list[str] = Field(default_factory=list)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def step(step_id: str, title: str, role: str, description: str, action: str, risk: Literal["low", "medium", "high"] = "low") -> ScenarioStep:
    return ScenarioStep(id=step_id, title=title, role=role, description=description, action=action, risk=risk)


def build_catalog() -> list[ScenarioTemplate]:
    return [
        ScenarioTemplate(id="batch-guard", name="夜间跑批值守与自动恢复", category="AIOps 运维", summary="检查失败、超时和执行异常的批任务，分析日志并按 Runbook 重跑和校验。", value="替代夜间人工盯盘", agents=["值守 Agent", "日志分析 Agent", "数据校验 Agent"], triggers=["每天 01:00 定时", "手动启动"], integrations=["Airflow / DolphinScheduler / cron", "OpenSearch", "Great Expectations / Soda"], approval_policy="瞬时网络或资源错误最多自动重跑一次；补数、覆盖数据和代码问题必须审批。", metrics=["失败任务数", "自动恢复率", "数据校验通过率", "人工介入次数"], steps=[step("detect", "发现异常任务", "值守 Agent", "拉取调度平台失败、超时和耗时异常任务。", "读取调度 API", "low"), step("investigate", "分类失败原因", "日志分析 Agent", "按网络、资源、数据、权限和代码分类并附证据。", "查询日志与最近变更", "low"), step("recover", "执行重跑或生成处置", "值守 Agent", "满足策略时重跑一次，否则生成人工处置任务。", "调用白名单 Runbook", "medium"), step("validate", "验证数据完整性", "数据校验 Agent", "核对行数、分区、金额和上下游完整性。", "执行质量规则", "low")]),
        ScenarioTemplate(id="incident-warroom", name="生产故障虚拟作战室", category="AIOps 运维", summary="一个事故一个根任务，指挥 Agent 并行调度观测、数据库、平台和业务影响分析。", value="缩短 MTTR，统一事故结论", agents=["事件指挥 Agent", "可观测性 Agent", "数据库 DBA Agent", "平台 SRE Agent", "业务影响 Agent"], triggers=["Prometheus / Alertmanager 告警", "人工创建事故"], integrations=["Prometheus", "Loki", "Jaeger / Tempo", "TiDB", "Kubernetes"], approval_policy="重启、流量切换和数据修复需要人工审批；查询和证据采集默认只读。", metrics=["MTTD", "MTTR", "根因确认耗时", "止损成功率"], steps=[step("triage", "建立事故根任务", "事件指挥 Agent", "确认影响范围、严重级别和责任人。", "创建事件时间线", "low"), step("observe", "并行采集证据", "可观测性 Agent", "查询指标、日志、链路和最近变更。", "执行只读查询", "low"), step("diagnose", "专业分析与止损方案", "DBA / SRE / 业务 Agent", "形成根因候选、业务影响和止损动作。", "生成行动建议", "medium"), step("approve", "执行高风险处置", "事件指挥 Agent", "将重启、切流或数据修复提交审批。", "等待人工审批", "high"), step("verify", "恢复验证与复盘", "事件指挥 Agent", "对照 SLO 验证恢复并沉淀复盘。", "核对指标与业务结果", "low")]),
        ScenarioTemplate(id="script-repair", name="脚本异常自动修复闭环", category="研发交付", summary="从日志诊断到 Git 分支补丁、隔离测试、Review、审批发布和补跑。", value="从报错通知升级为补丁与验证结果", agents=["排障 Agent", "开发 Agent", "测试 Agent", "审核 Agent"], triggers=["CI 失败", "批任务脚本失败", "人工启动"], integrations=["GitLab / Gitea", "Docker", "pytest / ShellCheck", "Rundeck"], approval_policy="禁止覆盖生产脚本；必须分支、测试、Review 和人工批准后发布。", metrics=["修复成功率", "测试通过率", "平均修复时长", "回滚次数"], steps=[step("diagnose", "提取错误与复现条件", "排障 Agent", "读取日志、定位脚本和依赖。", "生成诊断证据", "low"), step("patch", "创建 Git 分支并修改", "开发 Agent", "在隔离工作区生成最小补丁。", "提交分支和差异", "medium"), step("test", "隔离环境回放", "测试 Agent", "运行静态检查、单测和容器回放。", "执行测试流水线", "low"), step("review", "审核副作用", "审核 Agent", "检查差异、权限、数据覆盖和回滚方案。", "生成 Review 报告", "high"), step("release", "审批发布与补跑", "发布负责人", "审批后发布并执行补跑、数据校验。", "调用发布 Runbook", "high")]),
        ScenarioTemplate(id="db-health", name="数据库每日健康巡检", category="数据与数据库", summary="每天检查慢 SQL、锁等待、延迟、连接数、容量、备份和统计信息。", value="DBA 只处理真正异常项", agents=["DBA Agent", "SQL 优化 Agent", "容量 Agent"], triggers=["每天 08:00 定时", "手动启动"], integrations=["TiDB Dashboard / PMM", "Prometheus", "SQL 优化模块"], approval_policy="只读检查和建议自动执行；DDL、Kill Session、主从切换必须审批。", metrics=["异常项数", "慢 SQL p95", "锁等待时长", "备份成功率"], steps=[step("check", "采集健康指标", "DBA Agent", "读取慢 SQL、锁、连接、延迟、容量、备份和统计信息。", "执行只读 SQL", "low"), step("optimize", "生成 SQL 优化建议", "SQL 优化 Agent", "分析高成本 SQL 并关联 TiDB 版本计划。", "调用 SQL 优化模块", "low"), step("report", "创建异常任务", "容量 Agent", "按阈值创建任务并汇总日报。", "生成日报与责任人", "low")]),
        ScenarioTemplate(id="release-review", name="发布前自动风险评审", category="研发交付", summary="并行审查代码差异、测试、依赖、安全、数据库变更和回滚脚本。", value="把发布清单变成并行执行", agents=["发布经理 Agent", "代码评审 Agent", "安全 Agent", "测试 Agent", "回滚 Agent"], triggers=["提交版本号", "创建 Release 任务"], integrations=["GitLab / Gitea", "Jenkins / Tekton", "SonarQube / Semgrep / Trivy", "Liquibase / Flyway"], approval_policy="P0 漏洞、破坏性 DDL、无回滚方案自动阻断发布。", metrics=["风险评分", "阻断项数", "评审耗时", "回滚覆盖率"], steps=[step("diff", "审查代码和依赖差异", "代码评审 Agent", "读取提交、依赖和配置变化。", "生成差异摘要", "low"), step("security", "安全扫描", "安全 Agent", "扫描漏洞、密钥、镜像和依赖。", "运行安全工具", "medium"), step("test", "验证测试与数据库兼容", "测试 Agent", "检查覆盖、回归和迁移脚本。", "运行 CI 证据", "low"), step("decision", "生成发布评分", "发布经理 Agent", "汇总阻断项、风险和回滚路径。", "提交审批材料", "high")]),
        ScenarioTemplate(id="release-watch", name="发布后智能观察窗", category="研发交付", summary="发布后持续观察错误率、延迟、资源和业务指标，达到阈值生成回滚建议。", value="减少发布后人工守候", agents=["监控 Agent", "日志 Agent", "业务指标 Agent"], triggers=["发布完成", "手动开启观察窗"], integrations=["Argo Rollouts / Flagger", "Prometheus", "Grafana", "OpenFeature"], approval_policy="只读观察自动运行；回滚可使用已审批 Runbook，否则转人工。", metrics=["错误率变化", "P95 变化", "业务转化变化", "回滚决策时长"], steps=[step("baseline", "记录发布前基线", "监控 Agent", "保存错误率、延迟、资源和业务指标基线。", "读取监控 API", "low"), step("observe", "按窗口持续观测", "日志 / 指标 Agent", "每 5-10 分钟比较发布前后指标。", "执行定时检查", "low"), step("decide", "输出关闭或回滚建议", "业务指标 Agent", "达到阈值则生成行动建议。", "提交回滚审批", "high")]),
        ScenarioTemplate(id="data-quality", name="数据质量异常调查", category="数据与数据库", summary="从质量规则失败追溯血缘、Schema、代码变更和业务事件，输出修复与补数方案。", value="把数据问题变成可追踪调查", agents=["数据质量 Agent", "血缘分析 Agent", "业务口径 Agent", "修复 Agent"], triggers=["质量规则失败", "用户报告数据异常"], integrations=["Great Expectations / Soda", "OpenMetadata / DataHub", "OpenLineage", "dbt", "DolphinScheduler"], approval_policy="查询和影响分析只读；修复 SQL、补数和覆盖数据必须审批。", metrics=["规则通过率", "影响表数量", "定位耗时", "修复回归通过率"], steps=[step("detect", "确认质量异常", "数据质量 Agent", "读取空值、重复、突增突降规则结果。", "定位失败规则", "low"), step("lineage", "追溯影响范围", "血缘分析 Agent", "查询上游表、任务和最近变更。", "构建影响图", "low"), step("repair", "生成修复与补数计划", "修复 Agent", "输出 SQL、补数范围和回滚方案。", "创建审批任务", "high"), step("verify", "复跑质量规则", "数据质量 Agent", "修复后重新检查并归档证据。", "运行质量规则", "low")]),
        ScenarioTemplate(id="smart-query-team", name="企业智能问数交付团队", category="数据分析", summary="理解口径、生成只读 SQL、执行、复核数量级并输出 ECharts 报表。", value="不只生成 SQL，还交叉验证答案", agents=["需求理解 Agent", "指标语义 Agent", "SQL Agent", "可视化 Agent", "验证 Agent"], triggers=["频道自然语言提问", "创建分析任务"], integrations=["TiDB MCP", "Semantic Registry", "ECharts", "SQL 优化模块"], approval_policy="只读查询默认自动；跨域数据、敏感字段和导出需要权限与审批。", metrics=["问数成功率", "SQL 一次通过率", "结果复核率", "响应时延"], steps=[step("understand", "识别问题与指标口径", "需求理解 / 指标语义 Agent", "匹配已发布指标和数据权限。", "构建分析上下文", "low"), step("query", "生成并执行只读 SQL", "SQL Agent", "调用 Text2SQL、AST 检查和 TiDB MCP。", "生成查询结果", "low"), step("verify", "复核结果数量级", "验证 Agent", "检查空结果、异常波动和口径证据。", "运行校验规则", "low"), step("visualize", "生成图表与报告", "可视化 Agent", "选择合适 ECharts 图表并附 SQL/证据。", "返回 BI 结果", "low")]),
        ScenarioTemplate(id="customer-diagnosis", name="客户工单自动诊断", category="客户支持", summary="同步工单、检索知识、查询授权环境日志并起草人工确认的回复。", value="降低一线支持升级率", agents=["工单分类 Agent", "知识检索 Agent", "环境诊断 Agent", "客户回复 Agent"], triggers=["新工单", "SLA 临近"], integrations=["Zammad / FreeScout", "OpenSearch", "Dify / RAGFlow", "Sentry"], approval_policy="只能读取客户明确授权的数据；外发回复必须人工确认。", metrics=["首响时长", "自动诊断率", "升级率", "回复采纳率"], steps=[step("classify", "分类与定级工单", "工单分类 Agent", "识别产品、版本、优先级和 SLA。", "更新工单字段", "low"), step("retrieve", "检索知识和历史案例", "知识检索 Agent", "匹配受控知识和相似问题。", "返回引用证据", "low"), step("diagnose", "检查授权环境", "环境诊断 Agent", "查询授权机器日志和健康状态。", "执行只读诊断", "medium"), step("reply", "生成回复草稿", "客户回复 Agent", "输出根因、步骤和升级条件。", "提交人工确认", "high")]),
        ScenarioTemplate(id="security-response", name="安全漏洞响应流水线", category="安全治理", summary="同步漏洞公告、匹配 SBOM 资产、测试补丁并分批推进修复。", value="从漏洞公告快速推进到可执行任务", agents=["漏洞情报 Agent", "资产定位 Agent", "修复 Agent", "验证 Agent"], triggers=["CVE 公告", "扫描发现高危漏洞"], integrations=["Trivy / Grype / Syft", "Dependency-Track", "Wazuh / TheHive", "Ansible / AWX"], approval_policy="互联网暴露且可利用漏洞升级 P0；生产补丁必须审批和分批。", metrics=["受影响资产数", "高危修复时长", "补丁成功率", "复扫通过率"], steps=[step("ingest", "同步漏洞情报", "漏洞情报 Agent", "读取 CVE、利用性和修复版本。", "更新漏洞任务", "low"), step("impact", "定位受影响资产", "资产定位 Agent", "匹配 SBOM、镜像和主机。", "生成资产清单", "low"), step("patch", "测试并分批修复", "修复 Agent", "在测试环境验证补丁和回滚。", "创建分批变更", "high"), step("verify", "复扫与关闭", "验证 Agent", "确认漏洞不再暴露并归档证据。", "运行安全扫描", "low")]),
        ScenarioTemplate(id="cloud-finops", name="云成本持续优化", category="成本治理", summary="扫描闲置资源、异常增长和存储浪费，持续跟踪节省金额与实际收益。", value="FinOps 从月报变成持续行动", agents=["成本 Agent", "资源 Agent", "架构 Agent", "财务解释 Agent"], triggers=["每周扫描", "成本异常告警"], integrations=["OpenCost / Kubecost", "Infracost", "Steampipe", "Cloud Custodian", "Terraform / OpenTofu"], approval_policy="测试环境可按策略关停；生产资源只生成评审任务。", metrics=["预计节省", "实际节省", "闲置资源数", "优化采纳率"], steps=[step("scan", "识别浪费与异常增长", "成本 / 资源 Agent", "扫描低利用率实例、存储和异常账单。", "读取成本 API", "low"), step("explain", "分析架构与业务影响", "架构 / 财务 Agent", "计算节省、风险和服务影响。", "生成优化说明", "low"), step("plan", "生成实施任务", "成本 Agent", "输出 Terraform 变更建议和负责人。", "提交评审任务", "medium"), step("track", "追踪实际收益", "财务解释 Agent", "比较实施前后成本和利用率。", "更新收益台账", "low")]),
        ScenarioTemplate(id="project-staff", name="项目数字参谋部", category="项目协作", summary="读取提交、CI、任务和协作进展，识别延期、阻塞、依赖冲突并生成日报周报。", value="管理者不再逐人追进度", agents=["项目经理 Agent", "研发 Agent", "测试 Agent", "文档 Agent", "风险 Agent"], triggers=["每日站会", "每周周报", "手动刷新"], integrations=["GitLab / Gitea", "OpenProject / Plane", "Jenkins", "MkDocs"], approval_policy="读取和汇报自动执行；催办和任务分派需遵循团队权限。", metrics=["按期完成率", "阻塞项数量", "无人负责项", "风险关闭时长"], steps=[step("collect", "汇总项目事实", "项目经理 Agent", "读取提交、CI、任务和决策记录。", "构建项目快照", "low"), step("risk", "识别阻塞和依赖", "风险 Agent", "发现延期、无人负责和跨团队依赖。", "生成风险清单", "low"), step("follow", "拆分任务与催办", "项目经理 Agent", "生成下一步、负责人和截止时间。", "创建任务草稿", "medium"), step("report", "生成日报与周报", "文档 Agent", "输出进展、风险、决策和待办。", "发布报告草稿", "low")]),
    ]


SCENARIO_TEMPLATES = build_catalog()
SCENARIO_BY_ID = {item.id: item for item in SCENARIO_TEMPLATES}
SCENARIO_RUNS: dict[str, ScenarioRun] = {}


def new_run(template: ScenarioTemplate, payload: ScenarioRunCreate) -> ScenarioRun:
    run_id = f"run-{uuid4().hex[:10]}"
    steps = [item.model_copy(deep=True) for item in template.steps]
    approvals = sum(item.risk == "high" for item in steps)
    now = now_iso()
    run = ScenarioRun(run_id=run_id, scenario_id=template.id, scenario_name=template.name, objective=payload.objective, context=payload.context, status="running", created_at=now, updated_at=now, current_step_id=steps[0].id if steps else None, steps=steps, approvals_required=approvals, audit=[f"{now} 创建场景运行实例", f"{now} 初始化 {len(steps)} 个 Agent 步骤"])
    if steps:
        steps[0].status = "running"
    return run
