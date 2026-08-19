from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


DeliveryState = Literal["available", "demo", "planned"]
TargetPage = Literal[
    "workbench",
    "query",
    "knowledge",
    "assets",
    "catalog",
    "incidents",
    "sql-optimizer",
    "scenarios",
    "models",
    "agents",
    "datasources",
]


class ProductFeature(BaseModel):
    id: str
    name: str
    summary: str
    roles: list[str]
    delivery_state: DeliveryState
    target_page: TargetPage | None = None
    action_label: str
    inputs: list[str]
    outputs: list[str]
    guardrails: list[str]
    scenario_ids: list[str] = Field(default_factory=list)
    api_refs: list[str] = Field(default_factory=list)


class ProductModule(BaseModel):
    id: str
    name: str
    domain: Literal["data", "operations", "collaboration", "platform"]
    summary: str
    owner_role: str
    features: list[ProductFeature]


def feature(
    feature_id: str,
    name: str,
    summary: str,
    roles: list[str],
    delivery_state: DeliveryState,
    target_page: TargetPage | None,
    action_label: str,
    inputs: list[str],
    outputs: list[str],
    guardrails: list[str],
    scenario_ids: list[str] | None = None,
    api_refs: list[str] | None = None,
) -> ProductFeature:
    return ProductFeature(
        id=feature_id,
        name=name,
        summary=summary,
        roles=roles,
        delivery_state=delivery_state,
        target_page=target_page,
        action_label=action_label,
        inputs=inputs,
        outputs=outputs,
        guardrails=guardrails,
        scenario_ids=scenario_ids or [],
        api_refs=api_refs or [],
    )


READ_ONLY = ["默认只读", "记录操作审计"]
APPROVAL = ["高风险动作必须审批", "执行前检查并提供回滚", "记录操作审计"]


