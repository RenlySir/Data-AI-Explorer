import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import type { EChartsOption } from "echarts";
import {
  LayoutDashboard,
  MessageSquare,
  Activity,
  Database,
  Settings,
  Search,
  ArrowUpRight,
  Clock3,
  CheckCircle2,
  Play,
  ChevronRight,
  LogOut,
  Network,
  Link2,
  UploadCloud,
  FileUp,
  X,
  WandSparkles,
  FileCode2,
  ShieldCheck,
  GitCompareArrows,
  CircleAlert,
  Workflow,
  Bot,
  ListChecks,
  PlayCircle,
  PauseCircle,
  CircleCheck,
  ArrowRight,
  RefreshCw,
  BookOpen,
  FileText,
  FolderOpen,
  Plus,
  Quote,
  Send,
} from "lucide-react";
import "./styles.css";
import "./optimizer.css";
import "./scenarios.css";
import "./knowledge.css";
import "./capabilities.css";

type Page =
  | "workbench"
  | "capabilities"
  | "query"
  | "incidents"
  | "assets"
  | "catalog"
  | "sql-optimizer"
  | "scenarios"
  | "knowledge";
type Catalog = {
  database: string;
  source: string;
  schemas: {
    name: string;
    tables: {
      name: string;
      comment?: string;
      columns: {
        name: string;
        data_type: string;
        comment?: string;
        nullable: boolean;
      }[];
    }[];
  }[];
  relationships: { from: string; to: string; type: string }[];
  collected_at: string;
};
type QueryResult = {
  operation_id: string;
  status: string;
  question: string;
  sql?: string;
  answer?: string;
  columns: string[];
  rows: unknown[][];
  evidence: { type: string; label: string; ref: string }[];
  chart?: { option?: EChartsOption; type: string; title: string };
  created_at: string;
};
type Dataset = {
  id: string;
  name: string;
  kind: string;
  path: string;
  rows: number;
  columns: { name: string; type: string }[];
  created_at: string;
};
type OptimizerVersion = {
  minor: string;
  label: string;
  code_tag: string;
  code_commit: string;
  features: string[];
  release_notes: string;
  source: string;
};
type OptimizeResult = {
  analysis_id: string;
  requested_version: string;
  profile_version: string;
  optimizer_mode: "simulated" | "live";
  confidence: "low" | "medium" | "high";
  version_verified: boolean;
  actual_tidb_version?: string;
  summary: string;
  tables: string[];
  plan: {
    id: string;
    est_rows: string;
    task: string;
    access_object: string;
    operator_info: string;
    risk: "low" | "medium" | "high";
  }[];
  recommendations: {
    id: string;
    severity: "info" | "warning" | "critical";
    category: string;
    title: string;
    rationale: string;
    action: string;
    evidence: string[];
  }[];
  version_features: string[];
  assumptions: string[];
  sources: { label: string; url: string; ref: string }[];
};
type ScenarioStep = {
  id: string;
  title: string;
  role: string;
  description: string;
  action: string;
  risk: "low" | "medium" | "high";
  status: "queued" | "running" | "waiting_approval" | "completed" | "skipped";
  evidence: string[];
};
type Scenario = {
  id: string;
  name: string;
  category: string;
  summary: string;
  value: string;
  agents: string[];
  triggers: string[];
  integrations: string[];
  approval_policy: string;
  metrics: string[];
  steps: ScenarioStep[];
  status: "ready" | "running" | "waiting_approval" | "completed" | "failed";
};
type ScenarioRun = {
  run_id: string;
  scenario_id: string;
  scenario_name: string;
  objective: string;
  context: string;
  status: "ready" | "running" | "waiting_approval" | "completed" | "failed";
  created_at: string;
  updated_at: string;
  current_step_id?: string;
  steps: ScenarioStep[];
  approvals_required: number;
  approvals_granted: number;
  audit: string[];
};
type KnowledgeBaseRecord = {
  id: string;
  name: string;
  description: string;
  scope: string;
  embedding_provider: string;
  retrieval_strategy: string;
  chunk_size: number;
  chunk_overlap: number;
  document_count: number;
  chunk_count: number;
  created_at: string;
  updated_at: string;
};
type KnowledgeDocument = {
  id: string;
  title: string;
  source_type: "text" | "upload" | "local_directory" | "connector";
  source_uri: string;
  mime_type: string;
  content_size: number;
  status: "ready" | "processing" | "failed";
  chunk_count: number;
  tags: string[];
  updated_at: string;
};
type KnowledgeChunk = {
  id: string;
  document_id: string;
  position: number;
  text: string;
  token_count: number;
};
type KnowledgeQueryResult = {
  query_id: string;
  question: string;
  answer: string;
  confidence: "low" | "medium" | "high";
  retrieval_mode: string;
  citations: {
    rank: number;
    document_id: string;
    document_title: string;
    chunk_id: string;
    score: number;
    excerpt: string;
    source_uri: string;
    tags: string[];
  }[];
  knowledge_base_id: string;
  generated_at: string;
};
type KnowledgeFeedback = {
  id: string;
  query_id: string;
  helpful: boolean;
  comment: string;
};
type ProductFeature = {
  id: string;
  name: string;
  summary: string;
  roles: string[];
  delivery_state: "available" | "demo" | "planned";
  target_page?: Page;
  action_label: string;
  inputs: string[];
  outputs: string[];
  guardrails: string[];
  scenario_ids: string[];
  api_refs: string[];
};
type ProductModule = {
  id: string;
  name: string;
  domain: "data" | "operations" | "collaboration" | "platform";
  summary: string;
  owner_role: string;
  features: ProductFeature[];
};
const API_BASE = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8080/api/v1"
).replace(/\/$/, "");
async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const isMultipart =
    typeof FormData !== "undefined" && init?.body instanceof FormData;
  const headers = isMultipart
    ? { ...(init?.headers || {}) }
    : { "Content-Type": "application/json", ...(init?.headers || {}) };
  const response = await fetch(API_BASE + path, { ...init, headers });
  if (!response.ok)
    throw new Error((await response.text()) || "API " + response.status);
  return response.json() as Promise<T>;
}
const incidents = [
  {
    id: "INC-240819-001",
    title: "订单同步延迟超过 SLA",
    service: "订单数据管道",
    severity: "P1",
    status: "处理中",
    time: "08:42",
  },
  {
    id: "INC-240819-002",
    title: "TiDB 集群节点磁盘使用率高",
    service: "生产集群 / tidb-03",
    severity: "P2",
    status: "待处理",
    time: "07:18",
  },
  {
    id: "INC-240818-019",
    title: "营销报表刷新失败",
    service: "BI 报表服务",
    severity: "P2",
    status: "已恢复",
    time: "昨天 23:06",
  },
];
const assets = [
  {
    name: "orders",
    type: "业务表",
    owner: "数据平台组",
    rows: "128.4M",
    quality: 98,
    desc: "订单主表，承载交易链路核心事实数据",
  },
  {
    name: "customer_profile",
    type: "维表",
    owner: "客户中心",
    rows: "4.8M",
    quality: 94,
    desc: "客户画像与标签宽表，日更",
  },
  {
    name: "dwd_order_detail",
    type: "明细表",
    owner: "数仓开发组",
    rows: "2.1B",
    quality: 91,
    desc: "订单明细层，支持经营分析与问数",
  },
];
function Login({ onLogin }: { onLogin: () => void }) {
  return (
    <div className="login">
      <div className="login-card">
        <div className="brand-mark">A</div>
        <h1>Aegis AI</h1>
        <p>企业智能数据与运维工作台</p>
        <label>企业账号</label>
        <input placeholder="name@company.com" defaultValue="admin@acme.com" />
        <label>密码</label>
        <input type="password" defaultValue="12345678" />
        <button className="primary wide" onClick={onLogin}>
          登录工作台 <ArrowUpRight size={16} />
        </button>
        <small>本地演示环境 · 数据不会上传外部服务</small>
      </div>
    </div>
  );
}
function App() {
  const [logged, setLogged] = useState(false);
  const [page, setPage] = useState<Page>("workbench");
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [notice, setNotice] = useState("");
  const [catalogLoading, setCatalogLoading] = useState(false);
  const nav = [
    ["workbench", "工作台", LayoutDashboard],
    ["capabilities", "功能中心", ListChecks],
    ["query", "智能问数", MessageSquare],
    ["knowledge", "知识库", BookOpen],
    ["assets", "数据资产", Database],
    ["catalog", "TiDB 结构", Network],
    ["incidents", "AIOps 事件", Activity],
    ["sql-optimizer", "SQL 优化", WandSparkles],
    ["scenarios", "场景中心", Workflow],
  ] as const;
  const loadCatalog = async (endpoint = "demo://tidb") => {
    setCatalogLoading(true);
    try {
      const result = await api<Catalog>("/tidb/mcp/introspect", {
        method: "POST",
        body: JSON.stringify({ endpoint }),
      });
      setCatalog(result);
      setNotice("已采集 " + result.schemas.length + " 个 Schema");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "TiDB MCP 连接失败");
    } finally {
      setCatalogLoading(false);
    }
  };
  if (!logged)
    return (
      <Login
        onLogin={() => {
          setLogged(true);
          void loadCatalog();
        }}
      />
    );
  return (
    <div className="app">
      <aside>
        <div className="logo">
          <span>A</span>
          <b>Aegis AI</b>
        </div>
        {nav.map(([id, label, Icon]) => (
          <button
            className={page === id ? "nav active" : "nav"}
            aria-label={label}
            onClick={() => setPage(id)}
            key={id}
          >
            <Icon size={18} />
            <span className="nav-label">{label}</span>
          </button>
        ))}
        <div className="aside-bottom">
          <button
            className="nav"
            aria-label="系统设置"
            onClick={() => setPage("catalog")}
          >
            <Settings size={18} />
            <span className="nav-label">系统设置</span>
          </button>
          <button
            className="nav"
            aria-label="退出登录"
            onClick={() => setLogged(false)}
          >
            <LogOut size={18} />
            <span className="nav-label">退出登录</span>
          </button>
        </div>
      </aside>
      <main>
        <header>
          <div>
            <span className="eyebrow">企业智能平台</span>
            <h2>{nav.find((n) => n[0] === page)?.[1]}</h2>
          </div>
          <div className="user">
            <span className="status-dot" />
            生产环境 <div className="avatar">林</div>
          </div>
        </header>
        {notice && (
          <div className="notice">
            <CheckCircle2 size={15} />
            {notice}
            <button onClick={() => setNotice("")}>
              <X size={14} />
            </button>
          </div>
        )}
        {page === "workbench" && <Workbench setPage={setPage} />}{" "}
        {page === "capabilities" && <CapabilityCenter setPage={setPage} />}{" "}
        {page === "query" && (
          <QueryV2 catalog={catalog} loadCatalog={loadCatalog} />
        )}{" "}
        {page === "incidents" && <Incidents />}{" "}
        {page === "scenarios" && <ScenarioCenter />}{" "}
        {page === "knowledge" && <KnowledgeBasePage />}{" "}
        {page === "sql-optimizer" && <SQLOptimizerPage />}{" "}
        {page === "assets" && <AssetsV2 />}{" "}
        {page === "catalog" && (
          <CatalogPage
            catalog={catalog}
            loading={catalogLoading}
            loadCatalog={loadCatalog}
          />
        )}
      </main>
    </div>
  );
}
function CapabilityCenter({ setPage }: { setPage: (page: Page) => void }) {
  const [modules, setModules] = useState<ProductModule[]>([]);
  const [selectedModuleId, setSelectedModuleId] = useState("");
  const [selectedFeatureId, setSelectedFeatureId] = useState("");
  const [search, setSearch] = useState("");
  const [role, setRole] = useState("all");
  const [state, setState] = useState<"all" | ProductFeature["delivery_state"]>(
    "all",
  );
  const [error, setError] = useState("");

  useEffect(() => {
    api<ProductModule[]>("/product/modules")
      .then((items) => {
        setModules(items);
        setSelectedModuleId(items[0]?.id || "");
        setSelectedFeatureId(items[0]?.features[0]?.id || "");
      })
      .catch((reason) =>
        setError(reason instanceof Error ? reason.message : "功能目录加载失败"),
      );
  }, []);

  const roles = useMemo(
    () =>
      Array.from(
        new Set(
          modules.flatMap((module) =>
            module.features.flatMap((item) => item.roles),
          ),
        ),
      ).sort((left, right) => left.localeCompare(right, "zh-CN")),
    [modules],
  );
  const visibleModules = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    return modules
      .map((module) => ({
        ...module,
        features: module.features.filter(
          (item) =>
            (role === "all" || item.roles.includes(role)) &&
            (state === "all" || item.delivery_state === state) &&
            (!keyword ||
              `${module.name} ${item.name} ${item.summary} ${item.roles.join(" ")}`
                .toLowerCase()
                .includes(keyword)),
        ),
      }))
      .filter((module) => module.features.length > 0);
  }, [modules, role, search, state]);
  const selectedModule =
    visibleModules.find((module) => module.id === selectedModuleId) ||
    visibleModules[0];
  const selectedFeature =
    selectedModule?.features.find((item) => item.id === selectedFeatureId) ||
    selectedModule?.features[0];
  const counts = modules
    .flatMap((module) => module.features)
    .reduce(
      (result, item) => {
        result[item.delivery_state] += 1;
        return result;
      },
      { available: 0, demo: 0, planned: 0 },
    );
  const stateLabel = {
    available: "可使用",
    demo: "演示闭环",
    planned: "待生产接入",
  } as const;

  return (
    <section className="content capability-page">
      <div className="section-head">
        <div>
          <span className="eyebrow">模块 · 功能 · 角色 · 交付状态</span>
          <h1>功能中心</h1>
          <p className="section-subtitle">
            按当前职责选择可执行功能，已接入页面可直接进入。
          </p>
        </div>
        <span className="chip success">{modules.length} 个模块</span>
      </div>
      <div className="capability-summary">
        <Metric
          label="可直接使用"
          value={String(counts.available)}
          hint="接口与页面已联通"
          tone="green"
        />
        <Metric
          label="演示闭环"
          value={String(counts.demo)}
          hint="等待真实 Adapter"
          tone="blue"
        />
        <Metric
          label="生产接入"
          value={String(counts.planned)}
          hint="按架构计划实施"
          tone="red"
        />
      </div>
      <div className="capability-toolbar">
        <div className="capability-search">
          <Search size={17} />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="搜索功能、场景或角色"
            aria-label="搜索功能"
          />
        </div>
        <select
          value={role}
          onChange={(event) => setRole(event.target.value)}
          aria-label="按角色筛选"
        >
          <option value="all">全部角色</option>
          {roles.map((item) => (
            <option value={item} key={item}>
              {item}
            </option>
          ))}
        </select>
        <select
          value={state}
          onChange={(event) =>
            setState(
              event.target.value as
                | "all"
                | ProductFeature["delivery_state"],
            )
          }
          aria-label="按交付状态筛选"
        >
          <option value="all">全部状态</option>
          <option value="available">可使用</option>
          <option value="demo">演示闭环</option>
          <option value="planned">待生产接入</option>
        </select>
      </div>
      {error && <div className="error-banner">{error}</div>}
      <div className="capability-layout">
        <div className="panel capability-modules">
          <div className="panel-head">
            <h3>产品模块</h3>
            <span className="chip">{visibleModules.length}</span>
          </div>
          {visibleModules.map((module) => (
            <button
              key={module.id}
              className={
                selectedModule?.id === module.id
                  ? "capability-module active"
                  : "capability-module"
              }
              onClick={() => {
                setSelectedModuleId(module.id);
                setSelectedFeatureId(module.features[0]?.id || "");
              }}
            >
              <span>
                <b>{module.name}</b>
                <small>{module.owner_role}</small>
              </span>
              <strong>{module.features.length}</strong>
            </button>
          ))}
          {!visibleModules.length && <div className="empty">没有匹配功能</div>}
        </div>
        <div className="panel capability-features">
          <div className="panel-head">
            <div>
              <h3>{selectedModule?.name || "具体功能"}</h3>
              <span className="panel-help">{selectedModule?.summary}</span>
            </div>
          </div>
          {selectedModule?.features.map((item) => (
            <button
              key={item.id}
              className={
                selectedFeature?.id === item.id
                  ? "capability-feature active"
                  : "capability-feature"
              }
              onClick={() => setSelectedFeatureId(item.id)}
            >
              <span>
                <b>{item.name}</b>
                <small>{item.summary}</small>
              </span>
              <span className={`capability-state ${item.delivery_state}`}>
                {stateLabel[item.delivery_state]}
              </span>
              <ChevronRight size={16} />
            </button>
          ))}
        </div>
        <div className="panel capability-detail">
          {selectedFeature ? (
            <>
              <div className="capability-detail-head">
                <span className="task-icon">
                  <ListChecks size={19} />
                </span>
                <div>
                  <span className="eyebrow">{selectedFeature.id}</span>
                  <h2>{selectedFeature.name}</h2>
                </div>
              </div>
              <p>{selectedFeature.summary}</p>
              <div className="capability-roles">
                {selectedFeature.roles.map((item) => (
                  <span className="chip" key={item}>
                    {item}
                  </span>
                ))}
              </div>
              <CapabilityFact title="需要" items={selectedFeature.inputs} />
              <CapabilityFact title="产出" items={selectedFeature.outputs} />
              <CapabilityFact
                title="安全门禁"
                items={selectedFeature.guardrails}
              />
              {!!selectedFeature.scenario_ids.length && (
                <CapabilityFact
                  title="关联场景"
                  items={selectedFeature.scenario_ids}
                />
              )}
              {!!selectedFeature.api_refs.length && (
                <div className="capability-api">
                  <b>接口契约</b>
                  {selectedFeature.api_refs.map((item) => (
                    <code key={item}>{item}</code>
                  ))}
                </div>
              )}
              <button
                className="primary capability-open"
                disabled={
                  selectedFeature.delivery_state === "planned" ||
                  !selectedFeature.target_page
                }
                onClick={() =>
                  selectedFeature.target_page &&
                  setPage(selectedFeature.target_page)
                }
              >
                {selectedFeature.delivery_state === "planned"
                  ? "待生产接入"
                  : selectedFeature.action_label}
                <ArrowUpRight size={16} />
              </button>
            </>
          ) : (
            <div className="empty">请选择一个具体功能</div>
          )}
        </div>
      </div>
    </section>
  );
}
function CapabilityFact({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="capability-fact">
      <b>{title}</b>
      <div>
        {items.map((item) => (
          <span key={item}>{item}</span>
        ))}
      </div>
    </div>
  );
}
function Workbench({ setPage }: { setPage: (p: Page) => void }) {
  const today = new Intl.DateTimeFormat("zh-CN", {
    month: "long",
    day: "numeric",
    weekday: "long",
  }).format(new Date());
  return (
    <section className="content">
      <div className="welcome">
        <div>
          <span className="eyebrow">{today}</span>
          <h1>早上好，林工</h1>
          <p>这里是今天的运营概览，所有重要事项都在这里。</p>
        </div>
        <div className="welcome-actions">
          <button className="secondary" onClick={() => setPage("capabilities")}>
            <ListChecks size={16} /> 功能中心
          </button>
          <button className="primary" onClick={() => setPage("query")}>
            开始问数 <MessageSquare size={16} />
          </button>
        </div>
      </div>
      <div className="metrics">
        <Metric label="待处理事件" value="2" hint="较昨日 -1" tone="red" />
        <Metric
          label="今日数据任务"
          value="24"
          hint="22 个已完成"
          tone="green"
        />
        <Metric
          label="数据质量评分"
          value="96.4"
          hint="较上周 +1.2"
          tone="blue"
        />
        <Metric
          label="AI 节省工时"
          value="18.6h"
          hint="本周累计"
          tone="purple"
        />
      </div>
      <div className="workbench-tasks" aria-label="常用工作">
        {[
          ["query", "经营数据分析", "自然语言转 SQL 并生成图表", MessageSquare],
          [
            "knowledge",
            "查询企业知识",
            "从制度、手册和案例中获取有引用的回答",
            BookOpen,
          ],
          [
            "sql-optimizer",
            "诊断 SQL 性能",
            "按 TiDB 版本分析执行计划与索引建议",
            WandSparkles,
          ],
          [
            "scenarios",
            "发起协同任务",
            "按模板执行巡检、报告与故障处置",
            Workflow,
          ],
        ].map(([id, title, description, Icon]) => (
          <button
            className="workbench-task"
            key={String(id)}
            onClick={() => setPage(id as Page)}
          >
            <span className="task-icon">
              <Icon size={19} />
            </span>
            <span>
              <b>{String(title)}</b>
              <small>{String(description)}</small>
            </span>
            <ChevronRight size={17} />
          </button>
        ))}
      </div>
      <div className="grid-two">
        <div className="panel">
          <div className="panel-head">
            <h3>需要关注</h3>
            <button className="text-btn" onClick={() => setPage("incidents")}>
              查看全部 <ChevronRight size={14} />
            </button>
          </div>
          {incidents.slice(0, 2).map((i) => (
            <div className="list-row" key={i.id}>
              <div className={"severity " + i.severity.toLowerCase()}>
                {i.severity}
              </div>
              <div className="row-main">
                <b>{i.title}</b>
                <span>
                  {i.service} · {i.time}
                </span>
              </div>
              <span className="chip">{i.status}</span>
            </div>
          ))}
        </div>
        <div className="panel">
          <div className="panel-head">
            <h3>最近问数</h3>
            <button className="text-btn" onClick={() => setPage("query")}>
              新建问题 <ChevronRight size={14} />
            </button>
          </div>
          {[
            "近 30 天各区域 GMV 趋势",
            "订单取消率最高的商品品类",
            "本月新客留存率",
          ].map((x, i) => (
            <div className="query-row" key={x}>
              <MessageSquare size={15} />
              <span>{x}</span>
              <small>{i + 1} 小时前</small>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
function Metric({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string;
  hint: string;
  tone: string;
}) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong className={tone}>{value}</strong>
      <small>{hint}</small>
    </div>
  );
}
function Query({
  query,
  setQuery,
  answer,
  running,
  runQuery,
}: {
  query: string;
  setQuery: (v: string) => void;
  answer: string;
  running: boolean;
  runQuery: () => void;
}) {
  return (
    <section className="content query-page">
      <div className="query-intro">
        <span className="eyebrow">自然语言查询 · 已连接 12 个数据源</span>
        <h1>把问题交给数据</h1>
        <p>用业务语言提问，Aegis 会生成可解释的分析结果。</p>
      </div>
      <div className="query-box">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="例如：近 30 天各区域 GMV 趋势如何？"
        />
        <div className="query-actions">
          <span>支持中文自然语言 · 结果可追溯</span>
          <button className="primary" onClick={runQuery} disabled={running}>
            {running ? (
              <>
                <Clock3 size={16} />
                分析中…
              </>
            ) : (
              <>
                <Play size={16} />
                开始分析
              </>
            )}
          </button>
        </div>
      </div>
      <div className="suggestions">
        {["近 30 天 GMV 趋势", "订单取消率最高的品类", "本月新客留存率"].map(
          (x) => (
            <button onClick={() => setQuery(x)} key={x}>
              {x}
            </button>
          ),
        )}
      </div>
      {(answer || running) && (
        <div className="result panel">
          <div className="panel-head">
            <h3>分析结果</h3>
            <span className="chip success">已验证</span>
          </div>
          {running && !answer ? (
            <div className="loading">正在检索数据资产并生成 SQL…</div>
          ) : (
            <>
              <p className="answer">{answer}</p>
              <div className="evidence">
                <b>证据来源</b>
                <span>orders · dwd_order_detail</span>
                <span>查询耗时 1.8s</span>
              </div>
              <div className="chart">
                <div className="bar b1" />
                <div className="bar b2" />
                <div className="bar b3" />
                <div className="bar b4" />
                <div className="bar b5" />
              </div>
            </>
          )}
        </div>
      )}
    </section>
  );
}
function Incidents() {
  return (
    <section className="content">
      <div className="section-head">
        <div>
          <span className="eyebrow">实时监控 · 过去 24 小时</span>
          <h1>事件中心</h1>
        </div>
        <button className="secondary">
          <CheckCircle2 size={16} />
          标记已读
        </button>
      </div>
      <div className="filters">
        <button className="filter active">
          全部 <b>3</b>
        </button>
        <button className="filter">
          待处理 <b>1</b>
        </button>
        <button className="filter">
          处理中 <b>1</b>
        </button>
        <button className="filter">
          已恢复 <b>1</b>
        </button>
      </div>
      <div className="panel incident-list">
        {incidents.map((i) => (
          <div className="incident" key={i.id}>
            <div className={"severity " + i.severity.toLowerCase()}>
              {i.severity}
            </div>
            <div className="row-main">
              <b>{i.title}</b>
              <span>
                {i.id} · {i.service}
              </span>
            </div>
            <span className="chip">{i.status}</span>
            <small>{i.time}</small>
            <ChevronRight size={17} />
          </div>
        ))}
      </div>
    </section>
  );
}
function Assets() {
  return (
    <section className="content">
      <div className="section-head">
        <div>
          <span className="eyebrow">数据目录 · 128 个资产</span>
          <h1>数据资产</h1>
        </div>
        <button className="primary">
          <Database size={16} />
          接入数据源
        </button>
      </div>
      <div className="searchbar">
        <Search size={18} />
        <input placeholder="搜索表名、字段或业务描述…" />
      </div>
      <div className="asset-grid">
        {assets.map((a) => (
          <div className="asset panel" key={a.name}>
            <div className="asset-top">
              <div className="table-icon">
                <Database size={18} />
              </div>
              <span className="chip success">质量 {a.quality}</span>
            </div>
            <h3>{a.name}</h3>
            <span className="asset-type">
              {a.type} · {a.owner}
            </span>
            <p>{a.desc}</p>
            <div className="asset-foot">
              <span>{a.rows} 行</span>
              <button className="text-btn">
                查看详情 <ChevronRight size={14} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
function ChartView({ option }: { option?: EChartsOption }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current || !option) return;
    let disposed = false;
    let chart:
      | { resize: () => void; dispose: () => void; setOption: (next: EChartsOption) => void }
      | undefined;
    const resize = () => chart?.resize();
    void import("./chart-runtime").then(({ createChart }) => {
      if (disposed || !ref.current) return;
      chart = createChart(ref.current, option);
      window.addEventListener("resize", resize);
    });
    return () => {
      disposed = true;
      window.removeEventListener("resize", resize);
      chart?.dispose();
    };
  }, [option]);
  return <div className="echart" ref={ref} />;
}
function QueryV2({
  catalog,
  loadCatalog,
}: {
  catalog: Catalog | null;
  loadCatalog: (endpoint?: string) => Promise<void>;
}) {
  const [question, setQuestion] = useState("");
  const [endpoint, setEndpoint] = useState("demo://tidb");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<QueryResult | null>(null);
  const [error, setError] = useState("");
  const run = async () => {
    if (!question.trim()) return;
    setRunning(true);
    setError("");
    try {
      const data = await api<QueryResult>("/query/conversations", {
        method: "POST",
        body: JSON.stringify({
          question,
          source_type: "tidb",
          mcp_endpoint: endpoint === "demo://tidb" ? undefined : endpoint,
        }),
      });
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "分析失败");
    } finally {
      setRunning(false);
    }
  };
  return (
    <section className="content query-page">
      <div className="query-intro">
        <span className="eyebrow">自然语言查询 · Text2SQL · ECharts</span>
        <h1>把问题交给数据</h1>
        <p>
          连接 TiDB MCP 后，系统会读取 Schema、表结构和字段 comment，再生成只读
          SQL。
        </p>
      </div>
      <div className="connector-strip">
        <div>
          <b>
            <Link2 size={15} /> TiDB MCP 数据源
          </b>
          <span>
            {catalog
              ? catalog.database + " · " + catalog.schemas.length + " 个 Schema"
              : "尚未采集结构"}
          </span>
        </div>
        <input
          value={endpoint}
          onChange={(e) => setEndpoint(e.target.value)}
          placeholder="MCP Streamable HTTP 地址，或 demo://tidb"
        />
        <button
          className="secondary"
          onClick={() => void loadCatalog(endpoint)}
          disabled={running}
        >
          <Network size={15} />
          采集结构
        </button>
      </div>
      <div className="query-box">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="例如：近 30 天各区域 GMV 趋势如何？"
        />
        <div className="query-actions">
          <span>只读 SQL · 权限检查 · 结果可追溯</span>
          <button className="primary" onClick={run} disabled={running}>
            {running ? (
              <>
                <Clock3 size={16} />
                分析中…
              </>
            ) : (
              <>
                <Play size={16} />
                开始分析
              </>
            )}
          </button>
        </div>
      </div>
      <div className="suggestions">
        {["近 30 天 GMV 趋势", "订单金额按区域汇总", "客户数量按区域分布"].map(
          (x) => (
            <button onClick={() => setQuestion(x)} key={x}>
              {x}
            </button>
          ),
        )}
      </div>
      {error && <div className="error-banner">{error}</div>}
      {result && (
        <div className="result panel">
          <div className="panel-head">
            <h3>分析结果</h3>
            <span className="chip success">
              {result.status === "completed" ? "已验证" : result.status}
            </span>
          </div>
          <p className="answer">{result.answer}</p>
          {result.chart?.option && <ChartView option={result.chart.option} />}
          <div className="result-grid">
            <div>
              <b>只读 SQL</b>
              <pre>{result.sql}</pre>
            </div>
            <div className="evidence">
              <b>证据来源</b>
              {result.evidence.map((item) => (
                <span key={item.type + "-" + item.ref}>{item.label}</span>
              ))}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
function AssetsV2() {
  const [search, setSearch] = useState("");
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [directory, setDirectory] = useState("");
  const [message, setMessage] = useState("");
  const [datasetId, setDatasetId] = useState("");
  const [datasetQuestion, setDatasetQuestion] = useState("");
  const [datasetResult, setDatasetResult] = useState<QueryResult | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const filtered = assets.filter((item) =>
    (item.name + " " + item.desc).toLowerCase().includes(search.toLowerCase()),
  );
  const upload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const body = new FormData();
    body.append("file", file);
    try {
      const item = await api<Dataset>("/datasets/upload", {
        method: "POST",
        headers: {},
        body,
      });
      setDatasets((current) => [...current, item]);
      setDatasetId(item.id);
      setMessage("已上传 " + item.name + "，共 " + item.rows + " 行");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "上传失败");
    }
  };
  const scan = async () => {
    try {
      const data = await api<Dataset[]>("/datasets/local-directory", {
        method: "POST",
        body: JSON.stringify({ path: directory }),
      });
      setDatasets((current) => [...current, ...data]);
      if (data[0]) setDatasetId(data[0].id);
      setMessage("已扫描 " + data.length + " 个文件");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "目录扫描失败");
    }
  };
  const analyze = async () => {
    if (!datasetId || !datasetQuestion.trim()) return;
    setAnalyzing(true);
    setMessage("");
    try {
      const result = await api<QueryResult>("/datasets/analyze", {
        method: "POST",
        body: JSON.stringify({
          question: datasetQuestion,
          dataset_ids: [datasetId],
        }),
      });
      setDatasetResult(result);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "文件分析失败");
    } finally {
      setAnalyzing(false);
    }
  };
  return (
    <section className="content">
      <div className="section-head">
        <div>
          <span className="eyebrow">数据目录 · TiDB / 文件数据</span>
          <h1>数据资产</h1>
        </div>
        <label className="primary file-button">
          <UploadCloud size={16} />
          上传 CSV/Parquet
          <input type="file" accept=".csv,.parquet" onChange={upload} />
        </label>
      </div>
      <div className="dataset-tools">
        <b>
          <FileUp size={16} />
          文件数据分析
        </b>
        <input
          value={directory}
          onChange={(e) => setDirectory(e.target.value)}
          placeholder="允许目录路径，如 /workspace/data"
        />
        <button className="secondary" onClick={scan}>
          扫描目录
        </button>
      </div>
      {message && <div className="notice">{message}</div>}
      <div className="searchbar">
        <Search size={18} />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="搜索表名、字段或业务描述…"
        />
      </div>
      <div className="asset-grid">
        {filtered.map((a) => (
          <div className="asset panel" key={a.name}>
            <div className="asset-top">
              <div className="table-icon">
                <Database size={18} />
              </div>
              <span className="chip success">质量 {a.quality}</span>
            </div>
            <h3>{a.name}</h3>
            <span className="asset-type">
              {a.type} · {a.owner}
            </span>
            <p>{a.desc}</p>
            <div className="asset-foot">
              <span>{a.rows} 行</span>
              <button className="text-btn">
                查看详情 <ChevronRight size={14} />
              </button>
            </div>
          </div>
        ))}
      </div>
      {datasets.length > 0 && (
        <>
          <div className="panel dataset-list">
            <div className="panel-head">
              <h3>已注册文件数据</h3>
              <span className="chip success">可分析</span>
            </div>
            {datasets.map((item) => (
              <div className="list-row" key={item.id}>
                <FileUp size={16} />
                <div className="row-main">
                  <b>{item.name}</b>
                  <span>
                    {item.kind.toUpperCase()} · {item.rows} 行 ·{" "}
                    {item.columns.length} 列
                  </span>
                </div>
                <span className="chip">{item.id}</span>
              </div>
            ))}
          </div>
          <div className="panel dataset-analyzer">
            <div className="panel-head">
              <h3>文件数据问答与报表</h3>
              <span className="chip">DuckDB</span>
            </div>
            <div className="dataset-form">
              <select
                value={datasetId}
                onChange={(e) => setDatasetId(e.target.value)}
                aria-label="选择文件数据"
              >
                {datasets.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name} · {item.rows} 行
                  </option>
                ))}
              </select>
              <textarea
                value={datasetQuestion}
                onChange={(e) => setDatasetQuestion(e.target.value)}
                placeholder="例如：按天汇总金额并展示趋势"
              />
              <button
                className="primary"
                onClick={analyze}
                disabled={analyzing}
              >
                {analyzing ? (
                  <>
                    <Clock3 size={16} />
                    分析中…
                  </>
                ) : (
                  <>
                    <Play size={16} />
                    生成报表
                  </>
                )}
              </button>
            </div>
            {datasetResult && (
              <>
                <p className="answer">{datasetResult.answer}</p>
                {datasetResult.chart?.option && (
                  <ChartView option={datasetResult.chart.option} />
                )}
                <div className="result-grid">
                  <div>
                    <b>执行 SQL</b>
                    <pre>{datasetResult.sql}</pre>
                  </div>
                  <div className="evidence">
                    <b>数据来源</b>
                    {datasetResult.evidence.map((item) => (
                      <span key={item.type + "-" + item.ref}>{item.label}</span>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        </>
      )}
    </section>
  );
}
function CatalogPage({
  catalog,
  loading,
  loadCatalog,
}: {
  catalog: Catalog | null;
  loading: boolean;
  loadCatalog: (endpoint?: string) => Promise<void>;
}) {
  const [endpoint, setEndpoint] = useState("demo://tidb");
  return (
    <section className="content">
      <div className="section-head">
        <div>
          <span className="eyebrow">MCP 元数据采集 · 字段注释 · 关系图</span>
          <h1>TiDB 数据结构</h1>
        </div>
        <button
          className="primary"
          onClick={() => void loadCatalog(endpoint)}
          disabled={loading}
        >
          {loading ? "采集中…" : "重新采集"}
        </button>
      </div>
      <div className="connector-strip">
        <input
          value={endpoint}
          onChange={(e) => setEndpoint(e.target.value)}
          placeholder="MCP endpoint"
        />
        <span className="chip">{catalog?.source || "未连接"}</span>
      </div>
      {catalog ? (
        <>
          <div className="schema-summary">
            <Metric
              label="Schema"
              value={String(catalog.schemas.length)}
              hint={catalog.database}
              tone="blue"
            />
            <Metric
              label="表"
              value={String(
                catalog.schemas.reduce(
                  (sum, schema) => sum + schema.tables.length,
                  0,
                ),
              )}
              hint="已读取表结构"
              tone="green"
            />
            <Metric
              label="关系"
              value={String(catalog.relationships.length)}
              hint="字段/派生关系"
              tone="purple"
            />
          </div>
          <div className="schema-layout">
            <div className="schema-list">
              {catalog.schemas.map((schema) => (
                <div className="schema-card panel" key={schema.name}>
                  <div className="panel-head">
                    <h3>
                      <Database size={15} /> {schema.name}
                    </h3>
                    <span className="chip">{schema.tables.length} tables</span>
                  </div>
                  {schema.tables.map((table) => (
                    <details key={table.name}>
                      <summary>
                        <b>{table.name}</b>
                        <span>{table.comment || "暂无表 comment"}</span>
                      </summary>
                      <div className="column-list">
                        {table.columns.map((column) => (
                          <div className="column-row" key={column.name}>
                            <code>{column.name}</code>
                            <span>{column.data_type}</span>
                            <small>
                              {column.comment || "暂无字段 comment"}
                            </small>
                          </div>
                        ))}
                      </div>
                    </details>
                  ))}
                </div>
              ))}
            </div>
            <div className="relationship-panel panel">
              <div className="panel-head">
                <h3>
                  <Network size={15} /> 关系视图
                </h3>
                <span className="chip success">可追溯</span>
              </div>
              {catalog.relationships.map((edge) => (
                <div className="edge" key={edge.from + "-" + edge.to}>
                  <span>{edge.from}</span>
                  <Link2 size={15} />
                  <span>{edge.to}</span>
                  <small>{edge.type}</small>
                </div>
              ))}
            </div>
          </div>
        </>
      ) : (
        <div className="empty panel">尚未采集 TiDB 结构，请点击重新采集。</div>
      )}
    </section>
  );
}
function KnowledgeBasePage() {
  const [libraries, setLibraries] = useState<KnowledgeBaseRecord[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [question, setQuestion] = useState(
    "TiDB 巡检发现慢 SQL 时应该如何处理？",
  );
  const [result, setResult] = useState<KnowledgeQueryResult | null>(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [tags, setTags] = useState("");
  const [directory, setDirectory] = useState("");
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<
    "ask" | "documents" | "retrieval" | "settings"
  >("ask");
  const [queries, setQueries] = useState<KnowledgeQueryResult[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState("");
  const [chunks, setChunks] = useState<KnowledgeChunk[]>([]);
  const [feedback, setFeedback] = useState<"helpful" | "not-helpful" | "idle">(
    "idle",
  );
  const selected =
    libraries.find((item) => item.id === selectedId) || libraries[0];

  const loadLibraries = async (preferredId?: string) => {
    try {
      const items = await api<KnowledgeBaseRecord[]>("/knowledge-bases");
      setLibraries(items);
      setSelectedId((current) => preferredId || current || items[0]?.id || "");
    } catch (e) {
      setError(e instanceof Error ? e.message : "知识库加载失败");
    }
  };
  const loadDocuments = async (knowledgeBaseId: string) => {
    try {
      setDocuments(
        await api<KnowledgeDocument[]>(
          `/knowledge-bases/${knowledgeBaseId}/documents`,
        ),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "文档列表加载失败");
    }
  };
  const loadQueries = async (knowledgeBaseId: string) => {
    try {
      setQueries(
        await api<KnowledgeQueryResult[]>(
          "/knowledge-bases/" + knowledgeBaseId + "/queries?limit=20",
        ),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "检索历史加载失败");
    }
  };
  const loadChunks = async (knowledgeBaseId: string, documentId: string) => {
    try {
      setChunks(
        await api<KnowledgeChunk[]>(
          "/knowledge-bases/" +
            knowledgeBaseId +
            "/documents/" +
            documentId +
            "/chunks",
        ),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "分块预览加载失败");
    }
  };
  useEffect(() => {
    void loadLibraries();
  }, []);
  useEffect(() => {
    if (selectedId) {
      setResult(null);
      void loadDocuments(selectedId);
      void loadQueries(selectedId);
      setSelectedDocumentId("");
      setChunks([]);
      setFeedback("idle");
    }
  }, [selectedId]);
  const refresh = async () => {
    await loadLibraries(selectedId);
    if (selectedId) {
      await loadDocuments(selectedId);
      await loadQueries(selectedId);
    }
  };
  const createLibrary = async () => {
    if (!newName.trim()) return;
    setBusy("create");
    setError("");
    try {
      const item = await api<KnowledgeBaseRecord>("/knowledge-bases", {
        method: "POST",
        body: JSON.stringify({
          name: newName.trim(),
          description: newDescription.trim(),
        }),
      });
      setNewName("");
      setNewDescription("");
      setShowCreate(false);
      await loadLibraries(item.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "创建知识库失败");
    } finally {
      setBusy("");
    }
  };
  const addTextDocument = async () => {
    if (!selected || !title.trim() || !content.trim()) return;
    setBusy("text");
    setError("");
    try {
      await api<KnowledgeDocument>(
        `/knowledge-bases/${selected.id}/documents`,
        {
          method: "POST",
          body: JSON.stringify({
            title: title.trim(),
            content,
            tags: tags
              .split(",")
              .map((item) => item.trim())
              .filter(Boolean),
          }),
        },
      );
      setTitle("");
      setContent("");
      setTags("");
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "文档入库失败");
    } finally {
      setBusy("");
    }
  };
  const uploadDocuments = async (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    if (!selected || !event.target.files?.length) return;
    setBusy("upload");
    setError("");
    try {
      const form = new FormData();
      Array.from(event.target.files).forEach((file) =>
        form.append("files", file),
      );
      await api<KnowledgeDocument[]>(
        `/knowledge-bases/${selected.id}/documents/upload`,
        {
          method: "POST",
          body: form,
        },
      );
      event.target.value = "";
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "文件上传失败");
    } finally {
      setBusy("");
    }
  };
  const scanDirectory = async () => {
    if (!selected || !directory.trim()) return;
    setBusy("directory");
    setError("");
    try {
      await api<KnowledgeDocument[]>(
        `/knowledge-bases/${selected.id}/documents/local-directory`,
        {
          method: "POST",
          body: JSON.stringify({
            path: directory.trim(),
            tags: tags
              .split(",")
              .map((item) => item.trim())
              .filter(Boolean),
          }),
        },
      );
      setDirectory("");
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "目录扫描失败");
    } finally {
      setBusy("");
    }
  };
  const query = async () => {
    if (!selected || !question.trim()) return;
    setBusy("query");
    setError("");
    try {
      const nextResult = await api<KnowledgeQueryResult>(
        `/knowledge-bases/${selected.id}/query`,
        {
          method: "POST",
          body: JSON.stringify({ question: question.trim(), top_k: 5 }),
        },
      );
      setResult(nextResult);
      setFeedback("idle");
      await loadQueries(selected.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "知识库检索失败");
    } finally {
      setBusy("");
    }
  };
  const submitFeedback = async (helpful: boolean) => {
    if (!selected || !result) return;
    setBusy("feedback");
    try {
      await api<KnowledgeFeedback>(
        "/knowledge-bases/" +
          selected.id +
          "/queries/" +
          result.query_id +
          "/feedback",
        {
          method: "POST",
          body: JSON.stringify({ helpful }),
        },
      );
      setFeedback(helpful ? "helpful" : "not-helpful");
    } catch (e) {
      setError(e instanceof Error ? e.message : "反馈提交失败");
    } finally {
      setBusy("");
    }
  };
  const scenarioQuestions = [
    ["TiDB 慢 SQL", "TiDB 巡检发现慢 SQL 时应该如何处理？"],
    ["生产变更", "生产变更需要哪些审批和回滚准备？"],
    ["数据质量", "数据质量告警后如何定位影响并完成补数验证？"],
    ["故障值班", "线上故障处置完成后需要保留哪些证据？"],
  ] as const;
  return (
    <section className="content knowledge-page">
      <div className="section-head">
        <div>
          <span className="eyebrow">RAG · 文档分块 · 引用溯源</span>
          <h1>知识库</h1>
          <p className="section-subtitle">
            把企业规范、运维手册和项目资料沉淀为可检索、可核验的工作上下文。
          </p>
        </div>
        <button
          className="secondary"
          onClick={() => void refresh()}
          disabled={Boolean(busy)}
        >
          <RefreshCw size={15} /> 刷新
        </button>
      </div>
      {error && (
        <div className="error-banner">
          {error}
          <button onClick={() => setError("")}>
            <X size={14} />
          </button>
        </div>
      )}
      <div className="knowledge-layout">
        <div className="panel knowledge-library">
          <div className="panel-head">
            <h3>
              <LibraryIcon /> 知识库
            </h3>
            <button
              className="icon-btn"
              title="新建知识库"
              onClick={() => setShowCreate((current) => !current)}
            >
              <Plus size={16} />
            </button>
          </div>
          {showCreate && (
            <div className="knowledge-create">
              <input
                value={newName}
                onChange={(event) => setNewName(event.target.value)}
                placeholder="知识库名称"
              />
              <input
                value={newDescription}
                onChange={(event) => setNewDescription(event.target.value)}
                placeholder="用途描述（可选）"
              />
              <button
                className="primary"
                onClick={() => void createLibrary()}
                disabled={busy === "create"}
              >
                <Plus size={14} /> 创建
              </button>
            </div>
          )}
          <div className="knowledge-library-list">
            {libraries.map((item) => (
              <button
                key={item.id}
                className={
                  item.id === selected?.id
                    ? "knowledge-library-item active"
                    : "knowledge-library-item"
                }
                onClick={() => setSelectedId(item.id)}
              >
                <span className="knowledge-library-icon">
                  <BookOpen size={15} />
                </span>
                <span>
                  <b>{item.name}</b>
                  <small>
                    {item.document_count} 份文档 · {item.chunk_count} 个片段
                  </small>
                </span>
              </button>
            ))}
            {!libraries.length && <div className="empty">暂无知识库</div>}
          </div>
        </div>
        <div className="knowledge-main">
          {selected ? (
            <>
              <div className="knowledge-stats">
                <Metric
                  label="文档数"
                  value={String(selected.document_count)}
                  hint="已完成索引"
                  tone="blue"
                />
                <Metric
                  label="检索片段"
                  value={String(selected.chunk_count)}
                  hint={selected.retrieval_strategy}
                  tone="purple"
                />
                <Metric
                  label="分块大小"
                  value={`${selected.chunk_size}`}
                  hint={`重叠 ${selected.chunk_overlap}`}
                  tone="green"
                />
                <Metric
                  label="索引模式"
                  value="本地"
                  hint={selected.embedding_provider}
                  tone="red"
                />
              </div>
              <div
                className="knowledge-tabs"
                role="tablist"
                aria-label="知识库任务"
              >
                {(
                  [
                    ["ask", "问知识库", MessageSquare],
                    ["documents", "文档管理", FileText],
                    ["retrieval", "检索测试", Search],
                    ["settings", "配置", Settings],
                  ] as const
                ).map(([id, label, Icon]) => (
                  <button
                    key={id}
                    role="tab"
                    aria-selected={activeTab === id}
                    className={activeTab === id ? "active" : ""}
                    onClick={() => setActiveTab(id)}
                  >
                    <Icon size={15} /> {label}
                  </button>
                ))}
              </div>
              {activeTab === "ask" && (
                <div className="knowledge-scenarios">
                  <span>常用场景</span>
                  {scenarioQuestions.map(([label, value]) => (
                    <button
                      key={label}
                      onClick={() => {
                        setQuestion(value);
                        setResult(null);
                      }}
                    >
                      {label} <ChevronRight size={13} />
                    </button>
                  ))}
                </div>
              )}
              {(activeTab === "ask" || activeTab === "retrieval") && (
                <div className="panel knowledge-query">
                  <div className="panel-head">
                    <div>
                      <h3>
                        {activeTab === "ask" ? (
                          <MessageSquare size={16} />
                        ) : (
                          <Search size={16} />
                        )}{" "}
                        {activeTab === "ask" ? "问知识库" : "检索测试"}
                      </h3>
                      <span className="panel-help">{selected.name}</span>
                    </div>
                    <span className="chip success">
                      {activeTab === "ask" ? "引用优先" : "单库召回"}
                    </span>
                  </div>
                  <textarea
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    placeholder="输入关于制度、数据或运维资料的问题..."
                  />
                  <div className="knowledge-query-actions">
                    <span>最多返回 5 个相关片段</span>
                    <button
                      className="primary"
                      onClick={() => void query()}
                      disabled={busy === "query"}
                    >
                      <Send size={15} />{" "}
                      {busy === "query"
                        ? "检索中..."
                        : activeTab === "ask"
                          ? "检索并回答"
                          : "运行测试"}
                    </button>
                  </div>
                  {result && (
                    <div className="knowledge-answer">
                      <div className="knowledge-answer-head">
                        <b>回答</b>
                        <span
                          className={`chip ${result.confidence === "low" ? "" : "success"}`}
                        >
                          {result.confidence === "high"
                            ? "高置信度"
                            : result.confidence === "medium"
                              ? "中置信度"
                              : "未找到充分证据"}
                        </span>
                      </div>
                      <p>{result.answer}</p>
                      <div className="knowledge-answer-meta">
                        检索模式：{result.retrieval_mode} · 查询 ID：
                        {result.query_id}
                      </div>
                      <div className="knowledge-citations">
                        <div className="knowledge-citations-title">
                          <Quote size={14} /> 引用来源（
                          {result.citations.length}）
                        </div>
                        {result.citations.map((citation) => (
                          <div
                            className="knowledge-citation"
                            key={citation.chunk_id}
                          >
                            <div className="citation-rank">{citation.rank}</div>
                            <div>
                              <b>{citation.document_title}</b>
                              <span>{citation.excerpt}</span>
                              <small>
                                相关度 {(citation.score * 100).toFixed(0)}% ·{" "}
                                {citation.source_uri}
                              </small>
                            </div>
                          </div>
                        ))}
                      </div>
                      <div className="knowledge-feedback">
                        <span>
                          {feedback === "idle"
                            ? "这次结果是否有帮助？"
                            : "反馈已记录"}
                        </span>
                        <button
                          className={feedback === "helpful" ? "active" : ""}
                          title="有帮助"
                          onClick={() => void submitFeedback(true)}
                          disabled={feedback !== "idle" || busy === "feedback"}
                        >
                          有帮助
                        </button>
                        <button
                          className={
                            feedback === "not-helpful" ? "active negative" : ""
                          }
                          title="需改进"
                          onClick={() => void submitFeedback(false)}
                          disabled={feedback !== "idle" || busy === "feedback"}
                        >
                          需改进
                        </button>
                      </div>
                    </div>
                  )}
                  {activeTab === "retrieval" && (
                    <div className="knowledge-history">
                      <div className="knowledge-citations-title">
                        <Clock3 size={14} /> 最近测试
                      </div>
                      {queries.slice(0, 6).map((item) => (
                        <button
                          key={item.query_id}
                          onClick={() => {
                            setQuestion(item.question);
                            setResult(item);
                            setFeedback("idle");
                          }}
                        >
                          <span>{item.question}</span>
                          <small>
                            {item.citations.length} 条命中 · {item.confidence}
                          </small>
                        </button>
                      ))}
                      {!queries.length && (
                        <div className="empty">运行一次检索后显示记录</div>
                      )}
                    </div>
                  )}
                </div>
              )}
              {activeTab === "documents" && (
                <div className="knowledge-columns">
                  <div className="panel knowledge-documents">
                    <div className="panel-head">
                      <h3>
                        <FileText size={16} /> 文档库
                      </h3>
                      <span className="chip">{documents.length} 份</span>
                    </div>
                    <div className="knowledge-document-list">
                      {documents.map((document) => (
                        <button
                          className={
                            selectedDocumentId === document.id
                              ? "knowledge-document-row active"
                              : "knowledge-document-row"
                          }
                          key={document.id}
                          onClick={() => {
                            setSelectedDocumentId(document.id);
                            void loadChunks(selected.id, document.id);
                          }}
                        >
                          <span className="knowledge-doc-icon">
                            <FileText size={15} />
                          </span>
                          <div>
                            <b>{document.title}</b>
                            <span>
                              {document.source_type} · {document.chunk_count}{" "}
                              个片段
                            </span>
                          </div>
                          <span className="chip success">
                            {document.status === "ready"
                              ? "已就绪"
                              : document.status}
                          </span>
                        </button>
                      ))}
                      {!documents.length && (
                        <div className="empty">尚未添加文档</div>
                      )}
                    </div>
                    {selectedDocumentId && (
                      <div className="knowledge-chunks">
                        <div className="knowledge-citations-title">
                          <ListChecks size={14} /> 分块预览（{chunks.length}）
                        </div>
                        {chunks.map((chunk) => (
                          <div className="knowledge-chunk" key={chunk.id}>
                            <b>片段 {chunk.position + 1}</b>
                            <span>{chunk.text}</span>
                            <small>
                              {chunk.token_count} 个检索词 · {chunk.id}
                            </small>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="panel knowledge-ingest">
                    <div className="panel-head">
                      <h3>
                        <UploadCloud size={16} /> 添加资料
                      </h3>
                      <span className="panel-help">
                        支持 TXT / Markdown / HTML / JSON / SQL
                      </span>
                    </div>
                    <div className="knowledge-ingest-tabs">
                      <span className="active">
                        <FileText size={13} /> 文本
                      </span>
                      <label className="secondary file-button">
                        <UploadCloud size={14} /> 上传文件
                        <input
                          type="file"
                          multiple
                          accept=".txt,.md,.markdown,.html,.htm,.json,.sql,.ddl"
                          onChange={(event) => void uploadDocuments(event)}
                        />
                      </label>
                    </div>
                    <input
                      value={title}
                      onChange={(event) => setTitle(event.target.value)}
                      placeholder="文档标题"
                    />
                    <textarea
                      value={content}
                      onChange={(event) => setContent(event.target.value)}
                      placeholder="粘贴规范、手册或项目资料..."
                    />
                    <input
                      value={tags}
                      onChange={(event) => setTags(event.target.value)}
                      placeholder="标签，用逗号分隔（可选）"
                    />
                    <button
                      className="primary wide"
                      onClick={() => void addTextDocument()}
                      disabled={
                        busy === "text" || !title.trim() || !content.trim()
                      }
                    >
                      <Plus size={15} />{" "}
                      {busy === "text" ? "入库中..." : "入库文本"}
                    </button>
                    <div className="knowledge-directory">
                      <label>
                        <FolderOpen size={14} /> 本机目录
                      </label>
                      <div>
                        <input
                          value={directory}
                          onChange={(event) => setDirectory(event.target.value)}
                          placeholder="/data/handbook"
                        />
                        <button
                          className="secondary"
                          onClick={() => void scanDirectory()}
                          disabled={busy === "directory"}
                        >
                          扫描
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              {activeTab === "settings" && (
                <div className="panel knowledge-settings">
                  <div className="panel-head">
                    <h3>
                      <Settings size={16} /> 知识库配置
                    </h3>
                    <span className="chip success">本地索引</span>
                  </div>
                  <div className="knowledge-setting-grid">
                    <label>
                      <span>知识库名称</span>
                      <input value={selected.name} readOnly />
                    </label>
                    <label>
                      <span>可见范围</span>
                      <input
                        value={
                          selected.scope === "workspace"
                            ? "当前工作区"
                            : selected.scope
                        }
                        readOnly
                      />
                    </label>
                    <label>
                      <span>检索策略</span>
                      <input value={selected.retrieval_strategy} readOnly />
                    </label>
                    <label>
                      <span>索引提供方</span>
                      <input value={selected.embedding_provider} readOnly />
                    </label>
                    <label>
                      <span>分块大小</span>
                      <input value={selected.chunk_size} readOnly />
                    </label>
                    <label>
                      <span>相邻重叠</span>
                      <input value={selected.chunk_overlap} readOnly />
                    </label>
                  </div>
                  <div className="policy-box">
                    <b>生产切换条件</b>
                    <p>
                      完成持久化、向量检索、模型网关、文档 ACL
                      和异步索引验收后，再把索引模式从 local-keyword 切换为
                      hybrid。
                    </p>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="empty panel">请选择或创建知识库</div>
          )}
        </div>
      </div>
    </section>
  );
}
function LibraryIcon() {
  return <BookOpen size={16} />;
}
function scenarioStatusLabel(
  status: ScenarioRun["status"] | Scenario["status"] | ScenarioStep["status"],
) {
  return (
    (
      {
        ready: "可运行",
        running: "运行中",
        waiting_approval: "等待审批",
        completed: "已完成",
        failed: "失败",
        queued: "排队中",
        skipped: "已跳过",
      } as Record<string, string>
    )[status] || status
  );
}
function scenarioStatusClass(status: string) {
  return "scenario-status " + status.replace("_", "-");
}
function ScenarioCenter() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [runs, setRuns] = useState<ScenarioRun[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [category, setCategory] = useState("全部");
  const [objective, setObjective] = useState(
    "检查今晚的关键任务与系统风险，并给出可执行的处置结果",
  );
  const [context, setContext] = useState("");
  const [selectedRun, setSelectedRun] = useState<ScenarioRun | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const load = async () => {
    try {
      const [items, existing] = await Promise.all([
        api<Scenario[]>("/scenarios"),
        api<ScenarioRun[]>("/scenario-runs"),
      ]);
      setScenarios(items);
      setRuns(existing);
      setSelectedId((current) => current || items[0]?.id || "");
      setSelectedRun((current) => current || existing[0] || null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "场景加载失败");
    }
  };
  useEffect(() => {
    void load();
  }, []);
  const categories = [
    "全部",
    ...Array.from(new Set(scenarios.map((item) => item.category))),
  ];
  const filtered = scenarios.filter(
    (item) => category === "全部" || item.category === category,
  );
  const selected =
    scenarios.find((item) => item.id === selectedId) || filtered[0];
  const start = async () => {
    if (!selected || !objective.trim()) return;
    setBusy(true);
    setError("");
    try {
      const run = await api<ScenarioRun>(`/scenarios/${selected.id}/runs`, {
        method: "POST",
        body: JSON.stringify({ objective, context }),
      });
      setSelectedRun(run);
      setRuns((current) => [run, ...current]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "启动场景失败");
    } finally {
      setBusy(false);
    }
  };
  const updateRun = async (action: "advance" | "approve") => {
    if (!selectedRun) return;
    setBusy(true);
    setError("");
    try {
      const run = await api<ScenarioRun>(
        `/scenario-runs/${selectedRun.run_id}/${action}`,
        { method: "POST" },
      );
      setSelectedRun(run);
      setRuns((current) =>
        current.map((item) => (item.run_id === run.run_id ? run : item)),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "场景状态更新失败");
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="content scenario-page">
      <div className="section-head">
        <div>
          <span className="eyebrow">
            Agent Team · 定时触发 · 任务留痕 · 人工审批
          </span>
          <h1>场景中心</h1>
          <p className="section-subtitle">
            把多场景探索中的协作模式落成可配置、可运行、可追踪的企业 AI
            控制平面。
          </p>
        </div>
        <button className="secondary" onClick={() => void load()}>
          <RefreshCw size={16} />
          刷新场景
        </button>
      </div>
      {error && <div className="error-banner">{error}</div>}
      <div className="scenario-summary">
        <Metric
          label="场景模板"
          value={String(scenarios.length)}
          hint="来自多场景探索"
          tone="blue"
        />
        <Metric
          label="运行实例"
          value={String(runs.length)}
          hint="可追踪任务"
          tone="green"
        />
        <Metric
          label="待审批"
          value={String(
            runs.filter((item) => item.status === "waiting_approval").length,
          )}
          hint="高风险动作已阻断"
          tone="red"
        />
        <Metric
          label="已接入模式"
          value="只读优先"
          hint="Runbook 可扩展"
          tone="purple"
        />
      </div>
      <div className="scenario-layout">
        <div className="scenario-library panel">
          <div className="panel-head">
            <h3>
              <Workflow size={16} />
              场景模板
            </h3>
            <span className="chip">{filtered.length} 个</span>
          </div>
          <div className="scenario-filters">
            {categories.map((item) => (
              <button
                key={item}
                className={category === item ? "filter active" : "filter"}
                onClick={() => setCategory(item)}
              >
                {item}
              </button>
            ))}
          </div>
          <div className="scenario-list">
            {filtered.map((item) => (
              <button
                key={item.id}
                className={
                  selected?.id === item.id
                    ? "scenario-card active"
                    : "scenario-card"
                }
                onClick={() => setSelectedId(item.id)}
              >
                <div className="scenario-card-top">
                  <span className="scenario-icon">
                    <Bot size={16} />
                  </span>
                  <span className="chip">{item.category}</span>
                </div>
                <b>{item.name}</b>
                <p>{item.summary}</p>
                <small>
                  {item.agents.length} 个 Agent · {item.steps.length} 个步骤
                </small>
              </button>
            ))}
          </div>
        </div>
        <div className="scenario-detail">
          {selected ? (
            <>
              <div className="panel scenario-hero">
                <div className="scenario-hero-top">
                  <div>
                    <span className="eyebrow">{selected.category}</span>
                    <h2>{selected.name}</h2>
                    <p>{selected.summary}</p>
                  </div>
                  <span className={scenarioStatusClass(selected.status)}>
                    {scenarioStatusLabel(selected.status)}
                  </span>
                </div>
                <div className="scenario-value">
                  <b>提效价值</b>
                  <span>{selected.value}</span>
                </div>
                <div className="scenario-tags">
                  {selected.triggers.map((item) => (
                    <span className="chip" key={item}>
                      触发 · {item}
                    </span>
                  ))}
                  {selected.integrations.slice(0, 4).map((item) => (
                    <span className="chip" key={item}>
                      连接 · {item}
                    </span>
                  ))}
                </div>
              </div>
              <div className="scenario-columns">
                <div className="panel">
                  <div className="panel-head">
                    <h3>
                      <Bot size={16} />
                      Agent 阵容
                    </h3>
                    <span className="chip">{selected.agents.length}</span>
                  </div>
                  <div className="agent-list">
                    {selected.agents.map((item, index) => (
                      <div className="agent-row" key={item}>
                        <span>{String(index + 1).padStart(2, "0")}</span>
                        <b>{item}</b>
                      </div>
                    ))}
                  </div>
                  <div className="policy-box">
                    <b>审批策略</b>
                    <p>{selected.approval_policy}</p>
                  </div>
                </div>
                <div className="panel">
                  <div className="panel-head">
                    <h3>
                      <ListChecks size={16} />
                      执行步骤
                    </h3>
                    <span className="chip">顺序与并行可编排</span>
                  </div>
                  <div className="template-steps">
                    {selected.steps.map((item, index) => (
                      <div className="template-step" key={item.id}>
                        <span className="step-index">{index + 1}</span>
                        <div>
                          <b>{item.title}</b>
                          <span>
                            {item.role} · {item.description}
                          </span>
                        </div>
                        <span className={"risk-pill " + item.risk}>
                          {item.risk === "high"
                            ? "高风险"
                            : item.risk === "medium"
                              ? "需确认"
                              : "只读"}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              <div className="panel scenario-launch">
                <div className="panel-head">
                  <div>
                    <h3>启动一次协作任务</h3>
                    <span className="panel-help">
                      任务会创建根实例，步骤完成前保留审计和证据。
                    </span>
                  </div>
                  <span className="chip success">审批门禁已开启</span>
                </div>
                <textarea
                  value={objective}
                  onChange={(event) => setObjective(event.target.value)}
                  placeholder="本次任务目标"
                />
                <input
                  value={context}
                  onChange={(event) => setContext(event.target.value)}
                  placeholder="可选上下文：环境、时间范围、服务或业务范围"
                />
                <button
                  className="primary"
                  onClick={start}
                  disabled={busy || !objective.trim()}
                >
                  <PlayCircle size={16} />
                  {busy ? "提交中…" : "启动场景"}
                </button>
              </div>
            </>
          ) : (
            <div className="empty panel">暂无场景模板</div>
          )}
        </div>
      </div>
      <div className="scenario-runs panel">
        <div className="panel-head">
          <h3>
            <ListChecks size={16} />
            最近运行实例
          </h3>
          <span className="chip">{runs.length} 条</span>
        </div>
        {runs.length === 0 ? (
          <div className="empty">启动一个场景后，运行记录会显示在这里。</div>
        ) : (
          runs.slice(0, 5).map((run) => (
            <button
              className={
                selectedRun?.run_id === run.run_id
                  ? "run-row active"
                  : "run-row"
              }
              key={run.run_id}
              onClick={() => setSelectedRun(run)}
            >
              <div className="run-status-dot" />
              <div className="row-main">
                <b>{run.scenario_name}</b>
                <span>{run.objective}</span>
              </div>
              <span className={scenarioStatusClass(run.status)}>
                {scenarioStatusLabel(run.status)}
              </span>
              <small>{run.run_id}</small>
              <ArrowRight size={15} />
            </button>
          ))
        )}
      </div>
      {selectedRun && (
        <div className="panel run-detail">
          <div className="panel-head">
            <div>
              <span className="eyebrow">运行实例 · {selectedRun.run_id}</span>
              <h3>{selectedRun.scenario_name}</h3>
            </div>
            <div className="run-actions">
              <span className={scenarioStatusClass(selectedRun.status)}>
                {scenarioStatusLabel(selectedRun.status)}
              </span>
              {selectedRun.status === "waiting_approval" ? (
                <button
                  className="primary"
                  onClick={() => void updateRun("approve")}
                  disabled={busy}
                >
                  <ShieldCheck size={16} />
                  批准当前动作
                </button>
              ) : (
                selectedRun.status !== "completed" && (
                  <button
                    className="secondary"
                    onClick={() => void updateRun("advance")}
                    disabled={busy}
                  >
                    <PlayCircle size={16} />
                    推进一步
                  </button>
                )
              )}
            </div>
          </div>
          <div className="run-progress">
            <div className="progress-track">
              <span
                style={{
                  width: `${Math.round((selectedRun.steps.filter((item) => item.status === "completed").length / Math.max(selectedRun.steps.length, 1)) * 100)}%`,
                }}
              />
            </div>
            <small>
              {
                selectedRun.steps.filter((item) => item.status === "completed")
                  .length
              }
              /{selectedRun.steps.length} 步完成 · 审批{" "}
              {selectedRun.approvals_granted}/{selectedRun.approvals_required}
            </small>
          </div>
          <div className="run-step-list">
            {selectedRun.steps.map((item) => (
              <div className="run-step" key={item.id}>
                <div className={"run-step-icon " + item.status}>
                  {item.status === "completed" ? (
                    <CircleCheck size={16} />
                  ) : item.status === "waiting_approval" ? (
                    <PauseCircle size={16} />
                  ) : (
                    <Clock3 size={16} />
                  )}
                </div>
                <div className="row-main">
                  <b>{item.title}</b>
                  <span>
                    {item.role} · {item.action}
                  </span>
                  {item.evidence.map((evidence) => (
                    <small key={evidence}>{evidence}</small>
                  ))}
                </div>
                <span className={scenarioStatusClass(item.status)}>
                  {scenarioStatusLabel(item.status)}
                </span>
              </div>
            ))}
          </div>
          <div className="audit-list">
            <b>审计轨迹</b>
            {selectedRun.audit.slice(-5).map((item) => (
              <span key={item}>{item}</span>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
function SQLOptimizerPage() {
  const [versions, setVersions] = useState<OptimizerVersion[]>([]);
  const [version, setVersion] = useState("8.5");
  const [mode, setMode] = useState<"simulate" | "live">("simulate");
  const [sql, setSql] = useState(
    "SELECT o.customer_id, SUM(o.amount) AS total_amount\nFROM sales.orders o\nWHERE o.created_at >= '2026-01-01'\nGROUP BY o.customer_id\nORDER BY total_amount DESC;",
  );
  const [ddl, setDdl] = useState(
    "CREATE TABLE orders (\n  order_id BIGINT PRIMARY KEY,\n  customer_id BIGINT,\n  created_at DATETIME,\n  amount DECIMAL(18,2)\n);",
  );
  const [endpoint, setEndpoint] = useState("");
  const [directoryOpen, setDirectoryOpen] = useState(false);
  const [directoryPath, setDirectoryPath] = useState(
    "/workspace/data/sql-optimizer",
  );
  const [bundle, setBundle] = useState<{
    files: string[];
    sql_items: { name: string; sql: string }[];
    ddl: string;
  } | null>(null);
  const [result, setResult] = useState<OptimizeResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  useEffect(() => {
    void api<OptimizerVersion[]>("/aiops/sql-optimizer/versions")
      .then(setVersions)
      .catch((e) => setError(e instanceof Error ? e.message : "版本加载失败"));
  }, []);
  const analyze = async () => {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const data = await api<OptimizeResult>("/aiops/sql-optimizer/analyze", {
        method: "POST",
        body: JSON.stringify({
          sql,
          ddl,
          tidb_version: version,
          plan_mode: mode,
          mcp_endpoint: mode === "live" ? endpoint || undefined : undefined,
        }),
      });
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "SQL 优化失败");
    } finally {
      setBusy(false);
    }
  };
  const upload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;
    const body = new FormData();
    files.forEach((file) => body.append("files", file));
    try {
      const data = await api<{
        files: string[];
        sql_items: { name: string; sql: string }[];
        ddl: string;
      }>("/aiops/sql-optimizer/inputs/upload", {
        method: "POST",
        headers: {},
        body,
      });
      setBundle(data);
      if (data.sql_items[0]) setSql(data.sql_items[0].sql);
      if (data.ddl) setDdl(data.ddl);
      setMessage("已读取 " + data.files.length + " 个 SQL/DDL 文件");
    } catch (e) {
      setError(e instanceof Error ? e.message : "SQL 文件读取失败");
    }
  };
  const scan = async () => {
    if (!directoryPath.trim()) return;
    try {
      const data = await api<{
        files: string[];
        sql_items: { name: string; sql: string }[];
        ddl: string;
      }>("/aiops/sql-optimizer/inputs/local-directory", {
        method: "POST",
        body: JSON.stringify({ path: directoryPath.trim() }),
      });
      setBundle(data);
      if (data.sql_items[0]) setSql(data.sql_items[0].sql);
      if (data.ddl) setDdl(data.ddl);
      setMessage("已读取目录中的 " + data.files.length + " 个文件");
      setDirectoryOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "目录读取失败");
    }
  };
  const profile = versions.find((item) => item.minor === version);
  return (
    <section className="content sql-optimizer-page">
      <div className="section-head">
        <div>
          <span className="eyebrow">
            AIOps · TiDB Planner · SQLAdvisor 方法
          </span>
          <h1>SQL 优化</h1>
          <p className="section-subtitle">
            输入 SQL 与表结构，按 TiDB
            版本生成可解释的索引、改写和执行计划建议。
          </p>
        </div>
        <div className="sql-actions">
          <label className="primary file-button">
            <UploadCloud size={16} />
            读取 SQL/DDL
            <input
              type="file"
              accept=".sql,.ddl,.txt"
              multiple
              onChange={upload}
            />
          </label>
          <button className="secondary" onClick={() => setDirectoryOpen(true)}>
            <FileCode2 size={16} />
            读取受控目录
          </button>
        </div>
      </div>
      <div className="optimizer-toolbar">
        <div className="toolbar-field">
          <label>TiDB 版本</label>
          <select value={version} onChange={(e) => setVersion(e.target.value)}>
            {versions.map((item) => (
              <option key={item.minor} value={item.minor}>
                {item.label}
              </option>
            ))}
          </select>
        </div>
        <div className="mode-toggle">
          <label>计划模式</label>
          <div>
            <button
              className={mode === "simulate" ? "mode active" : "mode"}
              onClick={() => setMode("simulate")}
            >
              <GitCompareArrows size={15} />
              版本模拟
            </button>
            <button
              className={mode === "live" ? "mode active" : "mode"}
              onClick={() => setMode("live")}
            >
              <ShieldCheck size={15} />
              真实 EXPLAIN
            </button>
          </div>
        </div>
        {mode === "live" && (
          <div className="toolbar-field endpoint-field">
            <label>MCP endpoint</label>
            <input
              value={endpoint}
              onChange={(e) => setEndpoint(e.target.value)}
              placeholder="已采集连接可留空"
            />
          </div>
        )}
        <button
          className="primary optimize-button"
          onClick={analyze}
          disabled={busy || !sql.trim()}
        >
          {busy ? (
            <>
              <Clock3 size={16} />
              分析中…
            </>
          ) : (
            <>
              <WandSparkles size={16} />
              生成优化建议
            </>
          )}
        </button>
      </div>
      {profile && (
        <div className="profile-strip">
          <b>{profile.label}</b>
          <span>{profile.features.slice(0, 3).join(" · ")}</span>
          <a href={profile.release_notes} target="_blank" rel="noreferrer">
            查看 Release Notes
          </a>
        </div>
      )}
      {message && <div className="notice">{message}</div>}
      {error && <div className="error-banner">{error}</div>}
      <div className="sql-editor-grid">
        <div className="editor-panel panel">
          <div className="panel-head">
            <h3>
              <FileCode2 size={16} /> SQL 输入
            </h3>
            <span className="chip">只读分析</span>
          </div>
          <textarea
            className="code-editor"
            value={sql}
            onChange={(e) => setSql(e.target.value)}
            spellCheck={false}
          />
        </div>
        <div className="editor-panel panel">
          <div className="panel-head">
            <h3>
              <Database size={16} /> 表结构 / DDL
            </h3>
            <span className="chip">可选</span>
          </div>
          <textarea
            className="code-editor"
            value={ddl}
            onChange={(e) => setDdl(e.target.value)}
            spellCheck={false}
          />
        </div>
      </div>
      {bundle && (
        <div className="input-bundle panel">
          <b>已加载文件</b>
          {bundle.files.map((file) => (
            <span className="chip" key={file}>
              {file}
            </span>
          ))}
        </div>
      )}
      {result && <OptimizerResult result={result} />}
      {directoryOpen && (
        <div
          className="dialog-backdrop"
          role="presentation"
          onMouseDown={() => setDirectoryOpen(false)}
        >
          <div
            className="directory-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="directory-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="dialog-title">
              <div>
                <span className="eyebrow">本地部署目录</span>
                <h3 id="directory-title">读取 SQL / DDL 目录</h3>
              </div>
              <button
                className="icon-button"
                onClick={() => setDirectoryOpen(false)}
                aria-label="关闭"
              >
                <X size={18} />
              </button>
            </div>
            <label htmlFor="optimizer-directory">受控目录路径</label>
            <input
              id="optimizer-directory"
              autoFocus
              value={directoryPath}
              onChange={(event) => setDirectoryPath(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") void scan();
              }}
            />
            <div className="dialog-actions">
              <button
                className="secondary"
                onClick={() => setDirectoryOpen(false)}
              >
                取消
              </button>
              <button
                className="primary"
                onClick={() => void scan()}
                disabled={!directoryPath.trim()}
              >
                <FileCode2 size={16} />
                读取目录
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
function OptimizerResult({ result }: { result: OptimizeResult }) {
  return (
    <div className="optimizer-result">
      <div className="optimizer-summary panel">
        <div className="panel-head">
          <div>
            <span className="eyebrow">分析结果 · {result.analysis_id}</span>
            <h2>{result.summary}</h2>
          </div>
          <span
            className={
              result.optimizer_mode === "live"
                ? "chip success"
                : "chip simulated"
            }
          >
            {result.optimizer_mode === "live" ? "真实 EXPLAIN" : "版本模拟"}
          </span>
        </div>
        <div className="result-meta">
          <span>目标版本 {result.requested_version}</span>
          <span>规则包 {result.profile_version}</span>
          <span>置信度 {result.confidence}</span>
          {result.actual_tidb_version && (
            <span>集群 {result.actual_tidb_version}</span>
          )}
        </div>
        {result.assumptions.length > 0 && (
          <div className="assumptions">
            <CircleAlert size={16} />
            {result.assumptions.map((item) => (
              <span key={item}>{item}</span>
            ))}
          </div>
        )}
      </div>
      <div className="optimizer-columns">
        <div className="plan-panel panel">
          <div className="panel-head">
            <h3>执行计划</h3>
            <span className="chip">{result.plan.length} 节点</span>
          </div>
          {result.plan.map((node) => (
            <div className="plan-node" key={node.id + "-" + node.access_object}>
              <div className={"plan-risk " + node.risk} />
              <div className="row-main">
                <b>{node.id}</b>
                <span>
                  {node.task} · {node.access_object || "root"} · estRows{" "}
                  {node.est_rows}
                </span>
                <small>{node.operator_info}</small>
              </div>
            </div>
          ))}
        </div>
        <div className="recommendation-panel panel">
          <div className="panel-head">
            <h3>优化建议</h3>
            <span className="chip success">
              {result.recommendations.length} 条
            </span>
          </div>
          {result.recommendations.map((item) => (
            <div className="recommendation" key={item.id}>
              <div className={"recommendation-icon " + item.severity}>
                {item.severity === "critical" ? (
                  <CircleAlert size={16} />
                ) : (
                  <WandSparkles size={16} />
                )}
              </div>
              <div className="row-main">
                <b>{item.title}</b>
                <span>{item.rationale}</span>
                <code>{item.action}</code>
                {item.evidence.length > 0 && (
                  <small>证据：{item.evidence.join(" · ")}</small>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="feature-panel panel">
        <div className="panel-head">
          <h3>版本画像与依据</h3>
          <span className="chip">{result.sources.length} sources</span>
        </div>
        <div className="feature-list">
          {result.version_features.map((item) => (
            <span key={item}>{item}</span>
          ))}
        </div>
        <div className="source-list">
          {result.sources.map((source) => (
            <a
              href={source.url}
              target="_blank"
              rel="noreferrer"
              key={source.url}
            >
              {source.label} · {source.ref}
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}

declare global {
  interface Window {
    __aegisRoot?: ReturnType<typeof createRoot>;
  }
}

const rootElement = document.getElementById("root")!;
const root = window.__aegisRoot ?? createRoot(rootElement);
window.__aegisRoot = root;
root.render(<App />);