PRODUCT_MODULES = [
    ProductModule(
        id="smart-query",
        name="智能问数",
        domain="data",
        summary="从数据结构理解、自然语言问题到安全 SQL、复核结果和 BI 报表的完整分析链路。",
        owner_role="数据产品负责人",
        features=[
            feature("query-chatbi", "ChatBI 对话分析", "选择数据源后将自然语言转换为 SQL，执行并自动选择 BI 图表。", ["业务用户", "数据分析师"], "available", "query", "开始 ChatBI", ["数据源", "自然语言问题"], ["只读 SQL", "查询结果", "ECharts 图表"], ["SQL 只读拦截", "限制返回行数", "保留执行证据"], ["smart-query-team"], ["POST /api/v1/chatbi/query"]),
            feature("query-dashboard", "认可报表大屏", "将用户核验认可的 ChatBI 结果沉淀为可复用经营大屏。", ["业务用户", "管理者"], "available", "query", "查看大屏", ["已完成分析", "认可动作"], ["大屏报表", "来源与认可人"], ["仅认可结果可加入", "保留原问题和数据源", "支持移除"], ["smart-query-team"], ["GET/POST /api/v1/chatbi/reports"]),
            feature("query-tidb-mcp", "TiDB MCP 元数据连接", "采集 Schema、表、字段、Comment 与关系。", ["数据工程师", "DBA"], "demo", "catalog", "采集结构", ["MCP Endpoint", "只读凭证引用"], ["元数据目录", "关系边"], READ_ONLY, ["smart-query-team"], ["POST /api/v1/tidb/mcp/introspect"]),
            feature("query-semantic", "指标与语义匹配", "把业务术语映射到指标口径、维度和可用资产。", ["业务用户", "数据分析师"], "demo", "query", "开始问数", ["自然语言问题", "工作区"], ["指标口径", "候选数据资产"], ["应用数据权限", "歧义时要求澄清"], ["smart-query-team"]),
            feature("query-text2sql", "自然语言转 SQL", "生成受语义模型约束的 TiDB 只读 SQL。", ["业务用户", "数据分析师"], "available", "query", "生成并执行", ["问题", "Schema", "指标口径"], ["只读 SQL", "查询参数"], ["AST 拦截写操作", "限制扫描量与超时", "参数化执行"], ["smart-query-team"], ["POST /api/v1/query/conversations"]),
            feature("query-validation", "结果复核与证据", "校验空结果、数量级、时间范围和口径并保留证据。", ["数据分析师", "审计员"], "demo", "query", "核验结果", ["SQL 结果", "指标规则"], ["复核结论", "SQL 与资产证据"], ["不以模型自报置信度代替校验", "保留审计 ID"], ["smart-query-team"]),
            feature("query-bi", "BI 图表与分析结果", "按时间、比较、分布或占比选择 ECharts 图表并展示数据。", ["业务用户", "管理者"], "available", "query", "查看报表", ["查询结果", "分析意图"], ["图表", "数据表", "业务结论"], ["图表可回到原始数据", "脱敏后导出"], ["smart-query-team"]),
            feature("query-file", "CSV/Parquet 数据集分析", "上传文件后登记数据集并通过问题生成聚合结果。", ["数据分析师", "数据工程师"], "demo", "assets", "上传并分析", ["CSV/Parquet", "分析问题"], ["数据集", "SQL", "图表"], ["限制文件类型与大小", "隔离临时文件"], ["smart-query-team"], ["POST /api/v1/datasets/upload", "POST /api/v1/datasets/analyze"]),
            feature("query-directory", "受控目录数据分析", "扫描部署端白名单目录并登记可分析文件。", ["数据工程师", "管理员"], "demo", "assets", "扫描目录", ["允许目录"], ["数据集清单", "字段摘要"], ["禁止目录越界和符号链接", "只读挂载"], ["smart-query-team"], ["POST /api/v1/datasets/local-directory"]),
        ],
    ),
    ProductModule(
        id="knowledge",
        name="企业知识库",
        domain="data",
        summary="将制度、手册、案例和项目资料转为可检索、可引用、可评测的企业上下文。",
        owner_role="知识管理员",
        features=[
            feature("knowledge-space", "知识空间管理", "按工作区和用途建立隔离的知识空间。", ["知识管理员"], "available", "knowledge", "管理知识库", ["名称", "用途", "范围"], ["知识库", "策略标识"], ["租户与工作区隔离", "权限先于召回"], api_refs=["GET/POST /api/v1/knowledge-bases"]),
            feature("knowledge-ingest", "文本、文件与目录入库", "统一导入文本、文档和本机允许目录。", ["知识管理员", "数据工程师"], "available", "knowledge", "添加资料", ["文本/文件/目录", "标题与标签"], ["文档", "索引状态"], ["扩展名与大小限制", "内容视为不可信输入"], ["customer-diagnosis"], ["POST /api/v1/knowledge-bases/{id}/documents"]),
            feature("knowledge-chunks", "解析与 Chunk 检查", "查看文档切分片段，发现标题、表格或代码被错误切分。", ["知识管理员", "数据工程师"], "available", "knowledge", "检查分块", ["文档"], ["Chunk 文本", "位置与检索词数"], ["原文权限继承到 Chunk"], api_refs=["GET /api/v1/knowledge-bases/{id}/documents/{doc}/chunks"]),
            feature("knowledge-retrieval", "检索测试与历史", "对单个知识库测试召回并保留最近查询。", ["知识管理员", "AI 工程师"], "available", "knowledge", "运行检索测试", ["测试问题", "Top K"], ["命中片段", "相关度", "查询历史"], ["召回前执行 ACL", "无证据时拒答"], api_refs=["GET /api/v1/knowledge-bases/{id}/queries"]),
            feature("knowledge-qa", "有引用问答", "基于受控片段回答并返回来源与相关度。", ["业务用户", "SRE", "客户支持"], "available", "knowledge", "检索并回答", ["问题", "知识库"], ["回答", "引用", "查询 ID"], ["Citation Coverage", "禁止文档指令覆盖系统策略"], ["customer-diagnosis"], ["POST /api/v1/knowledge-bases/{id}/query"]),
            feature("knowledge-feedback", "回答反馈与评测", "记录有帮助/需改进反馈并沉淀评测样本。", ["业务用户", "AI 工程师"], "available", "knowledge", "提交反馈", ["查询 ID", "反馈"], ["反馈记录", "评测候选"], ["反馈不可改变原审计记录"], api_refs=["POST /api/v1/knowledge-bases/{id}/queries/{query}/feedback"]),
            feature("knowledge-connectors", "Wiki/Git/网盘连接器", "按计划增量同步企业内容并保留来源版本。", ["知识管理员", "管理员"], "planned", None, "待接入", ["连接器", "同步范围", "调度"], ["版本化文档", "同步报告"], ["最小权限", "增量同步幂等", "删除传播策略"]),
        ],
    ),
    ProductModule(
        id="data-governance",
        name="数据资产与治理",
        domain="data",
        summary="围绕资产对象统一管理结构、关系、SQL、质量、口径、责任人和影响范围。",
        owner_role="数据治理负责人",
        features=[
            feature("governance-catalog", "数据资产目录", "按名称、标签、负责人和业务域检索数据资产。", ["业务用户", "数据工程师", "DBA"], "available", "assets", "浏览资产", ["搜索条件"], ["资产列表", "质量与负责人"], READ_ONLY, api_refs=["GET /api/v1/assets"]),
            feature("governance-schema", "Schema 与字段 Comment", "查看 TiDB Schema、表、字段类型和业务注释。", ["数据工程师", "DBA"], "available", "catalog", "查看结构", ["数据源", "Schema"], ["表结构", "字段 Comment"], READ_ONLY, ["data-quality"]),
            feature("governance-lineage", "表/字段关系与血缘", "选择数据源采集全量 Schema、字段 Comment 与外键，并从关联 SQL 持续推断关系。", ["数据工程师", "DBA"], "available", "catalog", "查看关系", ["TiDB/MySQL 数据源", "关联查询 SQL"], ["表级/字段级网络图", "来源、次数与置信度"], ["采集账号只读", "仅解析不执行 SQL", "标记推断关系"], ["data-quality"], ["POST /api/v1/data-relationships/{datasource_id}/collect", "POST /api/v1/data-relationships/{datasource_id}/collect-sql"]),
            feature("governance-impact", "变更影响分析", "在改表、改指标或数据异常前计算受影响任务和服务。", ["数据工程师", "发布经理"], "demo", "scenarios", "发起影响分析", ["变更对象", "变更类型"], ["影响清单", "责任人", "风险"], READ_ONLY, ["data-quality", "release-review"]),
            feature("governance-sql-assets", "SQL 资产梳理", "归档查询 SQL，识别重复、高风险和热点语句。", ["DBA", "数据工程师"], "planned", "sql-optimizer", "分析 SQL", ["SQL 日志", "来源任务"], ["SQL 资产", "相似组", "风险标签"], ["SQL 文本脱敏", "按租户隔离"]),
            feature("governance-quality", "数据质量规则", "维护空值、重复、范围、波动和一致性规则。", ["数据工程师", "数据 Steward"], "demo", "scenarios", "调查质量异常", ["资产", "规则与阈值"], ["规则结果", "异常任务"], ["规则版本化", "修复必须复验"], ["data-quality"]),
            feature("governance-stewardship", "标签、口径与责任人", "维护业务术语、敏感级别、负责人和指标关联。", ["数据 Steward", "管理员"], "planned", None, "待接入", ["资产", "标签/术语/负责人"], ["治理属性", "变更记录"], ["变更审批", "历史版本可追溯"]),
        ],
    ),
    ProductModule(
        id="aiops",
        name="AIOps 事件与巡检",
        domain="operations",
        summary="把告警、观测证据、根因假设、Runbook、验证和复盘放在同一 Incident 上下文。",
        owner_role="SRE 负责人",
        features=[
            feature("aiops-event-center", "事件中心", "聚合、过滤和分派告警与 Incident。", ["SRE", "值班长"], "available", "incidents", "查看事件", ["严重级别", "状态", "服务"], ["事件列表", "负责人"], READ_ONLY, ["incident-warroom"], ["GET /api/v1/incidents"]),
            feature("aiops-evidence", "观测证据采集", "关联指标、日志、链路、数据库和最近变更。", ["SRE", "DBA"], "demo", "incidents", "查看证据", ["Incident", "时间窗"], ["证据时间线", "关联对象"], ["只读连接", "证据保留来源与时间"], ["incident-warroom"]),
            feature("aiops-rca", "根因分析与反证", "基于拓扑、规则和历史案例形成可验证根因候选。", ["SRE", "DBA"], "demo", "incidents", "开始分析", ["证据", "拓扑", "变更"], ["根因候选", "反证", "下一步"], ["生成式解释不得替代证据", "允许人工否决"], ["incident-warroom"]),
            feature("aiops-runbook", "受控 Runbook", "从版本化白名单选择处置动作并执行前置检查。", ["SRE", "值班长"], "demo", "scenarios", "选择处置", ["Incident", "Runbook 参数"], ["Dry-run", "执行计划", "回滚"], APPROVAL, ["incident-warroom", "batch-guard"]),
            feature("aiops-batch", "夜间跑批值守", "发现失败/超时任务，分类原因、策略重跑并校验数据。", ["运维", "数据工程师"], "demo", "scenarios", "启动值守", ["调度范围", "值守规则"], ["异常任务", "处置与校验报告"], APPROVAL, ["batch-guard"]),
            feature("aiops-db-health", "数据库健康巡检", "检查慢 SQL、锁、连接、热点、容量、备份和统计信息。", ["DBA", "SRE"], "demo", "scenarios", "启动巡检", ["集群", "检查项"], ["异常项", "优化任务", "日报"], READ_ONLY, ["db-health"]),
            feature("aiops-release-watch", "发布观察窗", "比较发布前后技术和业务指标并给出关闭/回滚建议。", ["发布经理", "SRE"], "demo", "scenarios", "开启观察窗", ["版本", "观察时长", "阈值"], ["基线对比", "关闭/回滚建议"], APPROVAL, ["release-watch"]),
            feature("aiops-postmortem", "恢复验证与复盘", "核对 SLO 和业务结果，归档时间线、根因和改进项。", ["SRE", "值班长"], "planned", "incidents", "查看事件", ["Incident", "验证规则"], ["恢复结论", "复盘", "知识条目"], ["关闭前必须验证", "复盘不可覆盖原证据"], ["incident-warroom"]),
        ],
    ),
    ProductModule(
        id="sql-optimization",
        name="TiDB SQL 优化",
        domain="operations",
        summary="面向 TiDB 7.5+ 的 SQL 输入、版本画像、执行计划、规则诊断和变更验证。",
        owner_role="DBA 负责人",
        features=[
            feature("sql-input", "SQL/DDL 多方式输入", "支持粘贴、SQL 文件和受控本机目录。", ["DBA", "开发"], "available", "sql-optimizer", "载入 SQL", ["SQL", "DDL/文件/目录"], ["标准化输入包"], ["扩展名与目录白名单", "不执行写 SQL"], ["db-health"], ["POST /api/v1/aiops/sql-optimizer/inputs/upload"]),
            feature("sql-version-profile", "TiDB 版本画像", "区分 TiDB 7.5+ 各版本优化器特性和规则。", ["DBA", "开发"], "available", "sql-optimizer", "选择版本", ["TiDB 版本"], ["版本特性", "规则来源"], ["不把新版本能力套用于旧版本"], ["db-health"], ["GET /api/v1/aiops/sql-optimizer/versions"]),
            feature("sql-simulate", "执行计划模拟", "无目标集群时按版本画像生成可解释的近似计划。", ["DBA", "开发"], "available", "sql-optimizer", "模拟计划", ["SQL", "DDL", "版本"], ["模拟计划", "假设"], ["明确标记模拟结果", "不得冒充真实 EXPLAIN"], ["db-health"]),
            feature("sql-live-explain", "真实 TiDB EXPLAIN", "连接版本匹配的只读目标集群获取真实计划。", ["DBA"], "planned", "sql-optimizer", "配置真实计划", ["SQL", "目标集群", "版本"], ["真实执行计划"], ["版本握手", "只读 EXPLAIN", "超时与资源限制"], ["db-health"]),
            feature("sql-advice", "SQL 与索引建议", "结合规则、TiDB 特性和计划风险给出改写与索引建议。", ["DBA", "开发"], "available", "sql-optimizer", "开始优化", ["计划", "表结构", "现有索引"], ["风险节点", "改写/索引建议", "依据"], ["不重复推荐已有左前缀索引", "建议需测试验证"], ["db-health"], ["POST /api/v1/aiops/sql-optimizer/analyze"]),
            feature("sql-change", "DDL 评审与收益验证", "评估索引写放大、空间和查询收益后进入变更审批。", ["DBA", "发布经理"], "planned", "scenarios", "发起评审", ["建议 DDL", "测试结果"], ["变更单", "回滚与验证"], APPROVAL, ["release-review", "db-health"]),
        ],
    ),
    ProductModule(
        id="scenario-command",
        name="场景中心与智能指挥",
        domain="collaboration",
        summary="用模板、Agent Team、证据、审批和验收规则编排跨系统企业任务。",
        owner_role="场景运营负责人",
        features=[
            feature("scenario-batch", "夜间跑批值守与自动恢复", "调度检查、日志分类、策略重跑和数据校验。", ["运维", "数据工程师"], "demo", "scenarios", "启动场景", ["值守范围", "重跑策略"], ["任务报告", "校验结果"], APPROVAL, ["batch-guard"]),
            feature("scenario-warroom", "生产故障虚拟作战室", "并行采集观测、数据库、平台和业务影响证据。", ["SRE", "DBA", "值班长"], "demo", "scenarios", "建立作战室", ["事故目标", "影响上下文"], ["根因", "止损方案", "恢复验证"], APPROVAL, ["incident-warroom"]),
            feature("scenario-script", "脚本异常自动修复", "诊断、Git 分支补丁、隔离测试、Review 和发布。", ["开发", "测试", "发布经理"], "demo", "scenarios", "启动修复", ["失败日志", "代码库"], ["补丁", "测试报告", "发布审批"], APPROVAL, ["script-repair"]),
            feature("scenario-db", "数据库每日健康巡检", "定时检查数据库关键健康项并创建异常任务。", ["DBA", "SRE"], "demo", "scenarios", "启动巡检", ["集群", "巡检策略"], ["异常项", "日报"], READ_ONLY, ["db-health"]),
            feature("scenario-release-review", "发布前自动风险评审", "并行审查 Diff、测试、安全、DDL 与回滚。", ["发布经理", "开发", "安全"], "demo", "scenarios", "发起评审", ["版本号", "变更范围"], ["风险评分", "阻断项", "审批材料"], APPROVAL, ["release-review"]),
            feature("scenario-release-watch", "发布后智能观察窗", "持续观察技术与业务指标并决定关闭或回滚。", ["发布经理", "SRE"], "demo", "scenarios", "开启观察", ["版本", "阈值"], ["观察报告", "回滚建议"], APPROVAL, ["release-watch"]),
            feature("scenario-quality", "数据质量异常调查", "追溯血缘、Schema 和最近变更并形成修复补数计划。", ["数据工程师", "数据 Steward"], "demo", "scenarios", "调查异常", ["失败规则", "数据范围"], ["影响清单", "修复与复验"], APPROVAL, ["data-quality"]),
            feature("scenario-query", "企业智能问数交付团队", "协作完成口径、SQL、验证和 BI 报告。", ["业务用户", "数据分析师"], "demo", "scenarios", "创建分析任务", ["业务问题", "交付要求"], ["SQL", "图表", "分析报告"], READ_ONLY, ["smart-query-team"]),
            feature("scenario-customer", "客户工单自动诊断", "分类工单、检索知识、检查授权环境并起草回复。", ["客户支持", "SRE"], "demo", "scenarios", "诊断工单", ["工单", "授权范围"], ["诊断", "回复草稿"], ["客户数据需明确授权", "外发回复人工确认"], ["customer-diagnosis"]),
            feature("scenario-security", "安全漏洞响应流水线", "同步漏洞、匹配 SBOM、测试补丁并分批修复。", ["安全", "SRE"], "demo", "scenarios", "响应漏洞", ["CVE", "资产范围"], ["影响资产", "修复与复扫"], APPROVAL, ["security-response"]),
            feature("scenario-finops", "云成本持续优化", "识别浪费、测算收益、生成变更任务并追踪节省。", ["FinOps", "云平台"], "demo", "scenarios", "扫描成本", ["账单范围", "资源范围"], ["优化项", "收益台账"], APPROVAL, ["cloud-finops"]),
            feature("scenario-project", "项目数字参谋部", "汇总 Git、CI 和任务事实，识别阻塞并生成报告。", ["项目经理", "研发负责人"], "demo", "scenarios", "生成项目快照", ["项目", "统计周期"], ["风险清单", "日报/周报", "任务草稿"], ["催办与分派遵循团队权限"], ["project-staff"]),
        ],
    ),
    ProductModule(
        id="task-approval",
        name="任务、审批与执行",
        domain="collaboration",
        summary="统一承接场景步骤、人工责任、风险审批、受控执行、验证回滚和审计。",
        owner_role="流程与安全负责人",
        features=[
            feature("task-queue", "任务队列与责任人", "跟踪任务目标、来源、负责人、截止时间和阻塞。", ["全员", "管理者"], "demo", "scenarios", "查看运行", ["任务条件"], ["任务队列", "状态与责任人"], ["服务端状态机为准"], scenario_ids=["batch-guard", "incident-warroom", "project-staff"]),
            feature("task-evidence", "步骤证据与审计轨迹", "每一步保存工具输入摘要、结果、时间和关联对象。", ["执行人", "审计员"], "demo", "scenarios", "查看证据", ["运行实例"], ["步骤证据", "审计轨迹"], ["证据追加写", "敏感值脱敏"]),
            feature("task-risk", "风险分级与策略判断", "按动作、环境、数据和影响范围计算风险。", ["审批人", "安全"], "demo", "scenarios", "查看策略", ["动作", "目标环境", "影响"], ["风险等级", "允许动作"], ["Critical 永久人工审批"]),
            feature("task-approval", "单步骤审批", "批准或拒绝当前高风险步骤，不复用到后续动作。", ["审批人", "值班长"], "available", "scenarios", "处理审批", ["审批请求", "意见"], ["审批决定", "有效期"], ["审批人与执行人分离", "高风险二次认证"], api_refs=["POST /api/v1/scenario-runs/{id}/approve"]),
            feature("task-execution", "白名单执行与状态", "调用注册的 Runbook 并持续记录执行状态。", ["SRE", "执行人"], "demo", "scenarios", "推进步骤", ["已审批动作", "参数"], ["执行日志", "状态"], ["短期凭证", "幂等键", "禁止任意 Shell"], api_refs=["POST /api/v1/scenario-runs/{id}/advance"]),
            feature("task-verify", "验证、回滚与归档", "执行后核验技术和业务结果，失败时进入回滚或人工接管。", ["执行人", "审批人"], "demo", "scenarios", "核验结果", ["执行结果", "验证规则"], ["验证结论", "回滚记录"], ["状态不明时禁止盲目重试"]),
        ],
    ),
    ProductModule(
        id="platform-admin",
        name="平台管理与集成",
        domain="platform",
        summary="管理企业数据源、模型、连接器、身份权限、策略、审计和平台健康。",
        owner_role="平台管理员",
        features=[
            feature("admin-datasource", "数据源管理与连接测试", "手动添加 TiDB、MySQL、CSV 或 Parquet 数据源并验证可用性。", ["管理员", "DBA", "数据分析师"], "available", "datasources", "添加数据源", ["数据库连接参数或文件", "只读凭证"], ["连接状态", "结构/行数摘要", "ChatBI 可选数据源"], ["凭证不回显", "只读账号", "删除二次确认"], api_refs=["GET/POST/DELETE /api/v1/chatbi/datasources", "POST /api/v1/chatbi/datasources/{id}/test", "POST /api/v1/chatbi/datasources/upload"]),
            feature("admin-model", "大模型接入与默认路由", "注册公有 OpenAI-compatible API、Ollama、vLLM 和企业自建模型，并选择平台默认模型。", ["管理员", "AI 工程师"], "available", "models", "添加模型", ["Provider", "Endpoint", "模型 ID（可选，可自动识别）", "凭证"], ["连接状态", "默认模型", "可用能力"], ["凭证不回显", "私网/HTTPS 主机策略", "连接测试后才能启用"], api_refs=["GET/POST /api/v1/models/connections"]),
            feature("admin-agent", "模块 Agent 一键装配", "基于当前默认模型，为 8 个一级模块批量或单独创建具备独立能力、工具白名单和审批策略的 Agent。", ["管理员", "AI 工程师", "模块负责人"], "available", "agents", "创建模块 Agent", ["已验证默认模型", "模块模板"], ["Agent 实例", "模型绑定", "配置自检与对话测试"], ["批量创建幂等", "工具默认只读或仅建议", "高风险动作必须审批", "模型凭证不进入 Agent 配置"], api_refs=["GET /api/v1/agents/templates", "POST /api/v1/agents/provision", "POST /api/v1/agents/{id}/test", "POST /api/v1/agents/{id}/invoke"]),
            feature("admin-connectors", "企业系统连接器", "管理监控、日志、调度、Git、工单与执行平台 Adapter。", ["管理员", "SRE"], "planned", None, "待接入", ["连接器配置", "权限范围"], ["健康状态", "能力与动作 Schema"], ["最小权限", "超时与熔断", "调用审计"]),
            feature("admin-iam", "租户、SSO 与 RBAC/ABAC", "管理用户、角色、工作区和资源/环境策略。", ["管理员", "安全"], "planned", None, "待接入", ["身份源", "角色", "策略"], ["有效权限", "策略版本"], ["默认拒绝", "生产最小权限"]),
            feature("admin-policy", "策略、Runbook 与审批矩阵", "版本化管理风险规则、动作和审批责任链。", ["管理员", "安全", "值班长"], "planned", None, "待接入", ["动作 Schema", "风险", "审批人"], ["可发布策略", "回滚版本"], ["发布前测试", "双人复核"]),
            feature("admin-audit", "统一审计与检索", "按人员、资源、动作、策略和 Trace 查询审计事件。", ["审计员", "安全"], "planned", None, "待接入", ["检索条件"], ["审计记录", "受控导出"], ["审计不可修改", "导出本身受审计"]),
            feature("admin-health", "平台健康与降级", "展示 API、数据库、索引、模型、连接器和执行网关健康。", ["管理员", "SRE"], "demo", "workbench", "查看工作台", ["环境"], ["健康摘要", "降级状态"], ["核心依赖故障时禁止高风险执行"], api_refs=["GET /health", "GET /api/v1/workbench/summary"]),
        ],
    ),
]


PRODUCT_FEATURES = {
    item.id: item
    for module in PRODUCT_MODULES
    for item in module.features
}


def list_modules(
    role: str | None = None,
    state: DeliveryState | None = None,
    search: str | None = None,
) -> list[ProductModule]:
    needle = (search or "").strip().lower()
    result: list[ProductModule] = []
    for module in PRODUCT_MODULES:
        matched = [
            item
            for item in module.features
            if (not role or role in item.roles)
            and (not state or item.delivery_state == state)
            and (
                not needle
                or needle in f"{module.name} {item.name} {item.summary}".lower()
            )
        ]
        if matched:
            result.append(module.model_copy(update={"features": matched}))
    return result
