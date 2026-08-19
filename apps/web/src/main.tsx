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
  ChevronDown,
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
  Bell,
  Building2,
  Cable,
  CloudCog,
  Gauge,
  LockKeyhole,
  Save,
  SlidersHorizontal,
  PlugZap,
  Server,
  FileSpreadsheet,
  MonitorUp,
  PanelsTopLeft,
  Trash2,
  Eye,
  EyeOff,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import "./styles.css";
import "./optimizer.css";
import "./scenarios.css";
import "./knowledge.css";
import "./capabilities.css";
import "./polish.css";
import "./chatbi.css";
import "./models.css";
import "./agents.css";
import "./datasources.css";
import "./relationships.css";
import "./login.css";
import "./operation.css";
import "./shell.css";

type Page =
  | "workbench"
  | "capabilities"
  | "query"
  | "incidents"
  | "assets"
  | "catalog"
  | "sql-optimizer"
  | "scenarios"
  | "knowledge"
  | "models"
  | "agents"
  | "datasources"
  | "settings";
type QueryModule = "chatbi" | "dashboard";
const ROUTABLE_PAGES: Page[] = [
  "workbench",
  "capabilities",
  "query",
  "incidents",
  "assets",
  "catalog",
  "sql-optimizer",
  "scenarios",
  "knowledge",
  "models",
  "agents",
  "datasources",
  "settings",
];
function pageFromLocation(): Page {
  const candidate = window.location.hash.replace(/^#\/?/, "") as Page;
  return ROUTABLE_PAGES.includes(candidate) ? candidate : "workbench";
}
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
type RelationshipNode = {
  id: string;
  label: string;
  kind: "schema" | "table" | "column";
  parent_id?: string;
  schema_name?: string;
  table_name?: string;
  data_type?: string;
  comment?: string;
};
type RelationshipEdge = {
  id: string;
  source: string;
  target: string;
  kind: string;
  level: "structure" | "table" | "field";
  source_type: "metadata" | "sql" | "structure";
  observation_count: number;
  confidence: number;
  first_seen_at: string;
  last_seen_at: string;
};
type SqlObservation = {
  id: string;
  digest: string;
  sql_preview: string;
  source: string;
  execution_count: number;
  relationship_ids: string[];
  first_seen_at: string;
  last_seen_at: string;
};
type RelationshipSnapshot = {
  datasource_id: string;
  datasource_name: string;
  database: string;
  source: string;
  schemas: Catalog["schemas"];
  nodes: RelationshipNode[];
  edges: RelationshipEdge[];
  sql_observations: SqlObservation[];
  collected_at: string;
};
type SqlCollectorStatus = {
  datasource_id: string;
  enabled: boolean;
  interval_seconds: number;
  last_collected_at?: string;
  last_error?: string;
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
type IncidentRecord = {
  id: string;
  title: string;
  severity: string;
  status: string;
  service: string;
  started_at: string;
  summary: string;
  recommended_action: string;
};
type AssetRecord = {
  id: string;
  name: string;
  type: string;
  owner: string;
  status: string;
  database: string;
  description: string;
  columns: { name: string; type: string; sensitivity?: string }[];
  upstream: string[];
  downstream: string[];
  row_count?: number;
  quality_score?: number;
};
type WorkbenchSummary = {
  metrics: {
    open_incidents: number;
    critical_incidents: number;
    managed_assets: number;
    query_success_rate: number;
  };
  incidents: IncidentRecord[];
  recent_queries: QueryResult[];
};
type WorkspaceSettings = {
  workspace_name: string;
  language: string;
  timezone: string;
  data_retention_days: number;
  tidb_mcp_endpoint: string;
  allowed_data_root: string;
  readonly_sql: boolean;
  operation_audit: boolean;
  high_risk_approval: boolean;
  local_models_only: boolean;
  updated_at: string;
};
type OperationPhase = "IDLE" | "PLANNING" | "VALIDATING" | "EXECUTING" | "COMPLETED" | "FAILED";
type OperationProgressState = {
  phase: OperationPhase;
  detail: string;
  progress: number;
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
type DataSourceRecord = {
  id: string;
  name: string;
  kind: "mysql" | "tidb" | "csv";
  status: "ready" | "unverified" | "error";
  host?: string;
  port?: number;
  database?: string;
  username?: string;
  dataset_id?: string;
  table_count: number;
  row_count?: number;
  last_error?: string;
  created_at: string;
  last_tested_at?: string;
};
type DashboardReport = {
  id: string;
  operation_id: string;
  datasource_id: string;
  datasource_name: string;
  title: string;
  question: string;
  chart: { type: string; title: string; option?: EChartsOption };
  columns: string[];
  rows: unknown[][];
  accepted_by: string;
  created_at: string;
};
type ModelProvider = {
  id: "openai" | "deepseek" | "qwen" | "zhipu" | "moonshot" | "ollama" | "vllm" | "custom";
  name: string;
  deployment: "public" | "private";
  protocol: string;
  default_base_url: string;
  model_placeholder: string;
  api_key_required: boolean;
  description: string;
};
type ModelConnection = {
  id: string;
  name: string;
  provider: ModelProvider["id"];
  provider_name: string;
  deployment: "public" | "private";
  protocol: string;
  base_url: string;
  model: string;
  model_source: "manual" | "auto" | "gateway-default" | "unspecified";
  status: "ready" | "unverified" | "error";
  is_default: boolean;
  has_credential: boolean;
  capabilities: string[];
  last_error?: string;
  last_tested_at?: string;
  created_at: string;
};
type ModelReadiness = {
  ready: boolean;
  source: "registry" | "environment" | "none";
  connection_id?: string;
  model?: string;
};
type AgentTool = {
  id: string;
  feature_id: string;
  name: string;
  api_ref: string;
  risk: "read" | "propose" | "approval";
};
type AgentTemplate = {
  id: string;
  module_id: string;
  module_name: string;
  name: string;
  summary: string;
  owner_role: string;
  domain: ProductModule["domain"];
  target_page?: Page;
  capabilities: string[];
  tools: AgentTool[];
  approval_policy: "read_only" | "human_approval";
  system_prompt: string;
};
type ModuleAgent = {
  id: string;
  template_id: string;
  module_id: string;
  module_name: string;
  name: string;
  summary: string;
  status: "ready" | "disabled" | "error";
  enabled: boolean;
  model_source: "registry" | "environment";
  model_connection_id?: string;
  model_connection_name: string;
  model: string;
  capabilities: string[];
  tools: AgentTool[];
  approval_policy: "read_only" | "human_approval";
  system_prompt: string;
  target_page?: Page;
  created_at: string;
  updated_at: string;
  last_tested_at?: string;
  last_invoked_at?: string;
  last_error?: string;
};
type AgentProvisionResult = {
  requested: number;
  created: ModuleAgent[];
  existing: ModuleAgent[];
  model_connection_name: string;
};
type AgentTestResult = {
  agent_id: string;
  passed: boolean;
  status: ModuleAgent["status"];
  checks: { key: string; label: string; passed: boolean; detail: string }[];
  tested_at: string;
};
type AgentInvokeResult = {
  run_id: string;
  agent_id: string;
  answer: string;
  execution_mode: "advisory";
  approval_required: boolean;
  available_tools: string[];
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
  retrieval_strategy: "lexical" | "semantic" | "hybrid";
  chunking_strategy: "recursive" | "markdown";
  splitter_provider: string;
  chunk_size: number;
  chunk_overlap: number;
  document_count: number;
  chunk_count: number;
  created_at: string;
  updated_at: string;
};
type KnowledgeIndexMode = {
  id: "lexical" | "semantic" | "hybrid";
  name: string;
  description: string;
  provider: string;
  recommended: boolean;
};
type KnowledgeChunkingMode = {
  id: "recursive" | "markdown";
  name: string;
  description: string;
  provider: string;
  recommended: boolean;
};
type KnowledgeDocument = {
  id: string;
  title: string;
  source_type: "text" | "upload" | "local_directory" | "connector";
  source_uri: string;
  mime_type: string;
  content_size: number;
  status: "ready" | "processing" | "failed";
  enabled: boolean;
  chunk_count: number;
  tags: string[];
  updated_at: string;
  indexed_at?: string;
  error_message: string;
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
  generation_mode: "model" | "extractive" | "retrieval-only" | "none";
  candidate_count: number;
  score_threshold: number;
  retrieval_latency_ms: number;
  citations: {
    rank: number;
    document_id: string;
    document_title: string;
    chunk_id: string;
    score: number;
    excerpt: string;
    source_uri: string;
    tags: string[];
    position: number;
    matched_terms: string[];
    retrieval_reason: string;
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
const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:18082/api/v1").replace(
  /\/$/,
  "",
);
async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const isMultipart = typeof FormData !== "undefined" && init?.body instanceof FormData;
  const headers = isMultipart
    ? { ...(init?.headers || {}) }
    : { "Content-Type": "application/json", ...(init?.headers || {}) };
  const response = await fetch(API_BASE + path, { ...init, headers });
  if (!response.ok) throw new Error((await response.text()) || "API " + response.status);
  return response.json() as Promise<T>;
}
function Login({
  onLogin,
  error,
  busy,
}: {
  onLogin: (email: string, password: string) => void;
  error?: string;
  busy?: boolean;
}) {
  return (
    <div className="login">
      <div className="login-shell">
        <section className="login-brand-panel">
          <div className="login-brand-lockup">
            <div className="brand-mark">A</div>
            <div>
              <b>Aegis AI</b>
              <span>Enterprise Control Plane</span>
            </div>
          </div>
          <div className="login-brand-copy">
            <span className="login-kicker">企业 AI 控制平面</span>
            <h1>一个入口，协同数据、知识与运维。</h1>
            <p>以可追溯的分析和受控的执行，让企业场景真正进入日常工作流。</p>
          </div>
          <div className="login-capability-list">
            <div>
              <MessageSquare size={18} />
              <span>
                <b>智能分析</b>
                <small>自然语言问数与可解释 SQL</small>
              </span>
            </div>
            <div>
              <BookOpen size={18} />
              <span>
                <b>企业知识</b>
                <small>受控检索、引用与知识治理</small>
              </span>
            </div>
            <div>
              <Activity size={18} />
              <span>
                <b>运维协同</b>
                <small>事件诊断、审批与场景编排</small>
              </span>
            </div>
          </div>
          <div className="login-brand-foot">
            <ShieldCheck size={16} /> 本地优先 · 支持完全离线部署
          </div>
        </section>
        <section className="login-form-panel">
          <form
            className="login-card"
            onSubmit={(event) => {
              event.preventDefault();
              const data = new FormData(event.currentTarget);
              onLogin(String(data.get("email") || ""), String(data.get("password") || ""));
            }}
          >
            <div className="login-form-head">
              <span className="login-kicker">欢迎回来</span>
              <h2>登录工作台</h2>
              <p>使用企业账号进入当前工作空间。</p>
            </div>
            <label htmlFor="login-email">企业账号</label>
            <input
              id="login-email"
              name="email"
              type="email"
              autoComplete="username"
              placeholder="name@company.com"
              defaultValue="admin@acme.com"
              required
            />
            <label htmlFor="login-password">密码</label>
            <input
              id="login-password"
              name="password"
              type="password"
              autoComplete="current-password"
              defaultValue="12345678"
              required
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  event.currentTarget.form?.requestSubmit();
                }
              }}
            />
            {error && <div className="form-error">{error}</div>}
            <div className="login-environment">
              <span className="status-dot" />
              <span>
                <b>本地演示环境</b>
                <small>数据不会发送到外部服务</small>
              </span>
            </div>
            <button className="primary wide" type="submit" disabled={busy}>
              {busy ? "正在登录…" : "登录工作台"} <ArrowUpRight size={16} />
            </button>
            <small className="login-help">登录即表示你已同意企业安全与审计策略</small>
          </form>
        </section>
      </div>
    </div>
  );
}
function App() {
  const [logged, setLogged] = useState(false);
  const [loginBusy, setLoginBusy] = useState(false);
  const [loginError, setLoginError] = useState("");
  const [workspaceName, setWorkspaceName] = useState("本地演示空间");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [page, setPage] = useState<Page>(pageFromLocation);
  const [notice, setNotice] = useState("");
  const [focusCapabilitySearch, setFocusCapabilitySearch] = useState(false);
  const [querySeed, setQuerySeed] = useState("");
  const [queryModule, setQueryModule] = useState<QueryModule>("chatbi");
  const [queryExpanded, setQueryExpanded] = useState(() => page === "query");
  const [modelOnboarding, setModelOnboarding] = useState(false);
  type NavItem = [Page, string, React.ComponentType<{ size?: number }>];
  type NavGroup = [string, NavItem[]];
  const navGroups: NavGroup[] = [
    [
      "总览",
      [
        ["workbench", "工作台", LayoutDashboard],
        ["capabilities", "功能中心", ListChecks],
      ],
    ],
    [
      "数据智能",
      [
        ["query", "智能问数", MessageSquare],
        ["knowledge", "知识库", BookOpen],
        ["assets", "数据资产", Database],
        ["catalog", "数据关系", Network],
      ],
    ],
    [
      "运维协同",
      [
        ["incidents", "AIOps 事件", Activity],
        ["sql-optimizer", "SQL 优化", WandSparkles],
        ["scenarios", "场景中心", Workflow],
      ],
    ],
    [
      "平台管理",
      [
        ["models", "模型接入", CloudCog],
        ["agents", "Agent 中心", Bot],
        ["datasources", "数据源管理", Database],
      ],
    ],
  ];
  const nav = navGroups.flatMap(([, items]) => items);
  const activeGroup = navGroups.find(([, items]) => items.some(([id]) => id === page))?.[0];
  const pageTitle =
    page === "settings"
      ? "系统设置"
      : page === "query"
        ? queryModule === "dashboard"
          ? "大屏展示"
          : "ChatBI"
        : nav.find((item) => item[0] === page)?.[1];
  const navigatePage = (next: Page) => {
    setPage(next);
    const nextHash = `#/${next}`;
    if (window.location.hash !== nextHash) window.history.pushState({ page: next }, "", nextHash);
  };
  const openQuery = (question = "") => {
    setQuerySeed(question);
    setQueryModule("chatbi");
    setQueryExpanded(true);
    navigatePage("query");
  };
  const openQueryModule = (module: QueryModule) => {
    setQuerySeed("");
    setQueryModule(module);
    setQueryExpanded(true);
    navigatePage("query");
  };
  useEffect(() => {
    if (!window.location.hash) window.history.replaceState({ page }, "", `#/${page}`);
    const handleHistory = () => setPage(pageFromLocation());
    window.addEventListener("popstate", handleHistory);
    return () => window.removeEventListener("popstate", handleHistory);
  }, []);
  useEffect(() => {
    if (page !== "capabilities") setFocusCapabilitySearch(false);
  }, [page]);
  useEffect(() => {
    setQueryExpanded(page === "query");
  }, [page]);
  useEffect(() => {
    if (!logged) return;
    void api<WorkspaceSettings>("/settings")
      .then((item) => setWorkspaceName(item.workspace_name))
      .catch(() => undefined);
  }, [logged]);
  const handleLogin = async (email: string, password: string) => {
    setLoginBusy(true);
    setLoginError("");
    try {
      const session = await api<{ session_id: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      localStorage.setItem("aegis_session_id", session.session_id);
      setLogged(true);
      const readiness = await api<ModelReadiness>("/models/readiness");
      if (!readiness.ready) {
        setModelOnboarding(true);
        navigatePage("models");
      } else {
        setModelOnboarding(false);
        navigatePage(page);
      }
    } catch (reason) {
      setLoginError(reason instanceof Error ? reason.message : "登录失败，请检查账号和密码");
    } finally {
      setLoginBusy(false);
    }
  };
  if (!logged)
    return (
      <Login
        onLogin={(email, password) => void handleLogin(email, password)}
        error={loginError}
        busy={loginBusy}
      />
    );
  const runtimeEnvironment = String(import.meta.env.VITE_ENV || "development");
  const isProduction = runtimeEnvironment === "production";
  return (
    <div className={sidebarCollapsed ? "app sidebar-collapsed" : "app"}>
      <aside className="app-sidebar">
        <div className="logo">
          <span>A</span>
          <div className="logo-copy">
            <b>Aegis AI</b>
            <small>Control Plane</small>
          </div>
        </div>
        <div className="workspace-switch">
          <Building2 size={17} />
          <span className="workspace-copy">
            <small>当前工作区</small>
            <b>{workspaceName}</b>
          </span>
        </div>
        <nav className="sidebar-nav" aria-label="产品导航">
          {navGroups.map(([group, items]) => (
            <div className="nav-group" key={group}>
              <span className="nav-section">{group}</span>
              {items.map(([id, label, Icon]) =>
                id === "query" ? (
                  <React.Fragment key={id}>
                    <button
                      className={page === id ? "nav nav-parent active" : "nav nav-parent"}
                      aria-label={label}
                      aria-expanded={queryExpanded}
                      aria-controls="query-subnav"
                      title={label}
                      onClick={() => {
                        setQueryExpanded((expanded) => !expanded);
                        if (page !== "query") openQuery();
                      }}
                    >
                      <Icon size={18} />
                      <span className="nav-label">{label}</span>
                      <ChevronDown className="nav-chevron" size={15} aria-hidden="true" />
                    </button>
                    {queryExpanded && (
                      <div className="nav-subgroup" id="query-subnav">
                        <button
                          className={
                            page === "query" && queryModule === "chatbi"
                              ? "nav nav-sub active"
                              : "nav nav-sub"
                          }
                          aria-label="ChatBI"
                          aria-current={
                            page === "query" && queryModule === "chatbi" ? "page" : undefined
                          }
                          onClick={() => openQueryModule("chatbi")}
                        >
                          <MessageSquare size={16} />
                          <span className="nav-label">ChatBI</span>
                        </button>
                        <button
                          className={
                            page === "query" && queryModule === "dashboard"
                              ? "nav nav-sub active"
                              : "nav nav-sub"
                          }
                          aria-label="大屏展示"
                          aria-current={
                            page === "query" && queryModule === "dashboard" ? "page" : undefined
                          }
                          onClick={() => openQueryModule("dashboard")}
                        >
                          <MonitorUp size={16} />
                          <span className="nav-label">大屏展示</span>
                        </button>
                      </div>
                    )}
                  </React.Fragment>
                ) : (
                  <button
                    className={page === id ? "nav active" : "nav"}
                    aria-label={label}
                    aria-current={page === id ? "page" : undefined}
                    title={label}
                    onClick={() => navigatePage(id)}
                    key={id}
                  >
                    <Icon size={18} />
                    <span className="nav-label">{label}</span>
                  </button>
                ),
              )}
            </div>
          ))}
        </nav>
        <div className="aside-bottom">
          <button
            className={page === "settings" ? "nav active" : "nav"}
            aria-label="系统设置"
            aria-current={page === "settings" ? "page" : undefined}
            title="系统设置"
            onClick={() => navigatePage("settings")}
          >
            <Settings size={18} />
            <span className="nav-label">系统设置</span>
          </button>
          <button
            className="nav"
            aria-label="退出登录"
            title="退出登录"
            onClick={() => {
              const sessionId = localStorage.getItem("aegis_session_id");
              void api("/auth/logout", {
                method: "POST",
                body: JSON.stringify({ session_id: sessionId }),
              }).catch(() => undefined);
              setLogged(false);
              localStorage.removeItem("aegis_session_id");
              setModelOnboarding(false);
              navigatePage("workbench");
            }}
          >
            <LogOut size={18} />
            <span className="nav-label">退出登录</span>
          </button>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div className="page-context">
            <button
              className="topbar-icon sidebar-toggle"
              aria-label={sidebarCollapsed ? "展开侧栏" : "收起侧栏"}
              title={sidebarCollapsed ? "展开侧栏" : "收起侧栏"}
              onClick={() => setSidebarCollapsed((current) => !current)}
            >
              {sidebarCollapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
            </button>
            <span className="eyebrow">{activeGroup || "平台管理"}</span>
            <h2>{pageTitle}</h2>
          </div>
          <button
            className="global-search"
            onClick={() => {
              setFocusCapabilitySearch(true);
              navigatePage("capabilities");
            }}
          >
            <Search size={16} />
            <span>搜索功能、场景或数据</span>
          </button>
          <div className="user topbar-actions">
            <span className={isProduction ? "environment-badge production" : "environment-badge"}>
              <span className="status-dot" />
              {isProduction ? "生产环境" : "开发环境"}
            </span>
            <button
              className="topbar-icon"
              aria-label="通知"
              title="通知"
              onClick={() => setNotice("当前没有未读通知")}
            >
              <Bell size={18} />
            </button>
            <div className="account-chip">
              <div className="avatar">林</div>
              <span>
                <b>林工</b>
                <small>平台管理员</small>
              </span>
            </div>
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
        {page === "workbench" && <Workbench setPage={navigatePage} openQuery={openQuery} />}{" "}
        {page === "capabilities" && (
          <CapabilityCenter setPage={navigatePage} focusSearch={focusCapabilitySearch} />
        )}{" "}
        {page === "query" && (
          <QueryV2
            initialQuestion={querySeed}
            module={queryModule}
            onModuleChange={setQueryModule}
          />
        )}{" "}
        {page === "incidents" && <Incidents setPage={navigatePage} />}{" "}
        {page === "scenarios" && <ScenarioCenter />} {page === "knowledge" && <KnowledgeBasePage />}{" "}
        {page === "models" && (
          <ModelConnectionsPage
            onboarding={modelOnboarding}
            onComplete={() => setModelOnboarding(false)}
            enterWorkspace={() => navigatePage("workbench")}
            openAgents={() => navigatePage("agents")}
          />
        )}{" "}
        {page === "agents" && <AgentCenterPage setPage={navigatePage} />}{" "}
        {page === "datasources" && <DataSourceManagementPage setPage={navigatePage} />}{" "}
        {page === "sql-optimizer" && <SQLOptimizerPage />}{" "}
        {page === "assets" && <AssetsV2 setPage={navigatePage} />}{" "}
        {page === "catalog" && <CatalogPage setPage={navigatePage} />}
        {page === "settings" && <SettingsPage setPage={navigatePage} />}
      </main>
    </div>
  );
}
function CapabilityCenter({
  setPage,
  focusSearch = false,
}: {
  setPage: (page: Page) => void;
  focusSearch?: boolean;
}) {
  const [modules, setModules] = useState<ProductModule[]>([]);
  const [selectedModuleId, setSelectedModuleId] = useState("");
  const [selectedFeatureId, setSelectedFeatureId] = useState("");
  const [search, setSearch] = useState("");
  const [role, setRole] = useState("all");
  const [state, setState] = useState<"all" | ProductFeature["delivery_state"]>("all");
  const [error, setError] = useState("");
  const searchRef = useRef<HTMLInputElement>(null);
  const featuresRef = useRef<HTMLDivElement>(null);
  const detailRef = useRef<HTMLDivElement>(null);
  const advanceOnMobile = (target: React.RefObject<HTMLDivElement | null>) => {
    if (window.matchMedia("(max-width: 700px)").matches) {
      window.requestAnimationFrame(() =>
        target.current?.scrollIntoView({ behavior: "smooth", block: "start" }),
      );
    }
  };

  useEffect(() => {
    api<ProductModule[]>("/product/modules")
      .then((items) => {
        setModules(items);
        setSelectedModuleId(items[0]?.id || "");
        setSelectedFeatureId(items[0]?.features[0]?.id || "");
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : "功能目录加载失败"));
  }, []);
  useEffect(() => {
    if (focusSearch) searchRef.current?.focus();
  }, [focusSearch]);

  const roles = useMemo(
    () =>
      Array.from(
        new Set(modules.flatMap((module) => module.features.flatMap((item) => item.roles))),
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
    visibleModules.find((module) => module.id === selectedModuleId) || visibleModules[0];
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
          <p className="section-subtitle">按当前职责选择可执行功能，已接入页面可直接进入。</p>
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
        <Metric label="演示闭环" value={String(counts.demo)} hint="等待真实 Adapter" tone="blue" />
        <Metric label="生产接入" value={String(counts.planned)} hint="按架构计划实施" tone="red" />
      </div>
      <div className="capability-toolbar">
        <div className="capability-search">
          <Search size={17} />
          <input
            ref={searchRef}
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
            setState(event.target.value as "all" | ProductFeature["delivery_state"])
          }
          aria-label="按交付状态筛选"
        >
          <option value="all">全部状态</option>
          <option value="available">可使用</option>
          <option value="demo">演示闭环</option>
          <option value="planned">待生产接入</option>
        </select>
        {(search || role !== "all" || state !== "all") && (
          <button
            className="secondary capability-reset"
            onClick={() => {
              setSearch("");
              setRole("all");
              setState("all");
              searchRef.current?.focus();
            }}
          >
            <X size={14} />
            清除筛选
          </button>
        )}
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
                selectedModule?.id === module.id ? "capability-module active" : "capability-module"
              }
              onClick={() => {
                setSelectedModuleId(module.id);
                setSelectedFeatureId(module.features[0]?.id || "");
                advanceOnMobile(featuresRef);
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
        <div className="panel capability-features" ref={featuresRef}>
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
                selectedFeature?.id === item.id ? "capability-feature active" : "capability-feature"
              }
              onClick={() => {
                setSelectedFeatureId(item.id);
                advanceOnMobile(detailRef);
              }}
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
        <div className="panel capability-detail" ref={detailRef}>
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
              <CapabilityFact title="安全门禁" items={selectedFeature.guardrails} />
              {!!selectedFeature.scenario_ids.length && (
                <CapabilityFact title="关联场景" items={selectedFeature.scenario_ids} />
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
                  selectedFeature.delivery_state === "planned" || !selectedFeature.target_page
                }
                onClick={() => selectedFeature.target_page && setPage(selectedFeature.target_page)}
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
function Workbench({
  setPage,
  openQuery,
}: {
  setPage: (p: Page) => void;
  openQuery: (question?: string) => void;
}) {
  const [summary, setSummary] = useState<WorkbenchSummary | null>(null);
  const [error, setError] = useState("");
  const today = new Intl.DateTimeFormat("zh-CN", {
    month: "long",
    day: "numeric",
    weekday: "long",
  }).format(new Date());
  useEffect(() => {
    void api<WorkbenchSummary>("/workbench/summary")
      .then(setSummary)
      .catch((reason) => setError(reason instanceof Error ? reason.message : "工作台加载失败"));
  }, []);
  const metrics = summary?.metrics;
  return (
    <section className="content workbench-page">
      <div className="welcome workbench-hero">
        <div className="welcome-copy">
          <span className="eyebrow">{today}</span>
          <h1>早上好，林工</h1>
          <p>今日重点已按风险和业务影响排序，可以从待办直接进入处置。</p>
          <div className="hero-signals">
            <span>
              <span className="status-dot" /> 核心服务正常
            </span>
            <span>
              <ShieldCheck size={14} /> 只读安全策略已启用
            </span>
            <span>
              <Gauge size={14} /> 数据更新于 2 分钟前
            </span>
          </div>
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
        <Metric
          label="待处理事件"
          value={String(metrics?.open_incidents ?? "-")}
          hint={`${metrics?.critical_incidents ?? 0} 个 P1 事件`}
          tone="red"
        />
        <Metric
          label="已管理资产"
          value={String(metrics?.managed_assets ?? "-")}
          hint="来自治理目录"
          tone="green"
        />
        <Metric
          label="问数成功率"
          value={metrics ? `${metrics.query_success_rate}%` : "-"}
          hint="最近运行统计"
          tone="blue"
        />
        <Metric
          label="平台状态"
          value={summary ? "正常" : "加载中"}
          hint="控制面 API"
          tone="purple"
        />
      </div>
      {error && <div className="error-banner">{error}</div>}
      <div className="workbench-section-label">
        <div>
          <span className="eyebrow">快捷入口</span>
          <h2>开始一项工作</h2>
        </div>
        <button className="text-btn" onClick={() => setPage("capabilities")}>
          浏览全部 63 项功能 <ChevronRight size={14} />
        </button>
      </div>
      <div className="workbench-tasks" aria-label="常用工作">
        {[
          ["query", "数据分析", "经营数据分析", "自然语言转 SQL 并生成图表", MessageSquare],
          [
            "knowledge",
            "知识检索",
            "查询企业知识",
            "从制度、手册和案例中获取有引用的回答",
            BookOpen,
          ],
          [
            "sql-optimizer",
            "性能诊断",
            "诊断 SQL 性能",
            "按 TiDB 版本分析执行计划与索引建议",
            WandSparkles,
          ],
          ["scenarios", "协同执行", "发起协同任务", "按模板执行巡检、报告与故障处置", Workflow],
        ].map(([id, category, title, description, Icon]) => (
          <button className="workbench-task" key={String(id)} onClick={() => setPage(id as Page)}>
            <span className="task-icon">
              <Icon size={19} />
            </span>
            <span>
              <span className="task-category">{String(category)}</span>
              <b>{String(title)}</b>
              <small>{String(description)}</small>
            </span>
            <ChevronRight size={17} />
          </button>
        ))}
      </div>
      <div className="grid-two">
        <div className="panel attention-panel">
          <div className="panel-head">
            <div className="panel-title">
              <CircleAlert size={17} />
              <span>
                <h3>需要关注</h3>
                <small>按业务影响排序</small>
              </span>
            </div>
            <button className="text-btn" onClick={() => setPage("incidents")}>
              查看全部 <ChevronRight size={14} />
            </button>
          </div>
          {(summary?.incidents || []).slice(0, 2).map((i) => (
            <div className="list-row" key={i.id}>
              <div className={"severity " + i.severity.toLowerCase()}>{i.severity}</div>
              <div className="row-main">
                <b>{i.title}</b>
                <span>
                  {i.service} ·{" "}
                  {new Date(i.started_at).toLocaleTimeString("zh-CN", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </div>
              <span className="chip">
                {i.status === "investigating"
                  ? "处理中"
                  : i.status === "open"
                    ? "待处理"
                    : i.status === "resolved"
                      ? "已恢复"
                      : i.status}
              </span>
            </div>
          ))}
          {!summary?.incidents.length && <div className="empty">暂无待关注事件</div>}
        </div>
        <div className="panel recent-panel">
          <div className="panel-head">
            <div className="panel-title">
              <Clock3 size={17} />
              <span>
                <h3>最近问数</h3>
                <small>可继续追问或复用结果</small>
              </span>
            </div>
            <button className="text-btn" onClick={() => openQuery()}>
              新建问题 <ChevronRight size={14} />
            </button>
          </div>
          {(summary?.recent_queries || []).slice(0, 3).map((item) => (
            <button
              className="query-row query-history-button"
              key={item.operation_id}
              onClick={() => openQuery(item.question)}
            >
              <MessageSquare size={15} />
              <span>{item.question}</span>
              <small>
                {new Date(item.created_at).toLocaleTimeString("zh-CN", {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </small>
              <ChevronRight size={14} />
            </button>
          ))}
          {!summary?.recent_queries.length && <div className="empty">暂无问数记录</div>}
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
    <div className={`metric metric-${tone}`}>
      <div className="metric-head">
        <span>{label}</span>
        <i />
      </div>
      <strong className={tone}>{value}</strong>
      <small>{hint}</small>
    </div>
  );
}

type DataSourceFilter = "all" | "database" | "file";

function DataSourceManagementPage({ setPage }: { setPage: (page: Page) => void }) {
  const [sources, setSources] = useState<DataSourceRecord[]>([]);
  const [filter, setFilter] = useState<DataSourceFilter>("all");
  const [search, setSearch] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [addKind, setAddKind] = useState<"database" | "file">("database");
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<DataSourceRecord | null>(null);
  const [form, setForm] = useState({
    name: "",
    kind: "tidb" as "tidb" | "mysql",
    host: "",
    port: "4000",
    database: "",
    username: "root",
    password: "",
  });

  const loadSources = async () => {
    const items = await api<DataSourceRecord[]>("/chatbi/datasources");
    setSources(items);
    return items;
  };
  useEffect(() => {
    loadSources().catch((reason) =>
      setError(reason instanceof Error ? reason.message : "数据源加载失败"),
    );
  }, []);
  const addDatabase = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy("create");
    setError("");
    setMessage("");
    try {
      const item = await api<DataSourceRecord>("/chatbi/datasources", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          port: Number(form.port),
          test_on_create: true,
        }),
      });
      await loadSources();
      setForm({
        name: "",
        kind: "tidb",
        host: "",
        port: "4000",
        database: "",
        username: "root",
        password: "",
      });
      if (item.status === "ready") {
        setShowAdd(false);
        setMessage(`${item.name} 已添加，连接测试通过`);
      } else setError(item.last_error || "数据源已保存，但连接测试未通过");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "数据源添加失败");
    } finally {
      setBusy("");
    }
  };
  const uploadFile = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy("upload");
    setError("");
    setMessage("");
    const body = new FormData();
    body.append("file", file);
    try {
      const item = await api<DataSourceRecord>("/chatbi/datasources/upload", {
        method: "POST",
        headers: {},
        body,
      });
      await loadSources();
      setShowAdd(false);
      setMessage(`${item.name} 已添加，共 ${item.row_count || 0} 行`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "文件数据源上传失败");
    } finally {
      setBusy("");
      event.target.value = "";
    }
  };
  const testSource = async (item: DataSourceRecord) => {
    setBusy(item.id);
    setError("");
    setMessage("");
    try {
      const updated = await api<DataSourceRecord>(`/chatbi/datasources/${item.id}/test`, {
        method: "POST",
      });
      await loadSources();
      if (updated.status === "ready") setMessage(`${updated.name} 连接正常`);
      else setError(updated.last_error || "连接测试失败");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "连接测试失败");
    } finally {
      setBusy("");
    }
  };
  const removeSource = async () => {
    if (!deleteTarget) return;
    setBusy(deleteTarget.id);
    try {
      const response = await fetch(`${API_BASE}/chatbi/datasources/${deleteTarget.id}`, {
        method: "DELETE",
      });
      if (!response.ok) throw new Error((await response.text()) || "删除失败");
      await loadSources();
      setMessage(`${deleteTarget.name} 已删除`);
      setDeleteTarget(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "数据源删除失败");
    } finally {
      setBusy("");
    }
  };
  const openQueryWithSource = (item: DataSourceRecord) => {
    window.localStorage.setItem("chatbi-preferred-source", item.id);
    setPage("query");
  };
  const visible = sources.filter((item) => {
    const matchesType =
      filter === "all" || (filter === "database" ? item.kind !== "csv" : item.kind === "csv");
    const haystack =
      `${item.name} ${item.kind} ${item.database || ""} ${item.host || ""}`.toLowerCase();
    return matchesType && haystack.includes(search.trim().toLowerCase());
  });
  const readyCount = sources.filter((item) => item.status === "ready").length;
  const databaseCount = sources.filter((item) => item.kind !== "csv").length;
  const fileCount = sources.filter((item) => item.kind === "csv").length;
  return (
    <section className="content datasource-page">
      <div className="section-head">
        <div>
          <span className="eyebrow">数据库 · 文件 · 连接测试 · ChatBI</span>
          <h1>数据源管理</h1>
          <p className="section-subtitle">
            集中添加企业数据库和文件数据，连接成功后可直接用于智能问数。
          </p>
        </div>
        <button className="primary" onClick={() => setShowAdd(true)}>
          <Plus size={16} />
          添加数据源
        </button>
      </div>
      {message && (
        <div className="notice">
          <CheckCircle2 size={15} />
          {message}
          <button onClick={() => setMessage("")} aria-label="关闭提示">
            <X size={14} />
          </button>
        </div>
      )}
      {error && <div className="error-banner">{error}</div>}
      <div className="datasource-metrics">
        <div>
          <span className="source-metric-icon ready">
            <CheckCircle2 size={18} />
          </span>
          <span>
            <b>{readyCount}</b>
            <small>可用数据源</small>
          </span>
        </div>
        <div>
          <span className="source-metric-icon">
            <Database size={18} />
          </span>
          <span>
            <b>{databaseCount}</b>
            <small>数据库连接</small>
          </span>
        </div>
        <div>
          <span className="source-metric-icon file">
            <FileSpreadsheet size={18} />
          </span>
          <span>
            <b>{fileCount}</b>
            <small>文件数据源</small>
          </span>
        </div>
      </div>
      <div className="datasource-toolbar">
        <div className="searchbar">
          <Search size={17} />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="搜索名称、数据库或主机"
          />
        </div>
        <div className="segmented datasource-filters">
          {(["all", "database", "file"] as DataSourceFilter[]).map((id) => (
            <button
              key={id}
              className={filter === id ? "active" : ""}
              onClick={() => setFilter(id)}
            >
              {id === "all" ? "全部" : id === "database" ? "数据库" : "文件"}
            </button>
          ))}
        </div>
      </div>
      {visible.length === 0 ? (
        <div className="datasource-empty panel">
          <Database size={34} />
          <b>{sources.length ? "没有匹配的数据源" : "还没有数据源"}</b>
          <span>
            {sources.length
              ? "调整搜索条件或类型筛选。"
              : "添加 TiDB、MySQL、CSV 或 Parquet 后开始分析。"}
          </span>
          {!sources.length && (
            <button className="primary" onClick={() => setShowAdd(true)}>
              <Plus size={16} />
              添加第一个数据源
            </button>
          )}
        </div>
      ) : (
        <div className="datasource-grid">
          {visible.map((item) => (
            <article className="datasource-card panel" key={item.id}>
              <div className="datasource-card-head">
                <span className={`datasource-kind-icon ${item.kind}`}>
                  <>
                    {item.kind === "csv" ? <FileSpreadsheet size={19} /> : <Database size={19} />}
                  </>
                </span>
                <div>
                  <h3>{item.name}</h3>
                  <span>
                    {item.kind === "csv" ? "文件数据" : `${item.kind.toUpperCase()} 数据库`}
                  </span>
                </div>
                <span
                  className={`chip ${item.status === "ready" ? "success" : item.status === "error" ? "danger" : ""}`}
                >
                  {item.status === "ready"
                    ? "可用"
                    : item.status === "error"
                      ? "连接失败"
                      : "待测试"}
                </span>
              </div>
              <div className="datasource-card-body">
                {item.kind === "csv" ? (
                  <>
                    <span>
                      <b>文件标识</b>
                      {item.dataset_id}
                    </span>
                    <span>
                      <b>数据规模</b>
                      {item.row_count || 0} 行
                    </span>
                  </>
                ) : (
                  <>
                    <span>
                      <b>数据库</b>
                      {item.database}
                    </span>
                    <span>
                      <b>连接地址</b>
                      {item.host ? `${item.host}:${item.port}` : "演示连接"}
                    </span>
                    <span>
                      <b>用户名</b>
                      {item.username || "-"}
                    </span>
                    <span>
                      <b>结构对象</b>
                      {item.table_count} 个
                    </span>
                  </>
                )}
                {item.last_error && <p className="datasource-card-error">{item.last_error}</p>}
              </div>
              <div className="datasource-card-actions">
                {item.kind !== "csv" && item.host && (
                  <button
                    className="secondary"
                    disabled={busy === item.id}
                    onClick={() => void testSource(item)}
                  >
                    <RefreshCw size={14} />
                    测试连接
                  </button>
                )}
                <button
                  className="primary"
                  disabled={item.status !== "ready"}
                  onClick={() => openQueryWithSource(item)}
                >
                  <MessageSquare size={14} />
                  进入问数
                </button>
                {item.id !== "ds-demo-tidb" && (
                  <button
                    className="icon-button danger-button"
                    disabled={busy === item.id}
                    title="删除数据源"
                    aria-label={`删除 ${item.name}`}
                    onClick={() => setDeleteTarget(item)}
                  >
                    <Trash2 size={15} />
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
      {showAdd && (
        <div
          className="modal-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setShowAdd(false);
          }}
        >
          <div className="modal-card datasource-add-modal">
            <div className="panel-head">
              <div>
                <span className="eyebrow">新建数据源</span>
                <h3>选择添加方式</h3>
              </div>
              <button className="icon-button" onClick={() => setShowAdd(false)} aria-label="关闭">
                <X size={16} />
              </button>
            </div>
            <div className="datasource-add-tabs">
              <button
                className={addKind === "database" ? "active" : ""}
                onClick={() => setAddKind("database")}
              >
                <Database size={18} />
                <span>
                  <b>连接数据库</b>
                  <small>TiDB 或 MySQL</small>
                </span>
              </button>
              <button
                className={addKind === "file" ? "active" : ""}
                onClick={() => setAddKind("file")}
              >
                <FileSpreadsheet size={18} />
                <span>
                  <b>上传文件</b>
                  <small>CSV 或 Parquet</small>
                </span>
              </button>
            </div>
            {addKind === "database" ? (
              <form className="datasource-form" onSubmit={addDatabase}>
                <label>
                  数据库类型
                  <select
                    value={form.kind}
                    onChange={(event) => {
                      const kind = event.target.value as "tidb" | "mysql";
                      setForm({
                        ...form,
                        kind,
                        port: kind === "tidb" ? "4000" : "3306",
                      });
                    }}
                  >
                    <option value="tidb">TiDB</option>
                    <option value="mysql">MySQL</option>
                  </select>
                </label>
                <label>
                  连接名称
                  <input
                    required
                    value={form.name}
                    onChange={(event) => setForm({ ...form, name: event.target.value })}
                    placeholder="例如：经营分析库"
                  />
                </label>
                <div className="form-row">
                  <label>
                    主机地址
                    <input
                      required
                      value={form.host}
                      onChange={(event) => setForm({ ...form, host: event.target.value })}
                      placeholder="db.internal"
                    />
                  </label>
                  <label>
                    端口
                    <input
                      required
                      type="number"
                      value={form.port}
                      onChange={(event) => setForm({ ...form, port: event.target.value })}
                    />
                  </label>
                </div>
                <div className="form-row">
                  <label>
                    数据库
                    <input
                      required
                      value={form.database}
                      onChange={(event) => setForm({ ...form, database: event.target.value })}
                      placeholder="analytics"
                    />
                  </label>
                  <label>
                    用户名
                    <input
                      required
                      value={form.username}
                      onChange={(event) => setForm({ ...form, username: event.target.value })}
                    />
                  </label>
                </div>
                <label>
                  密码
                  <input
                    type="password"
                    value={form.password}
                    onChange={(event) => setForm({ ...form, password: event.target.value })}
                    placeholder="留空表示无密码"
                    autoComplete="new-password"
                  />
                </label>
                <div className="model-security-note">
                  <ShieldCheck size={16} />
                  <span>
                    <b>使用只读账号</b>
                    <small>密码与连接信息分开保存，页面和接口不会回显密码。</small>
                  </span>
                </div>
                <div className="modal-actions">
                  <button type="button" className="secondary" onClick={() => setShowAdd(false)}>
                    取消
                  </button>
                  <button className="primary" disabled={busy === "create"} type="submit">
                    {busy === "create" ? (
                      <>
                        <Clock3 size={15} />
                        连接测试中…
                      </>
                    ) : (
                      <>
                        <PlugZap size={15} />
                        保存并测试连接
                      </>
                    )}
                  </button>
                </div>
              </form>
            ) : (
              <div className="datasource-file-upload">
                <span className="upload-illustration">
                  <UploadCloud size={28} />
                </span>
                <b>上传 CSV 或 Parquet</b>
                <p>系统读取字段和行数，文件注册后可直接用于 ChatBI 分析。</p>
                <label className="primary file-button">
                  {busy === "upload" ? (
                    <>
                      <Clock3 size={16} />
                      处理中…
                    </>
                  ) : (
                    <>
                      <FileUp size={16} />
                      选择文件
                    </>
                  )}
                  <input
                    type="file"
                    disabled={busy === "upload"}
                    accept=".csv,.parquet"
                    onChange={uploadFile}
                  />
                </label>
                <small>支持 UTF-8 CSV 和标准 Parquet 文件</small>
              </div>
            )}
          </div>
        </div>
      )}
      {deleteTarget && (
        <div className="modal-backdrop">
          <div className="modal-card confirm-delete-modal">
            <span className="delete-warning-icon">
              <Trash2 size={22} />
            </span>
            <h3>删除数据源？</h3>
            <p>
              将删除“{deleteTarget.name}
              ”的连接记录。已生成的历史问数结果不会自动删除。
            </p>
            <div className="modal-actions">
              <button className="secondary" onClick={() => setDeleteTarget(null)}>
                取消
              </button>
              <button
                className="danger-action"
                disabled={busy === deleteTarget.id}
                onClick={() => void removeSource()}
              >
                确认删除
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

function AgentCenterPage({ setPage }: { setPage: (page: Page) => void }) {
  const [templates, setTemplates] = useState<AgentTemplate[]>([]);
  const [agents, setAgents] = useState<ModuleAgent[]>([]);
  const [readiness, setReadiness] = useState<ModelReadiness>();
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [selectedAgent, setSelectedAgent] = useState<ModuleAgent>();
  const [testResult, setTestResult] = useState<AgentTestResult>();
  const [testInput, setTestInput] = useState("");
  const [invokeResult, setInvokeResult] = useState<AgentInvokeResult>();

  const load = async () => {
    const [templateItems, agentItems, modelState] = await Promise.all([
      api<AgentTemplate[]>("/agents/templates"),
      api<ModuleAgent[]>("/agents"),
      api<ModelReadiness>("/models/readiness"),
    ]);
    setTemplates(templateItems);
    setAgents(agentItems);
    setReadiness(modelState);
  };
  useEffect(() => {
    load().catch((reason) =>
      setError(reason instanceof Error ? reason.message : "Agent 中心加载失败"),
    );
  }, []);

  const agentByTemplate = useMemo(
    () => new Map(agents.map((item) => [item.template_id, item])),
    [agents],
  );
  const missingCount = templates.filter((item) => !agentByTemplate.has(item.id)).length;
  const readyCount = agents.filter((item) => item.status === "ready").length;
  const approvalCount = agents.filter((item) => item.approval_policy === "human_approval").length;

  const provisionAll = async () => {
    setBusy("provision");
    setError("");
    try {
      const result = await api<AgentProvisionResult>("/agents/provision", {
        method: "POST",
        body: JSON.stringify({}),
      });
      setMessage(
        result.created.length
          ? `已使用 ${result.model_connection_name} 创建 ${result.created.length} 个 Agent`
          : "全部模块 Agent 已存在，无需重复创建",
      );
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "批量创建失败");
    } finally {
      setBusy("");
    }
  };
  const createOne = async (template: AgentTemplate) => {
    setBusy(template.id);
    setError("");
    try {
      await api<ModuleAgent>("/agents", {
        method: "POST",
        body: JSON.stringify({ template_id: template.id }),
      });
      setMessage(`${template.name} 已创建`);
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Agent 创建失败");
    } finally {
      setBusy("");
    }
  };
  const toggleAgent = async (agent: ModuleAgent, enabled: boolean) => {
    setBusy(agent.id);
    setError("");
    try {
      await api<ModuleAgent>(`/agents/${agent.id}/enabled`, {
        method: "PUT",
        body: JSON.stringify({ enabled }),
      });
      setMessage(`${agent.name} 已${enabled ? "启用" : "停用"}`);
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "状态更新失败");
    } finally {
      setBusy("");
    }
  };
  const removeAgent = async (agent: ModuleAgent) => {
    if (!window.confirm(`删除“${agent.name}”？之后可从模板重新创建。`)) return;
    setBusy(agent.id);
    setError("");
    try {
      const response = await fetch(`${API_BASE}/agents/${agent.id}`, {
        method: "DELETE",
      });
      if (!response.ok) throw new Error(await response.text());
      setMessage(`${agent.name} 已删除`);
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Agent 删除失败");
    } finally {
      setBusy("");
    }
  };
  const checkAgent = async (agent: ModuleAgent) => {
    setBusy(`check-${agent.id}`);
    setTestResult(undefined);
    setError("");
    try {
      const result = await api<AgentTestResult>(`/agents/${agent.id}/test`, {
        method: "POST",
      });
      setTestResult(result);
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Agent 自检失败");
    } finally {
      setBusy("");
    }
  };
  const openTester = (agent: ModuleAgent) => {
    setSelectedAgent(agent);
    setTestInput(`请说明你能协助完成哪些${agent.module_name}任务，以及当前安全边界。`);
    setInvokeResult(undefined);
    setTestResult(undefined);
    void checkAgent(agent);
  };
  const invoke = async () => {
    if (!selectedAgent || !testInput.trim()) return;
    setBusy(`invoke-${selectedAgent.id}`);
    setInvokeResult(undefined);
    setError("");
    try {
      const result = await api<AgentInvokeResult>(`/agents/${selectedAgent.id}/invoke`, {
        method: "POST",
        body: JSON.stringify({ input: testInput.trim() }),
      });
      setInvokeResult(result);
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "对话测试失败");
    } finally {
      setBusy("");
    }
  };
  const domainMeta: Record<
    ProductModule["domain"],
    { label: string; Icon: React.ComponentType<{ size?: number }> }
  > = {
    data: { label: "数据智能", Icon: Database },
    operations: { label: "运维", Icon: Activity },
    collaboration: { label: "协同", Icon: Workflow },
    platform: { label: "平台", Icon: Settings },
  };

  return (
    <section className="content agents-page">
      <div className="section-head">
        <div>
          <span className="eyebrow">模型绑定 · 能力装配 · 权限边界</span>
          <h1>Agent 中心</h1>
          <p className="section-subtitle">
            每个一级模块使用独立 Agent；统一绑定模型，但隔离能力、工具和审批策略。
          </p>
        </div>
        <button
          className="primary"
          disabled={!readiness?.ready || missingCount === 0 || busy === "provision"}
          onClick={() => void provisionAll()}
        >
          {busy === "provision" ? (
            <RefreshCw size={16} />
          ) : missingCount === 0 ? (
            <CircleCheck size={16} />
          ) : (
            <WandSparkles size={16} />
          )}
          {missingCount === 0
            ? `${templates.length} 个 Agent 已创建`
            : `一键创建${agents.length ? `剩余 ${missingCount} 个` : "全部"} Agent`}
        </button>
      </div>
      {message && (
        <div className="notice agent-notice">
          <CheckCircle2 size={15} />
          {message}
          <button onClick={() => setMessage("")} aria-label="关闭提示">
            <X size={14} />
          </button>
        </div>
      )}
      {error && <div className="error-banner">{error}</div>}
      {!readiness?.ready && (
        <div className="agent-model-gate panel">
          <span className="agent-gate-icon">
            <CloudCog size={23} />
          </span>
          <div>
            <b>先连接并启用一个大模型</b>
            <small>Agent 创建时会固定记录已验证模型，未验证的连接不会被使用。</small>
          </div>
          <button className="primary" onClick={() => setPage("models")}>
            前往模型接入 <ArrowRight size={16} />
          </button>
        </div>
      )}
      <div className="agent-summary">
        <div>
          <span>模块模板</span>
          <strong>{templates.length}</strong>
          <small>与功能中心同步</small>
        </div>
        <div>
          <span>已创建</span>
          <strong>{agents.length}</strong>
          <small>重复点击不会重复生成</small>
        </div>
        <div>
          <span>运行就绪</span>
          <strong>{readyCount}</strong>
          <small>模型与策略自检通过</small>
        </div>
        <div>
          <span>需人工审批</span>
          <strong>{approvalCount}</strong>
          <small>禁止直接执行高风险动作</small>
        </div>
      </div>
      <div className="agent-context-bar">
        <span className={readiness?.ready ? "ready" : ""}>
          <span className={`model-status ${readiness?.ready ? "ready" : ""}`} />
          {readiness?.ready
            ? `当前模型：${readiness.model || "服务默认模型"}`
            : "当前没有可用默认模型"}
        </span>
        <small>创建后模型绑定保持不变；工具默认只读或仅建议。</small>
      </div>
      <div className="agent-grid">
        {templates.map((template) => {
          const agent = agentByTemplate.get(template.id);
          const meta = domainMeta[template.domain];
          const Icon = meta.Icon;
          return (
            <article
              className={`agent-card panel ${agent?.status || "template"}`}
              key={template.id}
            >
              <div className="agent-card-head">
                <span className={`agent-module-icon ${template.domain}`}>
                  <Icon size={19} />
                </span>
                <div>
                  <small>
                    {meta.label} · {template.owner_role}
                  </small>
                  <h3>{agent?.name || template.name}</h3>
                </div>
                <span className={`agent-state ${agent?.status || "template"}`}>
                  {!agent
                    ? "待创建"
                    : agent.status === "ready"
                      ? "已就绪"
                      : agent.status === "disabled"
                        ? "已停用"
                        : "需处理"}
                </span>
              </div>
              <p>{template.summary}</p>
              <div className="agent-card-facts">
                <span>
                  <b>{template.capabilities.length}</b> 项模块能力
                </span>
                <span>
                  <b>{template.tools.length}</b> 个允许工具
                </span>
                <span
                  className={
                    template.approval_policy === "human_approval" ? "approval" : "readonly"
                  }
                >
                  {template.approval_policy === "human_approval" ? "人工审批" : "只读分析"}
                </span>
              </div>
              {agent ? (
                <>
                  <div className="agent-model-binding">
                    <Bot size={14} />
                    <span>
                      <small>绑定模型</small>
                      <b>
                        {agent.model_connection_name} · {agent.model}
                      </b>
                    </span>
                  </div>
                  {agent.last_error && <div className="agent-card-error">{agent.last_error}</div>}
                  <div className="agent-card-actions">
                    <label
                      className="agent-toggle"
                      title={agent.enabled ? "停用 Agent" : "启用 Agent"}
                    >
                      <input
                        type="checkbox"
                        checked={agent.enabled}
                        disabled={busy === agent.id}
                        onChange={(event) => void toggleAgent(agent, event.target.checked)}
                      />
                      <span />
                      <small>{agent.enabled ? "启用" : "停用"}</small>
                    </label>
                    <button className="secondary" onClick={() => openTester(agent)}>
                      <MessageSquare size={14} />
                      测试
                    </button>
                    {agent.target_page && (
                      <button
                        className="icon-button"
                        title={`进入${agent.module_name}`}
                        aria-label={`进入${agent.module_name}`}
                        onClick={() => setPage(agent.target_page as Page)}
                      >
                        <ArrowUpRight size={15} />
                      </button>
                    )}
                    <button
                      className="icon-button danger-button"
                      title="删除 Agent"
                      aria-label={`删除 ${agent.name}`}
                      disabled={busy === agent.id}
                      onClick={() => void removeAgent(agent)}
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </>
              ) : (
                <button
                  className="secondary agent-create-one"
                  disabled={!readiness?.ready || busy === template.id}
                  onClick={() => void createOne(template)}
                >
                  <Plus size={15} />
                  创建此 Agent
                </button>
              )}
            </article>
          );
        })}
      </div>
      {selectedAgent && (
        <div className="modal-backdrop">
          <div
            className="modal-card agent-test-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="agent-test-title"
          >
            <div className="panel-head">
              <div>
                <span className="eyebrow">配置自检 · 建议模式</span>
                <h3 id="agent-test-title">测试 {selectedAgent.name}</h3>
              </div>
              <button
                className="icon-button"
                aria-label="关闭"
                onClick={() => setSelectedAgent(undefined)}
              >
                <X size={16} />
              </button>
            </div>
            <div className="agent-test-meta">
              <span>
                <Bot size={14} /> {selectedAgent.model_connection_name} · {selectedAgent.model}
              </span>
              <span>
                <ShieldCheck size={14} />{" "}
                {selectedAgent.approval_policy === "human_approval"
                  ? "高风险操作需人工审批"
                  : "默认只读分析"}
              </span>
            </div>
            {error && <div className="error-banner agent-test-error">{error}</div>}
            <div className="agent-check-list">
              {!testResult && (
                <span className="loading-inline">
                  <RefreshCw size={14} /> 正在检查配置…
                </span>
              )}
              {testResult?.checks.map((check) => (
                <div key={check.key} className={check.passed ? "passed" : "failed"}>
                  {check.passed ? <CircleCheck size={15} /> : <CircleAlert size={15} />}
                  <span>
                    <b>{check.label}</b>
                    <small>{check.detail}</small>
                  </span>
                </div>
              ))}
            </div>
            <label className="agent-test-input">
              测试任务
              <textarea value={testInput} onChange={(event) => setTestInput(event.target.value)} />
            </label>
            <div className="agent-test-action">
              <small>测试只调用模型生成建议，不会执行模块工具。</small>
              <button
                className="primary"
                disabled={
                  !testResult?.passed || busy === `invoke-${selectedAgent.id}` || !testInput.trim()
                }
                onClick={() => void invoke()}
              >
                <Send size={15} />
                发送测试
              </button>
            </div>
            {invokeResult && (
              <div className="agent-test-answer">
                <div>
                  <b>Agent 回答</b>
                  <span>
                    {invokeResult.approval_required ? "建议模式 · 需审批" : "建议模式 · 只读"}
                  </span>
                </div>
                <p>{invokeResult.answer}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

function ModelConnectionsPage({
  onboarding,
  onComplete,
  enterWorkspace,
  openAgents,
}: {
  onboarding: boolean;
  onComplete: () => void;
  enterWorkspace: () => void;
  openAgents: () => void;
}) {
  const [providers, setProviders] = useState<ModelProvider[]>([]);
  const [connections, setConnections] = useState<ModelConnection[]>([]);
  const [deployment, setDeployment] = useState<"public" | "private">("public");
  const [providerId, setProviderId] = useState<ModelProvider["id"]>("openai");
  const [showForm, setShowForm] = useState(onboarding);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [completed, setCompleted] = useState(false);
  const [form, setForm] = useState({
    name: "OpenAI",
    base_url: "https://api.openai.com/v1",
    model: "",
    api_key: "",
    set_default: true,
  });

  const loadConnections = async () => {
    const items = await api<ModelConnection[]>("/models/connections");
    setConnections(items);
    return items;
  };
  useEffect(() => {
    Promise.all([api<ModelProvider[]>("/models/providers"), loadConnections()])
      .then(([items]) => setProviders(items))
      .catch((reason) => setError(reason instanceof Error ? reason.message : "模型配置加载失败"));
  }, []);
  useEffect(() => {
    if (onboarding) setShowForm(true);
  }, [onboarding]);

  const chooseProvider = (provider: ModelProvider) => {
    setProviderId(provider.id);
    setDeployment(provider.deployment);
    setForm({
      name: provider.name,
      base_url: provider.default_base_url,
      model: "",
      api_key: "",
      set_default: true,
    });
    setError("");
  };
  const switchDeployment = (next: "public" | "private") => {
    setDeployment(next);
    const provider = providers.find((item) => item.deployment === next);
    if (provider) chooseProvider(provider);
  };
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy("create");
    setError("");
    setMessage("");
    try {
      const item = await api<ModelConnection>("/models/connections", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          provider: providerId,
          deployment,
          test_on_create: true,
        }),
      });
      await loadConnections();
      setShowForm(false);
      onComplete();
      if (item.status === "ready") {
        setCompleted(true);
        setMessage(
          item.model_source === "auto"
            ? `${item.name} 已保存，自动识别模型 ${item.model}`
            : `${item.name} 已连接并设为默认模型`,
        );
      } else {
        setMessage(`${item.name} 已保存；暂未验证可用模型，可在连接列表中重新测试`);
      }
      setForm((current) => ({ ...current, api_key: "" }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "模型添加失败");
    } finally {
      setBusy("");
    }
  };
  const testModel = async (id: string) => {
    setBusy(id);
    setError("");
    try {
      const item = await api<ModelConnection>(`/models/connections/${id}/test`, { method: "POST" });
      await loadConnections();
      setMessage(
        item.status === "ready" ? `${item.name} 连接正常` : item.last_error || "连接测试失败",
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "连接测试失败");
    } finally {
      setBusy("");
    }
  };
  const activate = async (id: string) => {
    setBusy(id);
    try {
      const item = await api<ModelConnection>(`/models/connections/${id}/activate`, {
        method: "POST",
      });
      await loadConnections();
      setMessage(`${item.name} 已设为默认模型`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "默认模型设置失败");
    } finally {
      setBusy("");
    }
  };
  const remove = async (id: string) => {
    setBusy(id);
    try {
      const response = await fetch(`${API_BASE}/models/connections/${id}`, {
        method: "DELETE",
      });
      if (!response.ok) throw new Error(await response.text());
      await loadConnections();
      setMessage("模型连接已移除");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "模型移除失败");
    } finally {
      setBusy("");
    }
  };
  const provisionAgents = async () => {
    setBusy("provision-agents");
    setError("");
    try {
      const result = await api<AgentProvisionResult>("/agents/provision", {
        method: "POST",
        body: JSON.stringify({}),
      });
      const detail = result.created.length
        ? `已基于 ${result.model_connection_name} 创建 ${result.created.length} 个模块 Agent`
        : `${result.existing.length} 个模块 Agent 已存在，无需重复创建`;
      setMessage(detail);
      openAgents();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Agent 创建失败");
    } finally {
      setBusy("");
    }
  };
  const selected = providers.find((item) => item.id === providerId);
  const visibleProviders = providers.filter((item) => item.deployment === deployment);
  const activeConnection = connections.find((item) => item.is_default && item.status === "ready");
  return (
    <section className="content models-page">
      <div className="section-head">
        <div>
          <span className="eyebrow">
            {onboarding ? "首次配置 · 第 1 步" : "模型注册 · 连接测试 · 默认路由"}
          </span>
          <h1>{onboarding ? "先连接一个大模型" : "模型接入"}</h1>
          <p className="section-subtitle">
            {onboarding
              ? "完成连接后，智能问数、知识库和 AIOps 才能使用模型推理。"
              : "统一管理公有 API 与企业私有推理服务。"}
          </p>
        </div>
        {!onboarding && (
          <button className="primary" onClick={() => setShowForm(true)}>
            <Plus size={16} />
            添加模型
          </button>
        )}
      </div>
      {message && (
        <div className="notice">
          <CheckCircle2 size={15} />
          {message}
          <button onClick={() => setMessage("")} aria-label="关闭提示">
            <X size={14} />
          </button>
        </div>
      )}
      {error && <div className="error-banner">{error}</div>}
      {completed && (
        <div className="model-complete panel">
          <div className="model-complete-icon">
            <CircleCheck size={24} />
          </div>
          <div>
            <b>模型连接已就绪</b>
            <span>下一步可按 8 个产品模块自动装配能力、工具权限和审批策略。</span>
          </div>
          <div className="model-complete-actions">
            <button className="secondary" onClick={enterWorkspace}>
              稍后处理
            </button>
            <button
              className="primary"
              disabled={busy === "provision-agents"}
              onClick={() => void provisionAgents()}
            >
              {busy === "provision-agents" ? <RefreshCw size={16} /> : <WandSparkles size={16} />}
              一键创建模块 Agent
            </button>
          </div>
        </div>
      )}
      {!completed && !showForm && activeConnection && (
        <div className="model-agent-next panel">
          <span className="model-agent-next-icon">
            <Bot size={20} />
          </span>
          <div>
            <b>默认模型已就绪，继续装配模块 Agent</b>
            <small>将为智能问数、知识库、数据治理、AIOps 等 8 个模块创建独立 Agent。</small>
          </div>
          <button
            className="primary"
            disabled={busy === "provision-agents"}
            onClick={() => void provisionAgents()}
          >
            <WandSparkles size={16} />
            一键创建
          </button>
        </div>
      )}
      {showForm && (
        <div className="model-setup panel">
          <div className="model-provider-pane">
            <div className="segmented model-deployment-tabs">
              <button
                className={deployment === "public" ? "active" : ""}
                onClick={() => switchDeployment("public")}
              >
                <CloudCog size={15} />
                公有模型
              </button>
              <button
                className={deployment === "private" ? "active" : ""}
                onClick={() => switchDeployment("private")}
              >
                <Server size={15} />
                私有模型
              </button>
            </div>
            <div className="model-provider-list">
              {visibleProviders.map((provider) => (
                <button
                  key={provider.id}
                  className={provider.id === providerId ? "active" : ""}
                  onClick={() => chooseProvider(provider)}
                >
                  <span className="provider-mark">{provider.name.slice(0, 1)}</span>
                  <span>
                    <b>{provider.name}</b>
                    <small>{provider.description}</small>
                  </span>
                  <ChevronRight size={15} />
                </button>
              ))}
            </div>
          </div>
          <form className="model-connection-form" onSubmit={submit}>
            <div className="panel-head">
              <div>
                <span className="eyebrow">
                  {selected?.deployment === "public" ? "云端 API" : "企业网络"}
                </span>
                <h3>连接 {selected?.name || "模型"}</h3>
              </div>
              {!onboarding && (
                <button
                  type="button"
                  className="icon-button"
                  onClick={() => setShowForm(false)}
                  aria-label="关闭"
                >
                  <X size={16} />
                </button>
              )}
            </div>
            <label>
              连接名称
              <input
                required
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
              />
            </label>
            <label>
              服务地址
              <input
                required
                value={form.base_url}
                onChange={(event) => setForm({ ...form, base_url: event.target.value })}
              />
            </label>
            <label>
              <span className="model-field-label">
                模型 ID <span className="optional-label">可选</span>
              </span>
              <input
                value={form.model}
                onChange={(event) => setForm({ ...form, model: event.target.value })}
                placeholder={`可留空自动识别；${selected?.model_placeholder || "也可手动输入模型 ID"}`}
              />
              <small className="model-field-help">
                留空时将从模型服务自动获取；无法识别也可以保存连接，但不能设为默认模型。
              </small>
            </label>
            <label>
              API Key{" "}
              {selected?.api_key_required ? (
                <span className="required-label">必填</span>
              ) : (
                <span className="optional-label">可选</span>
              )}
              <input
                type="password"
                required={selected?.api_key_required}
                value={form.api_key}
                onChange={(event) => setForm({ ...form, api_key: event.target.value })}
                placeholder={selected?.api_key_required ? "输入服务商 API Key" : "无鉴权可留空"}
                autoComplete="new-password"
              />
            </label>
            <label className="model-default-check">
              <input
                type="checkbox"
                checked={form.set_default}
                onChange={(event) => setForm({ ...form, set_default: event.target.checked })}
              />
              <span>
                <b>设为默认模型</b>
                <small>平台推理任务优先使用此连接</small>
              </span>
            </label>
            <div className="model-security-note">
              <ShieldCheck size={16} />
              <span>
                <b>凭证不会回显</b>
                <small>API Key 与连接记录分离保存，页面和接口响应不返回原值。</small>
              </span>
            </div>
            <div className="model-form-actions">
              {onboarding && (
                <button
                  type="button"
                  className="text-btn"
                  onClick={() => {
                    onComplete();
                    enterWorkspace();
                  }}
                >
                  稍后配置，使用规则模式
                </button>
              )}
              <button className="primary" type="submit" disabled={busy === "create"}>
                {busy === "create" ? (
                  <>
                    <Clock3 size={16} />
                    测试连接中…
                  </>
                ) : (
                  <>
                    <PlugZap size={16} />
                    保存并测试连接
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      )}
      {!showForm && connections.length === 0 && !completed && (
        <div className="model-empty panel">
          <Bot size={34} />
          <b>尚未接入模型</b>
          <span>添加一个公有 API 或企业私有推理服务。</span>
          <button className="primary" onClick={() => setShowForm(true)}>
            <Plus size={16} />
            添加模型
          </button>
        </div>
      )}
      {connections.length > 0 && (
        <div className="model-connections">
          <div className="model-list-head">
            <div>
              <span className="eyebrow">当前工作空间</span>
              <h3>已接入模型</h3>
            </div>
            <span className="chip">{connections.length} 个连接</span>
          </div>
          <div className="model-grid">
            {connections.map((item) => (
              <article
                className={`model-card panel ${item.is_default ? "default" : ""}`}
                key={item.id}
              >
                <div className="model-card-head">
                  <span className="provider-mark">{item.provider_name.slice(0, 1)}</span>
                  <div>
                    <h3>{item.name}</h3>
                    <span>
                      {item.provider_name} · {item.deployment === "public" ? "公有云" : "私有部署"}
                    </span>
                  </div>
                  {item.is_default && <span className="chip success">默认</span>}
                </div>
                <div className="model-card-body">
                  <span>
                    <b>模型</b>
                    {item.model ||
                      (item.model_source === "gateway-default" ? "服务默认模型" : "未指定")}
                    {item.model_source === "auto" ? "（自动识别）" : ""}
                  </span>
                  <span>
                    <b>地址</b>
                    {item.base_url}
                  </span>
                  <span>
                    <b>状态</b>
                    <i className={`model-status ${item.status}`} />
                    {item.status === "ready"
                      ? "连接正常"
                      : item.status === "error"
                        ? "连接失败"
                        : "待测试"}
                  </span>
                  <span>
                    <b>凭证</b>
                    {item.has_credential ? "已配置" : "无鉴权"}
                  </span>
                </div>
                {item.last_error && <div className="model-card-error">{item.last_error}</div>}
                <div className="model-card-actions">
                  <button
                    className="secondary"
                    disabled={busy === item.id}
                    onClick={() => void testModel(item.id)}
                  >
                    <RefreshCw size={14} />
                    测试
                  </button>
                  {!item.is_default && (
                    <button
                      className="secondary"
                      disabled={item.status !== "ready" || busy === item.id}
                      onClick={() => void activate(item.id)}
                    >
                      <CheckCircle2 size={14} />
                      设为默认
                    </button>
                  )}
                  <button
                    className="icon-button danger-button"
                    title="移除连接"
                    aria-label={`移除 ${item.name}`}
                    disabled={busy === item.id}
                    onClick={() => void remove(item.id)}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </article>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

type SettingsSection = "general" | "model" | "connectors" | "security";

function SettingsPage({ setPage }: { setPage: (page: Page) => void }) {
  const [section, setSection] = useState<SettingsSection>("general");
  const [feedback, setFeedback] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [settings, setSettings] = useState<WorkspaceSettings | null>(null);
  const sections = [
    ["general", "基础设置", SlidersHorizontal],
    ["model", "模型网关", CloudCog],
    ["connectors", "数据连接", Cable],
    ["security", "安全策略", LockKeyhole],
  ] as const;
  useEffect(() => {
    void api<WorkspaceSettings>("/settings")
      .then(setSettings)
      .catch((reason) => setError(reason instanceof Error ? reason.message : "设置加载失败"));
  }, []);
  const update = <K extends keyof WorkspaceSettings>(key: K, value: WorkspaceSettings[K]) =>
    setSettings((current) => (current ? { ...current, [key]: value } : current));
  const saveSettings = async (message: string) => {
    if (!settings) return;
    setSaving(true);
    setError("");
    try {
      const updated = await api<WorkspaceSettings>("/settings", {
        method: "PATCH",
        body: JSON.stringify(settings),
      });
      setSettings(updated);
      setFeedback(message);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "设置保存失败");
    } finally {
      setSaving(false);
    }
  };
  return (
    <section className="content settings-page">
      <div className="section-head">
        <div>
          <span className="eyebrow">工作空间 · 模型 · 连接 · 安全</span>
          <h1>系统设置</h1>
          <p className="section-subtitle">管理当前工作空间的基础配置和本地集成边界。</p>
        </div>
        <span className="environment-badge">
          <span className="status-dot" />
          本地演示
        </span>
      </div>
      {feedback && (
        <div className="notice settings-notice">
          <CheckCircle2 size={15} />
          {feedback}
          <button onClick={() => setFeedback("")} aria-label="关闭提示">
            <X size={14} />
          </button>
        </div>
      )}
      {error && <div className="error-banner">{error}</div>}
      <div className="settings-layout">
        <nav className="settings-nav" aria-label="设置分类">
          {sections.map(([id, label, Icon]) => (
            <button
              key={id}
              className={section === id ? "active" : ""}
              onClick={() => {
                setSection(id);
                setFeedback("");
              }}
            >
              <Icon size={17} />
              <span>{label}</span>
              <ChevronRight size={15} />
            </button>
          ))}
        </nav>
        <div className="panel settings-panel">
          {!settings && !error && <div className="loading">正在加载设置…</div>}
          {section === "general" && (
            <>
              <SettingsHeader title="基础设置" description="工作空间名称、语言和时间展示规则。" />
              <div className="settings-form-grid">
                <SettingsField label="工作空间名称">
                  <input
                    value={settings?.workspace_name || ""}
                    onChange={(event) => update("workspace_name", event.target.value)}
                  />
                </SettingsField>
                <SettingsField label="默认语言">
                  <select
                    value={settings?.language || "zh-CN"}
                    onChange={(event) => update("language", event.target.value)}
                  >
                    <option value="zh-CN">简体中文</option>
                    <option value="en-US">English</option>
                  </select>
                </SettingsField>
                <SettingsField label="时区">
                  <select
                    value={settings?.timezone || "Asia/Shanghai"}
                    onChange={(event) => update("timezone", event.target.value)}
                  >
                    <option>Asia/Shanghai</option>
                    <option>UTC</option>
                  </select>
                </SettingsField>
                <SettingsField label="数据保留期">
                  <select
                    value={String(settings?.data_retention_days || 90)}
                    onChange={(event) => update("data_retention_days", Number(event.target.value))}
                  >
                    <option value="30">30 天</option>
                    <option value="90">90 天</option>
                    <option value="180">180 天</option>
                  </select>
                </SettingsField>
              </div>
              <SettingsSave
                onClick={() => void saveSettings("基础设置已保存到 TiDB")}
                busy={saving || !settings}
              />
            </>
          )}
          {section === "model" && (
            <>
              <SettingsHeader
                title="模型网关"
                description="模型连接、凭证和默认路由统一在模型接入模块维护。"
              />
              <div className="settings-security-note">
                <ShieldCheck size={16} />
                <span>
                  <b>凭证安全</b>
                  <small>API Key 与连接记录分离保存，页面不会回显密钥。</small>
                </span>
              </div>
              <div className="settings-actions">
                <button className="primary" onClick={() => setPage("models")}>
                  <CloudCog size={16} />
                  打开模型接入
                </button>
              </div>
            </>
          )}
          {section === "connectors" && (
            <>
              <SettingsHeader
                title="数据连接"
                description="配置 TiDB MCP 与本地受控目录，连接默认只读。"
              />
              <div className="settings-form-grid">
                <SettingsField label="TiDB MCP Endpoint" wide>
                  <input
                    value={settings?.tidb_mcp_endpoint || ""}
                    onChange={(event) => update("tidb_mcp_endpoint", event.target.value)}
                  />
                </SettingsField>
                <SettingsField label="允许读取的目录" wide>
                  <input
                    value={settings?.allowed_data_root || ""}
                    onChange={(event) => update("allowed_data_root", event.target.value)}
                  />
                </SettingsField>
              </div>
              <div className="connector-health-row">
                <span>
                  <span className="status-dot" />
                  TiDB MCP
                </span>
                <b>已连接</b>
                <small>2 个 Schema</small>
              </div>
              <SettingsSave
                onClick={() => void saveSettings("数据连接配置已保存到 TiDB")}
                busy={saving || !settings}
              />
            </>
          )}
          {section === "security" && (
            <>
              <SettingsHeader
                title="安全策略"
                description="本地演示默认启用只读查询、操作审计和目录白名单。"
              />
              <div className="settings-toggle-list">
                <label>
                  <span>
                    <b>只读 SQL</b>
                    <small>阻止 INSERT、UPDATE、DELETE 与 DDL</small>
                  </span>
                  <input
                    type="checkbox"
                    checked={settings?.readonly_sql || false}
                    onChange={(event) => update("readonly_sql", event.target.checked)}
                  />
                </label>
                <label>
                  <span>
                    <b>操作审计</b>
                    <small>记录人员、输入、策略结果和追踪 ID</small>
                  </span>
                  <input
                    type="checkbox"
                    checked={settings?.operation_audit || false}
                    onChange={(event) => update("operation_audit", event.target.checked)}
                  />
                </label>
                <label>
                  <span>
                    <b>高风险操作审批</b>
                    <small>执行前等待具有权限的审批人确认</small>
                  </span>
                  <input
                    type="checkbox"
                    checked={settings?.high_risk_approval || false}
                    onChange={(event) => update("high_risk_approval", event.target.checked)}
                  />
                </label>
                <label>
                  <span>
                    <b>仅允许本地模型</b>
                    <small>禁止数据发送至公网模型服务</small>
                  </span>
                  <input
                    type="checkbox"
                    checked={settings?.local_models_only || false}
                    onChange={(event) => update("local_models_only", event.target.checked)}
                  />
                </label>
              </div>
              <SettingsSave
                onClick={() => void saveSettings("安全策略已保存到 TiDB")}
                busy={saving || !settings}
              />
            </>
          )}
        </div>
      </div>
    </section>
  );
}

function SettingsHeader({ title, description }: { title: string; description: string }) {
  return (
    <div className="settings-panel-head">
      <span className="eyebrow">当前工作空间</span>
      <h2>{title}</h2>
      <p>{description}</p>
    </div>
  );
}

function SettingsField({
  label,
  wide = false,
  children,
}: {
  label: string;
  wide?: boolean;
  children: React.ReactNode;
}) {
  return (
    <label className={wide ? "settings-field wide-field" : "settings-field"}>
      <span>{label}</span>
      {children}
    </label>
  );
}

function SettingsSave({ onClick, busy = false }: { onClick: () => void; busy?: boolean }) {
  return (
    <button className="primary settings-save" onClick={onClick} disabled={busy}>
      <Save size={16} />
      {busy ? "保存中…" : "保存设置"}
    </button>
  );
}
function Incidents({ setPage }: { setPage: (page: Page) => void }) {
  const [filter, setFilter] = useState("全部");
  const [selectedId, setSelectedId] = useState("");
  const [message, setMessage] = useState("");
  const [items, setItems] = useState<IncidentRecord[]>([]);
  const [error, setError] = useState("");
  const statusLabel = (status: string) =>
    status === "investigating"
      ? "处理中"
      : status === "open"
        ? "待处理"
        : status === "resolved"
          ? "已恢复"
          : status;
  const formatTime = (value: string) =>
    new Date(value).toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  useEffect(() => {
    void api<IncidentRecord[]>("/incidents")
      .then(setItems)
      .catch((reason) => setError(reason instanceof Error ? reason.message : "事件加载失败"));
  }, []);
  const visibleIncidents = items.filter(
    (item) => filter === "全部" || statusLabel(item.status) === filter,
  );
  const selectedIncident = items.find((item) => item.id === selectedId);
  const markRead = async () => {
    try {
      const result = await api<{ count: number }>("/incidents/read", {
        method: "POST",
        body: JSON.stringify({ incident_ids: items.map((item) => item.id) }),
      });
      setMessage(`已标记 ${result.count} 个事件为已读`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "标记已读失败");
    }
  };
  const claim = async (incidentId: string) => {
    try {
      const updated = await api<IncidentRecord>(`/incidents/${incidentId}/claim`, {
        method: "POST",
      });
      setItems((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setMessage("已领取事件，状态进入处理中");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "领取事件失败");
    }
  };
  return (
    <section className="content incident-page">
      <div className="section-head">
        <div>
          <span className="eyebrow">实时监控 · 过去 24 小时</span>
          <h1>事件中心</h1>
        </div>
        <button className="secondary" onClick={() => void markRead()}>
          <CheckCircle2 size={16} />
          标记已读
        </button>
      </div>
      {message && (
        <div className="notice inline-notice">
          <CheckCircle2 size={15} />
          {message}
          <button onClick={() => setMessage("")} aria-label="关闭提示">
            <X size={14} />
          </button>
        </div>
      )}
      {error && <div className="error-banner">{error}</div>}
      <div className="filters">
        {["全部", "待处理", "处理中", "已恢复"].map((item) => (
          <button
            className={filter === item ? "filter active" : "filter"}
            onClick={() => {
              setFilter(item);
              setSelectedId("");
            }}
            key={item}
          >
            {item}{" "}
            <b>
              {item === "全部"
                ? items.length
                : items.filter((incident) => statusLabel(incident.status) === item).length}
            </b>
          </button>
        ))}
      </div>
      <div className="incident-layout">
        <div className="panel incident-list">
          {visibleIncidents.map((i) => (
            <button
              className={
                selectedId === i.id
                  ? "incident incident-button selected"
                  : "incident incident-button"
              }
              key={i.id}
              onClick={() => setSelectedId(i.id)}
            >
              <div className={"severity " + i.severity.toLowerCase()}>{i.severity}</div>
              <div className="row-main">
                <b>{i.title}</b>
                <span>
                  {i.id} · {i.service}
                </span>
              </div>
              <span className="chip">{statusLabel(i.status)}</span>
              <small>{formatTime(i.started_at)}</small>
              <ChevronRight size={17} />
            </button>
          ))}
          {!visibleIncidents.length && <div className="empty">当前筛选下没有事件</div>}
        </div>
        {selectedIncident && (
          <div className="panel incident-detail" aria-label="事件详情">
            <div className="incident-detail-head">
              <div className={"severity " + selectedIncident.severity.toLowerCase()}>
                {selectedIncident.severity}
              </div>
              <button
                className="icon-button"
                onClick={() => setSelectedId("")}
                aria-label="关闭详情"
              >
                <X size={16} />
              </button>
            </div>
            <span className="eyebrow">{selectedIncident.id}</span>
            <h2>{selectedIncident.title}</h2>
            <p>{selectedIncident.summary}</p>
            <div className="incident-facts">
              <span>
                <b>当前状态</b>
                {statusLabel(selectedIncident.status)}
              </span>
              <span>
                <b>建议动作</b>
                {selectedIncident.recommended_action}
              </span>
            </div>
            <div className="incident-detail-actions">
              <button className="secondary" onClick={() => void claim(selectedIncident.id)}>
                领取事件
              </button>
              <button className="primary" onClick={() => setPage("scenarios")}>
                <Workflow size={15} />
                启动作战室
              </button>
            </div>
          </div>
        )}
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
      | {
          resize: () => void;
          dispose: () => void;
          setOption: (next: EChartsOption) => void;
        }
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
function OperationProgress({ state }: { state: OperationProgressState }) {
  if (state.phase === "IDLE") return null;
  const steps: Array<[OperationPhase, string]> = [
    ["PLANNING", "规划"],
    ["VALIDATING", "校验"],
    ["EXECUTING", "执行"],
    ["COMPLETED", "完成"],
  ];
  const currentIndex = steps.findIndex(([phase]) => phase === state.phase);
  return (
    <div
      className={`operation-progress ${state.phase.toLowerCase()}`}
      role="status"
      aria-live="polite"
    >
      <div className="operation-progress-head">
        <span>
          <Activity size={14} /> 查询执行进度
        </span>
        <b>{state.progress}%</b>
      </div>
      <div className="operation-progress-track">
        <span style={{ width: `${state.progress}%` }} />
      </div>
      <ol>
        {steps.map(([phase, label], index) => (
          <li
            key={phase}
            className={
              index < currentIndex || state.phase === "COMPLETED"
                ? "done"
                : index === currentIndex
                  ? "current"
                  : ""
            }
          >
            <span>{index < currentIndex || state.phase === "COMPLETED" ? "✓" : index + 1}</span>
            {label}
          </li>
        ))}
      </ol>
      <small>{state.detail}</small>
    </div>
  );
}
function QueryV2({
  initialQuestion = "",
  module,
  onModuleChange,
}: {
  initialQuestion?: string;
  module: QueryModule;
  onModuleChange: (module: QueryModule) => void;
}) {
  const [datasources, setDatasources] = useState<DataSourceRecord[]>([]);
  const [reports, setReports] = useState<DashboardReport[]>([]);
  const [sourceId, setSourceId] = useState(
    () => window.localStorage.getItem("chatbi-preferred-source") || "",
  );
  const [question, setQuestion] = useState(initialQuestion);
  const [result, setResult] = useState<QueryResult | null>(null);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [operationProgress, setOperationProgress] = useState<OperationProgressState>({
    phase: "IDLE",
    detail: "",
    progress: 0,
  });

  const loadSources = async () => {
    try {
      const data = await api<DataSourceRecord[]>("/chatbi/datasources");
      setDatasources(data);
      setSourceId((current) => {
        const next =
          current && data.some((item) => item.id === current)
            ? current
            : data.find((item) => item.status === "ready")?.id || data[0]?.id || "";
        if (next) window.localStorage.setItem("chatbi-preferred-source", next);
        return next;
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "数据源加载失败");
    }
  };
  const loadReports = async () => {
    try {
      setReports(await api<DashboardReport[]>("/chatbi/reports"));
    } catch (e) {
      setError(e instanceof Error ? e.message : "大屏加载失败");
    }
  };
  useEffect(() => {
    void loadSources();
    void loadReports();
  }, []);
  useEffect(() => {
    if (initialQuestion) setQuestion(initialQuestion);
  }, [initialQuestion]);

  const streamOperation = (operationId: string) =>
    new Promise<void>((resolve) => {
      let attempts = 0;
      let source: EventSource | undefined;
      const connect = () => {
        source = new EventSource(`${API_BASE}/query/operations/${operationId}/events`);
        source.addEventListener("progress", (event) => {
          const payload = JSON.parse((event as MessageEvent).data) as {
            phase: OperationPhase;
            detail: string;
            progress: number;
          };
          setOperationProgress(payload);
        });
        source.addEventListener("completed", (event) => {
          const payload = JSON.parse((event as MessageEvent).data) as {
            phase: OperationPhase;
            progress: number;
          };
          setOperationProgress({
            phase: payload.phase,
            detail: "查询结果已返回",
            progress: payload.progress,
          });
          source?.close();
          resolve();
        });
        source.onerror = () => {
          source?.close();
          if (attempts < 2) {
            attempts += 1;
            window.setTimeout(connect, 250 * attempts);
          } else {
            setOperationProgress((current) => ({
              ...current,
              phase: "COMPLETED",
              detail: "已完成，实时进度通道暂时断开",
              progress: 100,
            }));
            resolve();
          }
        };
      };
      connect();
    });

  const run = async () => {
    if (!sourceId || !question.trim()) {
      setError("请先选择可用数据源并输入问题");
      return;
    }
    setRunning(true);
    setError("");
    setMessage("");
    setOperationProgress({ phase: "PLANNING", detail: "正在解析自然语言问题", progress: 10 });
    try {
      const data = await api<QueryResult>("/chatbi/query", {
        method: "POST",
        body: JSON.stringify({ datasource_id: sourceId, question }),
      });
      setOperationProgress({
        phase: "VALIDATING",
        detail: "正在校验只读 SQL 和数据源权限",
        progress: 45,
      });
      await streamOperation(data.operation_id);
      setResult(data);
      setMessage("分析完成，可检查 SQL 和证据后加入大屏");
    } catch (e) {
      setOperationProgress({
        phase: "FAILED",
        detail: "执行失败，可检查错误后重试",
        progress: 100,
      });
      setError(e instanceof Error ? e.message : "分析失败");
    } finally {
      setRunning(false);
    }
  };
  const approve = async () => {
    if (!result || !sourceId) return;
    const title = result.chart?.title || result.question;
    try {
      await api<DashboardReport>("/chatbi/reports", {
        method: "POST",
        body: JSON.stringify({
          operation_id: result.operation_id,
          datasource_id: sourceId,
          title,
        }),
      });
      await loadReports();
      setMessage("已加入大屏");
      onModuleChange("dashboard");
    } catch (e) {
      setError(e instanceof Error ? e.message : "加入大屏失败");
    }
  };
  const deleteReport = async (id: string) => {
    try {
      const response = await fetch(`${API_BASE}/chatbi/reports/${id}`, {
        method: "DELETE",
      });
      if (!response.ok) throw new Error((await response.text()) || "移除失败");
      setReports((current) => current.filter((report) => report.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "移除失败");
    }
  };
  return (
    <section className="content query-page chatbi-page">
      <div className="section-head">
        <div>
          <span className="eyebrow">
            智能问数 · {module === "dashboard" ? "大屏展示" : "ChatBI"}
          </span>
          <h1>从问题到可复用报表</h1>
          <p className="section-subtitle">
            从统一数据源管理选择数据源，再提问和核验，认可的结果一键沉淀到大屏。
          </p>
        </div>
      </div>
      {message && (
        <div className="notice">
          <CheckCircle2 size={15} />
          {message}
          <button onClick={() => setMessage("")} aria-label="关闭提示">
            <X size={14} />
          </button>
        </div>
      )}
      {error && <div className="error-banner">{error}</div>}
      <OperationProgress state={operationProgress} />
      {module === "chatbi" && (
        <div className="chatbi-workspace">
          <div className="chatbi-conversation panel">
            <div className="chatbi-toolbar">
              <div>
                <span className="eyebrow">对话分析</span>
                <h3>问数据</h3>
              </div>
              <label>
                数据源
                <select
                  value={sourceId}
                  onChange={(event) => {
                    setSourceId(event.target.value);
                    window.localStorage.setItem("chatbi-preferred-source", event.target.value);
                  }}
                >
                  {datasources.length === 0 && <option value="">暂无可用数据源</option>}
                  {datasources.map((item) => (
                    <option key={item.id} value={item.id} disabled={item.status !== "ready"}>
                      {item.name} · {item.kind.toUpperCase()}{" "}
                      {item.status !== "ready" ? "（不可用）" : ""}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="chat-empty">
              <div className="chat-avatar">
                <MessageSquare size={20} />
              </div>
              <div>
                <b>今天想了解什么？</b>
                <p>我会根据所选数据源生成只读 SQL，执行后自动选择最合适的 BI 展示。</p>
              </div>
            </div>
            <div className="chat-suggestions">
              {["近 30 天 GMV 趋势", "订单金额按区域汇总", "不同品类的销售额占比"].map((item) => (
                <button key={item} onClick={() => setQuestion(item)}>
                  {item}
                </button>
              ))}
            </div>
            <textarea
              className="chat-input"
              value={question}
              autoFocus
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
                  event.preventDefault();
                  void run();
                }
              }}
              placeholder="输入你的业务问题，例如：本月各区域 GMV 占比"
            />
            <div className="chat-actions">
              <span>
                <ShieldCheck size={14} />
                只读执行 · 可追溯
              </span>
              <button
                className="primary"
                onClick={() => void run()}
                disabled={running || !sourceId || !question.trim()}
              >
                {running ? (
                  <>
                    <Clock3 size={16} />
                    分析中…
                  </>
                ) : (
                  <>
                    <Send size={16} />
                    发送问题
                  </>
                )}
              </button>
            </div>
            {result && (
              <div className="chat-last-message">
                <div className="chat-avatar user-avatar">林</div>
                <div>
                  <b>{result.question}</b>
                  <span>已生成 SQL 和结果</span>
                </div>
              </div>
            )}
          </div>
          <div className="chatbi-report panel">
            <div className="panel-head">
              <div>
                <span className="eyebrow">BI 结果</span>
                <h3>{result?.chart?.title || "等待一次提问"}</h3>
              </div>
              {result && <span className="chip success">已完成</span>}
            </div>
            {result ? (
              <>
                <p className="answer">{result.answer}</p>
                {result.chart?.option && <ChartView option={result.chart.option} />}
                <div className="report-table-wrap">
                  <table>
                    <thead>
                      <tr>
                        {result.columns.map((column) => (
                          <th key={column}>{column}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.rows.slice(0, 20).map((row, rowIndex) => (
                        <tr key={rowIndex}>
                          {row.map((cell, cellIndex) => (
                            <td key={cellIndex}>{String(cell ?? "-")}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <details className="sql-details">
                  <summary>
                    <FileCode2 size={15} />
                    查看只读 SQL 与证据
                  </summary>
                  <pre>{result.sql}</pre>
                  <div className="evidence">
                    {result.evidence.map((item) => (
                      <span key={item.type + item.ref}>{item.label}</span>
                    ))}
                  </div>
                </details>
                <button className="primary wide" onClick={() => void approve()}>
                  <MonitorUp size={16} />
                  认可并加入大屏
                </button>
              </>
            ) : (
              <div className="report-empty">
                <PanelsTopLeft size={32} />
                <b>报表会显示在这里</b>
                <span>选择数据源并发送一个问题</span>
              </div>
            )}
          </div>
        </div>
      )}
      {module === "dashboard" && (
        <div className="dashboard-panel">
          <div className="dashboard-toolbar">
            <div>
              <span className="eyebrow">已认可 · 可复用</span>
              <h3>经营分析大屏</h3>
            </div>
            <span className="chip success">{reports.length} 张报表</span>
          </div>
          {reports.length === 0 ? (
            <div className="dashboard-empty">
              <MonitorUp size={34} />
              <b>还没有已认可报表</b>
              <span>在 ChatBI 中核验结果后，点击“认可并加入大屏”。</span>
              <button className="secondary" onClick={() => onModuleChange("chatbi")}>
                <MessageSquare size={15} />
                去生成第一张
              </button>
            </div>
          ) : (
            <div className="dashboard-grid">
              {reports.map((report) => (
                <article className="dashboard-card panel" key={report.id}>
                  <div className="panel-head">
                    <div>
                      <span className="eyebrow">{report.datasource_name}</span>
                      <h3>{report.title}</h3>
                    </div>
                    <button
                      className="icon-button"
                      title="移除报表"
                      aria-label={`移除 ${report.title}`}
                      onClick={() => void deleteReport(report.id)}
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                  <p className="dashboard-question">{report.question}</p>
                  {report.chart.option && <ChartView option={report.chart.option} />}
                  <div className="dashboard-card-foot">
                    <span>认可人 {report.accepted_by}</span>
                    <button
                      className="text-btn"
                      onClick={() => {
                        setSourceId(report.datasource_id);
                        setQuestion(report.question);
                        onModuleChange("chatbi");
                      }}
                    >
                      再次分析 <ArrowRight size={14} />
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
function AssetsV2({ setPage }: { setPage: (page: Page) => void }) {
  const [search, setSearch] = useState("");
  const [assetItems, setAssetItems] = useState<AssetRecord[]>([]);
  const [assetError, setAssetError] = useState("");
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [directory, setDirectory] = useState("");
  const [message, setMessage] = useState("");
  const [datasetId, setDatasetId] = useState("");
  const [datasetQuestion, setDatasetQuestion] = useState("");
  const [datasetResult, setDatasetResult] = useState<QueryResult | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState<AssetRecord | null>(null);
  const [assetMessage, setAssetMessage] = useState("");
  useEffect(() => {
    void api<AssetRecord[]>("/assets")
      .then(setAssetItems)
      .catch((reason) => setAssetError(reason instanceof Error ? reason.message : "资产加载失败"));
  }, []);
  const filtered = assetItems.filter((item) =>
    (item.name + " " + item.description + " " + item.owner)
      .toLowerCase()
      .includes(search.toLowerCase()),
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
      {assetError && <div className="error-banner">{assetError}</div>}
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
              <span className="chip success">质量 {a.quality_score ?? "-"}</span>
            </div>
            <h3>{a.name}</h3>
            <span className="asset-type">
              {a.type} · {a.owner}
            </span>
            <p>{a.description}</p>
            <div className="asset-foot">
              <span>
                {a.row_count == null ? "指标" : `${a.row_count.toLocaleString("en-US")} 行`}
              </span>
              <button
                className="text-btn"
                onClick={() => {
                  setSelectedAsset(a);
                  setAssetMessage("");
                }}
              >
                查看详情 <ChevronRight size={14} />
              </button>
            </div>
          </div>
        ))}
      </div>
      {selectedAsset && (
        <div className="panel asset-detail-panel">
          <div className="panel-head">
            <div className="panel-title">
              <Database size={18} />
              <span>
                <h3>{selectedAsset.name}</h3>
                <small>
                  {selectedAsset.type} · {selectedAsset.owner}
                </small>
              </span>
            </div>
            <button
              className="icon-button"
              onClick={() => setSelectedAsset(null)}
              aria-label="关闭资产详情"
            >
              <X size={16} />
            </button>
          </div>
          <p>{selectedAsset.description}</p>
          {assetMessage && (
            <div className="inline-success">
              <CheckCircle2 size={14} />
              {assetMessage}
            </div>
          )}
          <div className="asset-detail-facts">
            <span>
              <b>数据规模</b>
              {selectedAsset.row_count == null
                ? "指标"
                : `${selectedAsset.row_count.toLocaleString("en-US")} 行`}
            </span>
            <span>
              <b>质量评分</b>
              {selectedAsset.quality_score ?? "-"}
            </span>
            <span>
              <b>责任团队</b>
              {selectedAsset.owner}
            </span>
          </div>
          <div className="asset-detail-actions">
            <button className="secondary" onClick={() => setPage("catalog")}>
              <Network size={15} />
              查看数据关系
            </button>
            <button
              className="primary"
              onClick={() => {
                void api(`/assets/${selectedAsset.id}/governance-tasks`, {
                  method: "POST",
                  body: JSON.stringify({
                    asset_id: selectedAsset.id,
                    title: `${selectedAsset.name}治理检查`,
                    description: "由数据资产页创建的治理任务草稿",
                  }),
                })
                  .then(() => setAssetMessage("已创建该资产的治理任务草稿"))
                  .catch((reason) =>
                    setAssetError(reason instanceof Error ? reason.message : "治理任务创建失败"),
                  );
              }}
            >
              <ListChecks size={15} />
              创建治理任务
            </button>
          </div>
        </div>
      )}
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
                    {item.kind.toUpperCase()} · {item.rows} 行 · {item.columns.length} 列
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
              <button className="primary" onClick={analyze} disabled={analyzing}>
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
                {datasetResult.chart?.option && <ChartView option={datasetResult.chart.option} />}
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
function RelationshipNetwork({
  snapshot,
  level,
}: {
  snapshot: RelationshipSnapshot;
  level: "table" | "field";
}) {
  const option = useMemo<EChartsOption>(() => {
    const visibleNodes = snapshot.nodes.filter((node) =>
      level === "table" ? node.kind === "table" : node.kind !== "schema",
    );
    const nodeIds = new Set(visibleNodes.map((node) => node.id));
    const visibleEdges = snapshot.edges.filter(
      (edge) =>
        (level === "table"
          ? edge.level === "table"
          : edge.level === "field" || edge.level === "structure") &&
        nodeIds.has(edge.source) &&
        nodeIds.has(edge.target),
    );
    const relationCount = new Map<string, number>();
    visibleEdges.forEach((edge) => {
      relationCount.set(edge.source, (relationCount.get(edge.source) || 0) + 1);
      relationCount.set(edge.target, (relationCount.get(edge.target) || 0) + 1);
    });
    return {
      animationDurationUpdate: 450,
      tooltip: {
        trigger: "item",
        renderMode: "richText",
        formatter: (params: any) => {
          const data = params.data || {};
          if (params.dataType === "edge") {
            return `${data.source}\n→ ${data.target}\n${data.kind} · ${data.sourceType === "sql" ? "SQL 推断" : "元数据"}\n置信度 ${Math.round((data.confidence || 0) * 100)}% · ${data.count || 1} 次`;
          }
          return [
            data.displayLabel || data.name,
            data.fullName,
            data.comment || "暂无 Comment",
            data.dataType || "",
          ]
            .filter(Boolean)
            .join("\n");
        },
      },
      legend: [
        {
          bottom: 10,
          data: ["数据表", "字段"],
          textStyle: { color: "#64748b" },
        },
      ],
      series: [
        {
          type: "graph",
          layout: "force",
          roam: true,
          draggable: true,
          categories: [
            { name: "数据表", itemStyle: { color: "#2864dc" } },
            { name: "字段", itemStyle: { color: "#6b7f95" } },
          ],
          data: visibleNodes.map((node) => ({
            id: node.id,
            name: node.id,
            displayLabel: node.label,
            fullName: node.id,
            comment: node.comment,
            dataType: node.data_type,
            category: node.kind === "table" ? 0 : 1,
            symbolSize:
              node.kind === "table" ? 34 + Math.min(relationCount.get(node.id) || 0, 6) * 2 : 13,
            label: {
              show: node.kind === "table",
              formatter: node.label,
              color: "#24364d",
              position: "bottom",
              fontSize: 11,
            },
          })),
          links: visibleEdges.map((edge) => ({
            source: edge.source,
            target: edge.target,
            kind: edge.kind,
            sourceType: edge.source_type,
            confidence: edge.confidence,
            count: edge.observation_count,
            lineStyle: {
              color:
                edge.source_type === "sql"
                  ? "#c27b28"
                  : edge.source_type === "metadata"
                    ? "#27845c"
                    : "#cbd5e1",
              width:
                edge.level === "structure" ? 1 : 1.5 + Math.min(edge.observation_count, 6) * 0.25,
              opacity: edge.level === "structure" ? 0.38 : 0.82,
              curveness: 0.08,
            },
          })),
          force: {
            repulsion: level === "table" ? 420 : 250,
            edgeLength: level === "table" ? [110, 190] : [70, 125],
            gravity: 0.08,
          },
          emphasis: { focus: "adjacency", lineStyle: { width: 3 } },
        },
      ],
    };
  }, [snapshot, level]);
  return <ChartView option={option} />;
}

function CatalogPage({ setPage }: { setPage: (page: Page) => void }) {
  const [sources, setSources] = useState<DataSourceRecord[]>([]);
  const [sourceId, setSourceId] = useState("");
  const [snapshot, setSnapshot] = useState<RelationshipSnapshot | null>(null);
  const [activeTab, setActiveTab] = useState<"graph" | "metadata" | "sql">("graph");
  const [graphLevel, setGraphLevel] = useState<"table" | "field">("table");
  const [sqlInput, setSqlInput] = useState(
    "SELECT o.order_id, c.region\nFROM sales.orders o\nJOIN sales.customers c ON c.customer_id = o.customer_id;",
  );
  const [autoCollect, setAutoCollect] = useState(false);
  const [collectorStatus, setCollectorStatus] = useState<SqlCollectorStatus | null>(null);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const selectedSource = sources.find((item) => item.id === sourceId);

  const collectMetadata = async (id = sourceId) => {
    if (!id) return;
    setBusy("metadata");
    setError("");
    try {
      const data = await api<RelationshipSnapshot>(`/data-relationships/${id}/collect`, {
        method: "POST",
      });
      setSnapshot(data);
      setMessage(
        `已采集 ${data.schemas.length} 个 Schema、${data.nodes.filter((node) => node.kind === "table").length} 张表`,
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "元数据采集失败");
    } finally {
      setBusy("");
    }
  };
  const collectSql = async (silent = false) => {
    if (!sourceId || selectedSource?.kind !== "tidb") return;
    if (!silent) setBusy("sql-collect");
    setError("");
    try {
      const data = await api<RelationshipSnapshot>(`/data-relationships/${sourceId}/collect-sql`, {
        method: "POST",
      });
      setSnapshot(data);
      if (!silent) setMessage(`已更新 ${data.sql_observations.length} 条关联 SQL 摘要`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "关联 SQL 采集失败");
      setAutoCollect(false);
    } finally {
      if (!silent) setBusy("");
    }
  };
  const ingestManualSql = async () => {
    if (!sourceId || !sqlInput.trim()) return;
    setBusy("sql-manual");
    setError("");
    try {
      await api(`/data-relationships/${sourceId}/sql-observations`, {
        method: "POST",
        body: JSON.stringify({ sql: sqlInput, source: "manual" }),
      });
      const data = await api<RelationshipSnapshot>(`/data-relationships/${sourceId}`);
      setSnapshot(data);
      setMessage("SQL 已解析，表级和字段级关系已更新");
      setActiveTab("graph");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "SQL 关系解析失败");
    } finally {
      setBusy("");
    }
  };
  const configureAutoCollect = async (enabled: boolean) => {
    if (!sourceId || selectedSource?.kind !== "tidb") return;
    setBusy("collector");
    setError("");
    try {
      const status = await api<SqlCollectorStatus>(
        `/data-relationships/${sourceId}/sql-collector`,
        {
          method: "PUT",
          body: JSON.stringify({ enabled, interval_seconds: 30 }),
        },
      );
      setCollectorStatus(status);
      setAutoCollect(status.enabled);
      if (status.last_error) {
        setError(`持续采集最近失败：${status.last_error}`);
      }
      setMessage(
        status.enabled ? "服务端持续采集已启动，关闭页面后仍会运行" : "服务端持续采集已停止",
      );
      if (status.enabled) {
        const data = await api<RelationshipSnapshot>(`/data-relationships/${sourceId}`);
        setSnapshot(data);
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "持续采集设置失败");
      setAutoCollect(false);
    } finally {
      setBusy("");
    }
  };

  useEffect(() => {
    api<DataSourceRecord[]>("/chatbi/datasources")
      .then((items) => {
        const databaseSources = items.filter((item) => ["tidb", "mysql"].includes(item.kind));
        setSources(databaseSources);
        setSourceId(
          databaseSources.find((item) => item.status === "ready")?.id ||
            databaseSources[0]?.id ||
            "",
        );
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : "数据源加载失败"));
  }, []);
  useEffect(() => {
    if (!sourceId) {
      setSnapshot(null);
      setAutoCollect(false);
      setCollectorStatus(null);
      return;
    }
    void collectMetadata(sourceId);
    api<SqlCollectorStatus>(`/data-relationships/${sourceId}/sql-collector`)
      .then((status) => {
        setCollectorStatus(status);
        setAutoCollect(status.enabled);
      })
      .catch((reason) =>
        setError(reason instanceof Error ? reason.message : "持续采集状态加载失败"),
      );
  }, [sourceId]);

  const tableCount = snapshot?.nodes.filter((node) => node.kind === "table").length || 0;
  const relationCount = snapshot?.edges.filter((edge) => edge.level !== "structure").length || 0;
  const sqlCount = snapshot?.sql_observations.length || 0;

  return (
    <section className="content relationship-page">
      <div className="section-head">
        <div>
          <span className="eyebrow">Schema · 表 · 字段 Comment · SQL 血缘</span>
          <h1>数据关系</h1>
          <p className="section-subtitle">
            从数据库元数据和关联查询 SQL 持续发现表级、字段级关系。
          </p>
        </div>
        <div className="relationship-head-actions">
          <button
            className="secondary"
            disabled={!sourceId || selectedSource?.kind !== "tidb" || busy === "sql-collect"}
            onClick={() => void collectSql()}
          >
            <Link2 size={15} />
            {busy === "sql-collect" ? "采集中…" : "采集关联 SQL"}
          </button>
          <button
            className="primary"
            disabled={!sourceId || busy === "metadata"}
            onClick={() => void collectMetadata()}
          >
            <RefreshCw size={15} />
            {busy === "metadata" ? "采集中…" : "采集元数据"}
          </button>
        </div>
      </div>
      {message && (
        <div className="notice relationship-notice">
          <CheckCircle2 size={15} />
          {message}
          <button onClick={() => setMessage("")} aria-label="关闭提示">
            <X size={14} />
          </button>
        </div>
      )}
      {error && <div className="error-banner">{error}</div>}
      <div className="relationship-sourcebar panel">
        <label>
          <span>数据源</span>
          <select value={sourceId} onChange={(event) => setSourceId(event.target.value)}>
            {sources.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name} · {item.kind.toUpperCase()} · {item.status}
              </option>
            ))}
          </select>
        </label>
        <div className="relationship-source-status">
          <span className={`model-status ${selectedSource?.status || ""}`} />
          <span>
            <b>{selectedSource?.name || "尚未添加数据库"}</b>
            <small>
              {selectedSource
                ? `${selectedSource.database || "-"} · ${snapshot?.source || "等待采集"}`
                : "先到数据源管理添加 TiDB 或 MySQL"}
            </small>
          </span>
        </div>
        <label className="auto-collect-toggle">
          <input
            type="checkbox"
            checked={autoCollect}
            disabled={!sourceId || selectedSource?.kind !== "tidb" || busy === "collector"}
            onChange={(event) => void configureAutoCollect(event.target.checked)}
          />
          <span>
            <b>持续采集 SQL</b>
            <small>
              {selectedSource?.kind === "tidb"
                ? "服务端每 30 秒增量同步"
                : "自动采集仅支持 TiDB；可手工粘贴 SQL"}
              {collectorStatus?.last_collected_at
                ? ` · 最近 ${new Date(collectorStatus.last_collected_at).toLocaleTimeString("zh-CN")}`
                : ""}
            </small>
          </span>
        </label>
        {!sources.length && (
          <button className="primary" onClick={() => setPage("datasources")}>
            <Plus size={15} />
            添加数据源
          </button>
        )}
      </div>
      <div className="relationship-metrics">
        <div>
          <Database size={18} />
          <span>
            <b>{snapshot?.schemas.length || 0}</b>
            <small>Schema</small>
          </span>
        </div>
        <div>
          <PanelsTopLeft size={18} />
          <span>
            <b>{tableCount}</b>
            <small>数据表</small>
          </span>
        </div>
        <div>
          <Network size={18} />
          <span>
            <b>{relationCount}</b>
            <small>表/字段关系</small>
          </span>
        </div>
        <div>
          <FileCode2 size={18} />
          <span>
            <b>{sqlCount}</b>
            <small>关联 SQL</small>
          </span>
        </div>
      </div>
      <div className="relationship-tabs" role="tablist" aria-label="数据关系视图">
        <button
          className={activeTab === "graph" ? "active" : ""}
          onClick={() => setActiveTab("graph")}
        >
          <Network size={16} />
          关系网络图
        </button>
        <button
          className={activeTab === "metadata" ? "active" : ""}
          onClick={() => setActiveTab("metadata")}
        >
          <Database size={16} />
          元数据目录
        </button>
        <button className={activeTab === "sql" ? "active" : ""} onClick={() => setActiveTab("sql")}>
          <FileCode2 size={16} />
          SQL 采集
        </button>
      </div>
      {!snapshot ? (
        <div className="relationship-empty panel">
          <Network size={36} />
          <b>等待采集数据关系</b>
          <span>选择可用数据库并点击“采集元数据”。</span>
        </div>
      ) : activeTab === "graph" ? (
        <div className="relationship-graph-layout">
          <div className="relationship-network panel">
            <div className="panel-head">
              <div>
                <span className="eyebrow">力导向网络 · 滚轮缩放 · 拖拽节点</span>
                <h3>{graphLevel === "table" ? "表与表关系" : "字段与字段关系"}</h3>
              </div>
              <div className="segmented">
                <button
                  className={graphLevel === "table" ? "active" : ""}
                  onClick={() => setGraphLevel("table")}
                >
                  表级
                </button>
                <button
                  className={graphLevel === "field" ? "active" : ""}
                  onClick={() => setGraphLevel("field")}
                >
                  字段级
                </button>
              </div>
            </div>
            <RelationshipNetwork snapshot={snapshot} level={graphLevel} />
            <div className="relationship-legend">
              <span>
                <i className="metadata" />
                数据库约束/元数据
              </span>
              <span>
                <i className="sql" />
                SQL 推断
              </span>
              <span>
                <i className="structure" />
                表字段从属
              </span>
            </div>
          </div>
          <section className="relationship-edge-list panel">
            <div className="panel-head">
              <h3>已发现关系</h3>
              <span className="chip">{relationCount}</span>
            </div>
            {snapshot.edges
              .filter((edge) => edge.level === graphLevel)
              .sort((a, b) => b.observation_count - a.observation_count)
              .slice(0, 30)
              .map((edge) => (
                <div className="relationship-edge-row" key={edge.id}>
                  <span className={`edge-source-mark ${edge.source_type}`} />
                  <div>
                    <b>{edge.source}</b>
                    <span>
                      <ArrowRight size={12} />
                      {edge.target}
                    </span>
                    <small>
                      {edge.kind} · {edge.observation_count} 次 · 置信度{" "}
                      {Math.round(edge.confidence * 100)}%
                    </small>
                  </div>
                </div>
              ))}
          </section>
        </div>
      ) : activeTab === "metadata" ? (
        <div className="relationship-metadata-grid">
          {snapshot.schemas.map((schema) => (
            <section className="relationship-schema panel" key={schema.name}>
              <div className="panel-head">
                <h3>
                  <Database size={15} />
                  {schema.name}
                </h3>
                <span className="chip">{schema.tables.length} tables</span>
              </div>
              {schema.tables.map((table) => (
                <details key={table.name}>
                  <summary>
                    <span>
                      <b>{table.name}</b>
                      <small>{table.comment || "暂无表 Comment"}</small>
                    </span>
                    <span>{table.columns.length} 字段</span>
                  </summary>
                  <div className="relationship-column-list">
                    {table.columns.map((column) => (
                      <div key={column.name}>
                        <code>{column.name}</code>
                        <span>{column.data_type}</span>
                        <small>{column.comment || "暂无字段 Comment"}</small>
                      </div>
                    ))}
                  </div>
                </details>
              ))}
            </section>
          ))}
        </div>
      ) : (
        <div className="relationship-sql-layout">
          <section className="relationship-sql-input panel">
            <div className="panel-head">
              <div>
                <span className="eyebrow">补充采集</span>
                <h3>粘贴关联查询 SQL</h3>
              </div>
              <span className="chip success">仅解析，不执行</span>
            </div>
            <textarea
              value={sqlInput}
              onChange={(event) => setSqlInput(event.target.value)}
              spellCheck={false}
              aria-label="关联查询 SQL"
            />
            <div className="relationship-sql-actions">
              <span>解析 FROM、JOIN 和字段等值条件，合并到关系图。</span>
              <button
                className="primary"
                disabled={!sqlInput.trim() || busy === "sql-manual"}
                onClick={() => void ingestManualSql()}
              >
                <Network size={15} />
                {busy === "sql-manual" ? "解析中…" : "解析并学习关系"}
              </button>
            </div>
          </section>
          <section className="relationship-sql-history panel">
            <div className="panel-head">
              <h3>采集记录</h3>
              <span className="chip">{sqlCount} 条摘要</span>
            </div>
            {snapshot.sql_observations.length ? (
              snapshot.sql_observations.map((item) => (
                <article key={item.id}>
                  <div>
                    <span className="chip">{item.source}</span>
                    <small>
                      {item.execution_count} 次 · {item.relationship_ids.length} 条关系
                    </small>
                  </div>
                  <code>{item.sql_preview}</code>
                  <small>最近发现 {new Date(item.last_seen_at).toLocaleString("zh-CN")}</small>
                </article>
              ))
            ) : (
              <div className="relationship-sql-empty">尚未采集关联 SQL。</div>
            )}
          </section>
        </div>
      )}
    </section>
  );
}
function KnowledgeBasePage() {
  const [libraries, setLibraries] = useState<KnowledgeBaseRecord[]>([]);
  const [indexModes, setIndexModes] = useState<KnowledgeIndexMode[]>([]);
  const [chunkingModes, setChunkingModes] = useState<KnowledgeChunkingMode[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [question, setQuestion] = useState("TiDB 巡检发现慢 SQL 时应该如何处理？");
  const [queryTags, setQueryTags] = useState("");
  const [topK, setTopK] = useState("5");
  const [scoreThreshold, setScoreThreshold] = useState("0.20");
  const [generateAnswer, setGenerateAnswer] = useState(true);
  const [result, setResult] = useState<KnowledgeQueryResult | null>(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [tags, setTags] = useState("");
  const [directory, setDirectory] = useState("");
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newChunkSize, setNewChunkSize] = useState("800");
  const [newChunkOverlap, setNewChunkOverlap] = useState("120");
  const [newIndexMode, setNewIndexMode] = useState<KnowledgeIndexMode["id"]>("hybrid");
  const [newChunkingMode, setNewChunkingMode] = useState<KnowledgeChunkingMode["id"]>("recursive");
  const [showCreate, setShowCreate] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [activeTab, setActiveTab] = useState<"ask" | "documents" | "retrieval">("ask");
  const [queries, setQueries] = useState<KnowledgeQueryResult[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState("");
  const [chunks, setChunks] = useState<KnowledgeChunk[]>([]);
  const [feedback, setFeedback] = useState<"helpful" | "not-helpful" | "idle">("idle");
  const [editChunkSize, setEditChunkSize] = useState("800");
  const [editChunkOverlap, setEditChunkOverlap] = useState("120");
  const [editIndexMode, setEditIndexMode] = useState<KnowledgeIndexMode["id"]>("hybrid");
  const [editChunkingMode, setEditChunkingMode] =
    useState<KnowledgeChunkingMode["id"]>("recursive");
  const selected = libraries.find((item) => item.id === selectedId) || libraries[0];

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
      setDocuments(await api<KnowledgeDocument[]>(`/knowledge-bases/${knowledgeBaseId}/documents`));
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
          "/knowledge-bases/" + knowledgeBaseId + "/documents/" + documentId + "/chunks",
        ),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "分块预览加载失败");
    }
  };
  useEffect(() => {
    void loadLibraries();
    api<KnowledgeIndexMode[]>("/knowledge-bases/index-modes")
      .then(setIndexModes)
      .catch((e) => setError(e instanceof Error ? e.message : "索引模式加载失败"));
    api<KnowledgeChunkingMode[]>("/knowledge-bases/chunking-modes")
      .then(setChunkingModes)
      .catch((e) => setError(e instanceof Error ? e.message : "分块模式加载失败"));
  }, []);
  useEffect(() => {
    if (selectedId) {
      setResult(null);
      void loadDocuments(selectedId);
      void loadQueries(selectedId);
      setSelectedDocumentId("");
      setChunks([]);
      setFeedback("idle");
      setEditChunkSize(String(selected?.chunk_size || 800));
      setEditChunkOverlap(String(selected?.chunk_overlap || 120));
      setEditIndexMode(selected?.retrieval_strategy || "hybrid");
      setEditChunkingMode(selected?.chunking_strategy || "recursive");
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
          chunk_size: Number(newChunkSize),
          chunk_overlap: Number(newChunkOverlap),
          retrieval_strategy: newIndexMode,
          chunking_strategy: newChunkingMode,
        }),
      });
      setNewName("");
      setNewDescription("");
      setNewChunkSize("800");
      setNewChunkOverlap("120");
      setNewIndexMode("hybrid");
      setNewChunkingMode("recursive");
      setShowCreate(false);
      await loadLibraries(item.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "创建知识库失败");
    } finally {
      setBusy("");
    }
  };
  const saveSettings = async () => {
    if (!selected) return;
    setBusy("settings");
    setError("");
    setMessage("");
    try {
      const updated = await api<KnowledgeBaseRecord>(`/knowledge-bases/${selected.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          chunk_size: Number(editChunkSize),
          chunk_overlap: Number(editChunkOverlap),
          retrieval_strategy: editIndexMode,
          chunking_strategy: editChunkingMode,
        }),
      });
      setLibraries((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      setMessage(
        Number(editChunkSize) !== selected.chunk_size ||
          Number(editChunkOverlap) !== selected.chunk_overlap ||
          editChunkingMode !== selected.chunking_strategy
          ? `配置已保存，已重新生成 ${updated.chunk_count} 个检索片段`
          : "索引配置已保存",
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "索引配置保存失败");
    } finally {
      setBusy("");
    }
  };
  const addTextDocument = async () => {
    if (!selected || !title.trim() || !content.trim()) return;
    setBusy("text");
    setError("");
    try {
      await api<KnowledgeDocument>(`/knowledge-bases/${selected.id}/documents`, {
        method: "POST",
        body: JSON.stringify({
          title: title.trim(),
          content,
          tags: tags
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
        }),
      });
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
  const uploadDocuments = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!selected || !event.target.files?.length) return;
    setBusy("upload");
    setError("");
    try {
      const form = new FormData();
      Array.from(event.target.files).forEach((file) => form.append("files", file));
      await api<KnowledgeDocument[]>(`/knowledge-bases/${selected.id}/documents/upload`, {
        method: "POST",
        body: form,
      });
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
      await api<KnowledgeDocument[]>(`/knowledge-bases/${selected.id}/documents/local-directory`, {
        method: "POST",
        body: JSON.stringify({
          path: directory.trim(),
          tags: tags
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
        }),
      });
      setDirectory("");
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "目录扫描失败");
    } finally {
      setBusy("");
    }
  };
  const toggleDocument = async (document: KnowledgeDocument) => {
    if (!selected) return;
    setBusy(`toggle-${document.id}`);
    setError("");
    try {
      const updated = await api<KnowledgeDocument>(
        `/knowledge-bases/${selected.id}/documents/${document.id}`,
        {
          method: "PATCH",
          body: JSON.stringify({ enabled: !document.enabled }),
        },
      );
      setDocuments((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      setMessage(updated.enabled ? "文档已参与检索" : "文档已暂停检索");
    } catch (e) {
      setError(e instanceof Error ? e.message : "文档状态更新失败");
    } finally {
      setBusy("");
    }
  };
  const reindexDocument = async (document: KnowledgeDocument) => {
    if (!selected) return;
    setBusy(`reindex-${document.id}`);
    setError("");
    try {
      const updated = await api<KnowledgeDocument>(
        `/knowledge-bases/${selected.id}/documents/${document.id}/reindex`,
        { method: "POST" },
      );
      setDocuments((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      await loadLibraries(selected.id);
      if (selectedDocumentId === document.id) {
        await loadChunks(selected.id, document.id);
      }
      setMessage(`“${document.title}”已重新生成 ${updated.chunk_count} 个片段`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "重新索引失败");
    } finally {
      setBusy("");
    }
  };
  const removeDocument = async (document: KnowledgeDocument) => {
    if (!selected || !window.confirm(`确认删除“${document.title}”及其全部检索片段？`)) {
      return;
    }
    setBusy(`delete-${document.id}`);
    setError("");
    try {
      await api<{ deleted: boolean }>(`/knowledge-bases/${selected.id}/documents/${document.id}`, {
        method: "DELETE",
      });
      if (selectedDocumentId === document.id) {
        setSelectedDocumentId("");
        setChunks([]);
      }
      await refresh();
      setMessage("文档及其检索片段已删除");
    } catch (e) {
      setError(e instanceof Error ? e.message : "文档删除失败");
    } finally {
      setBusy("");
    }
  };
  const query = async () => {
    if (!selected || !question.trim()) return;
    setBusy("query");
    setError("");
    try {
      const nextResult = await api<KnowledgeQueryResult>(`/knowledge-bases/${selected.id}/query`, {
        method: "POST",
        body: JSON.stringify({
          question: question.trim(),
          top_k: Number(topK),
          tags: queryTags
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
          generate_answer: activeTab === "ask" && generateAnswer,
          score_threshold: Number(scoreThreshold),
        }),
      });
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
        "/knowledge-bases/" + selected.id + "/queries/" + result.query_id + "/feedback",
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
        <button className="secondary" onClick={() => void refresh()} disabled={Boolean(busy)}>
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
      {message && (
        <div className="notice knowledge-notice">
          <CheckCircle2 size={15} />
          {message}
          <button onClick={() => setMessage("")} aria-label="关闭提示">
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
              <label>
                <span>分块大小</span>
                <input
                  type="number"
                  min={200}
                  max={4000}
                  value={newChunkSize}
                  onChange={(event) => setNewChunkSize(event.target.value)}
                />
              </label>
              <label>
                <span>相邻重叠</span>
                <input
                  type="number"
                  min={0}
                  max={1000}
                  value={newChunkOverlap}
                  onChange={(event) => setNewChunkOverlap(event.target.value)}
                />
              </label>
              <label>
                <span>分块模式</span>
                <select
                  value={newChunkingMode}
                  onChange={(event) =>
                    setNewChunkingMode(event.target.value as KnowledgeChunkingMode["id"])
                  }
                >
                  {chunkingModes.map((mode) => (
                    <option key={mode.id} value={mode.id}>
                      {mode.name}
                      {mode.recommended ? "（推荐）" : ""}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>索引模式</span>
                <select
                  value={newIndexMode}
                  onChange={(event) =>
                    setNewIndexMode(event.target.value as KnowledgeIndexMode["id"])
                  }
                >
                  {indexModes.map((mode) => (
                    <option key={mode.id} value={mode.id}>
                      {mode.name}
                      {mode.recommended ? "（推荐）" : ""}
                    </option>
                  ))}
                </select>
              </label>
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
              <div className="panel knowledge-overview">
                <div className="panel-head">
                  <div>
                    <span className="eyebrow">当前知识库</span>
                    <h3>{selected.name}</h3>
                  </div>
                  <span className="chip success">
                    {selected.scope === "workspace" ? "当前工作区" : selected.scope}
                  </span>
                </div>
                <div className="knowledge-overview-row">
                  <span className="knowledge-overview-icon blue">
                    <FileText size={16} />
                  </span>
                  <span>
                    <b>文档数</b>
                    <small>已完成入库的资料</small>
                  </span>
                  <strong>{selected.document_count}</strong>
                </div>
                <div className="knowledge-overview-row">
                  <span className="knowledge-overview-icon purple">
                    <ListChecks size={16} />
                  </span>
                  <span>
                    <b>检索片段</b>
                    <small>当前配置生成的 Chunk 数量</small>
                  </span>
                  <strong>{selected.chunk_count}</strong>
                </div>
                <div className="knowledge-overview-row editable">
                  <span className="knowledge-overview-icon green">
                    <SlidersHorizontal size={16} />
                  </span>
                  <span>
                    <b>分块大小</b>
                    <small>单个片段最大字符数；修改后会重建当前知识库</small>
                  </span>
                  <input
                    aria-label="分块大小"
                    type="number"
                    min={200}
                    max={4000}
                    value={editChunkSize}
                    onChange={(event) => setEditChunkSize(event.target.value)}
                  />
                  <small className="knowledge-unit">字符</small>
                </div>
                <div className="knowledge-overview-row editable">
                  <span className="knowledge-overview-icon green">
                    <Link2 size={16} />
                  </span>
                  <span>
                    <b>相邻重叠</b>
                    <small>相邻片段保留的上下文长度</small>
                  </span>
                  <input
                    aria-label="相邻重叠"
                    type="number"
                    min={0}
                    max={1000}
                    value={editChunkOverlap}
                    onChange={(event) => setEditChunkOverlap(event.target.value)}
                  />
                  <small className="knowledge-unit">字符</small>
                </div>
                <div className="knowledge-overview-row editable index-mode-row">
                  <span className="knowledge-overview-icon blue">
                    <FileCode2 size={16} />
                  </span>
                  <span>
                    <b>分块模式</b>
                    <small>
                      {chunkingModes.find((mode) => mode.id === editChunkingMode)?.description ||
                        "选择文档分块方式"}
                    </small>
                  </span>
                  <select
                    aria-label="分块模式"
                    value={editChunkingMode}
                    onChange={(event) =>
                      setEditChunkingMode(event.target.value as KnowledgeChunkingMode["id"])
                    }
                  >
                    {chunkingModes.map((mode) => (
                      <option key={mode.id} value={mode.id}>
                        {mode.name}
                        {mode.recommended ? "（推荐）" : ""}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="knowledge-overview-row editable index-mode-row">
                  <span className="knowledge-overview-icon red">
                    <Network size={16} />
                  </span>
                  <span>
                    <b>索引模式</b>
                    <small>
                      {indexModes.find((mode) => mode.id === editIndexMode)?.description ||
                        "选择检索策略"}
                    </small>
                  </span>
                  <select
                    aria-label="索引模式"
                    value={editIndexMode}
                    onChange={(event) =>
                      setEditIndexMode(event.target.value as KnowledgeIndexMode["id"])
                    }
                  >
                    {indexModes.map((mode) => (
                      <option key={mode.id} value={mode.id}>
                        {mode.name}
                        {mode.recommended ? "（推荐）" : ""}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="knowledge-overview-actions">
                  <span>
                    当前提供方：{selected.embedding_provider} · 分块器：{selected.splitter_provider}
                  </span>
                  <button
                    className="primary"
                    disabled={busy === "settings"}
                    onClick={() => void saveSettings()}
                  >
                    <Save size={15} /> {busy === "settings" ? "保存并重建中..." : "保存索引配置"}
                  </button>
                </div>
              </div>
              <div className="knowledge-task-picker panel">
                <label>
                  <span>当前任务</span>
                  <select
                    value={activeTab}
                    onChange={(event) => setActiveTab(event.target.value as typeof activeTab)}
                  >
                    <option value="ask">问知识库</option>
                    <option value="documents">文档管理与分块预览</option>
                    <option value="retrieval">检索测试与历史</option>
                  </select>
                </label>
                <small>
                  {activeTab === "ask"
                    ? "基于当前索引模式回答并返回引用"
                    : activeTab === "documents"
                      ? "添加资料、查看文档和检查 Chunk"
                      : "验证关键词、字符语义或混合召回效果"}
                </small>
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
                        {activeTab === "ask" ? <MessageSquare size={16} /> : <Search size={16} />}{" "}
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
                  <div className="knowledge-query-controls">
                    <label>
                      <span>标签过滤</span>
                      <input
                        value={queryTags}
                        onChange={(event) => setQueryTags(event.target.value)}
                        placeholder="可选，如 TiDB, SQL"
                      />
                    </label>
                    <label>
                      <span>返回片段</span>
                      <select value={topK} onChange={(event) => setTopK(event.target.value)}>
                        {[3, 5, 8, 10].map((value) => (
                          <option key={value} value={value}>
                            Top {value}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="knowledge-threshold-control">
                      <span>
                        相似度阈值 <output>{Number(scoreThreshold).toFixed(2)}</output>
                      </span>
                      <input
                        aria-label="相似度阈值"
                        type="range"
                        min="0"
                        max="1"
                        step="0.05"
                        value={scoreThreshold}
                        onChange={(event) => setScoreThreshold(event.target.value)}
                      />
                    </label>
                    {activeTab === "ask" && (
                      <label className="knowledge-answer-toggle">
                        <input
                          type="checkbox"
                          checked={generateAnswer}
                          onChange={(event) => setGenerateAnswer(event.target.checked)}
                        />
                        <span>生成模型回答</span>
                      </label>
                    )}
                  </div>
                  <div className="knowledge-query-actions">
                    <span>
                      {activeTab === "ask" && generateAnswer
                        ? "回答必须基于下方引用"
                        : "只返回可核验的检索片段"}
                    </span>
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
                        <span className={`chip ${result.confidence === "low" ? "" : "success"}`}>
                          {result.confidence === "high"
                            ? "高置信度"
                            : result.confidence === "medium"
                              ? "中置信度"
                              : "未找到充分证据"}
                        </span>
                      </div>
                      <p>{result.answer}</p>
                      <div className="knowledge-answer-meta">
                        检索模式：{result.retrieval_mode} ·{" "}
                        {result.generation_mode === "model"
                          ? "模型生成"
                          : result.generation_mode === "extractive"
                            ? "抽取式降级"
                            : result.generation_mode === "retrieval-only"
                              ? "仅检索"
                              : "无回答"}
                        {" · "}
                        候选 {result.candidate_count} 条 · 阈值 {result.score_threshold.toFixed(2)}{" "}
                        · {result.retrieval_latency_ms} ms · 查询 ID：
                        {result.query_id}
                      </div>
                      <div className="knowledge-citations">
                        <div className="knowledge-citations-title">
                          <Quote size={14} /> 引用来源（
                          {result.citations.length}）
                        </div>
                        {result.citations.map((citation) => (
                          <div className="knowledge-citation" key={citation.chunk_id}>
                            <div className="citation-rank">{citation.rank}</div>
                            <div>
                              <b>{citation.document_title}</b>
                              <span>{citation.excerpt}</span>
                              <small>
                                相关度 {(citation.score * 100).toFixed(0)}% ·{" "}
                                {citation.retrieval_reason} · 片段 {citation.position + 1}
                              </small>
                              <div className="knowledge-citation-foot">
                                <span>
                                  命中词：
                                  {citation.matched_terms.length
                                    ? citation.matched_terms.join("、")
                                    : "语义相似"}
                                </span>
                                <button
                                  className="text-btn"
                                  onClick={() => {
                                    setActiveTab("documents");
                                    setSelectedDocumentId(citation.document_id);
                                    void loadChunks(selected.id, citation.document_id);
                                  }}
                                >
                                  查看分块 <ChevronRight size={13} />
                                </button>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                      <div className="knowledge-feedback">
                        <span>{feedback === "idle" ? "这次结果是否有帮助？" : "反馈已记录"}</span>
                        <button
                          className={feedback === "helpful" ? "active" : ""}
                          title="有帮助"
                          onClick={() => void submitFeedback(true)}
                          disabled={feedback !== "idle" || busy === "feedback"}
                        >
                          有帮助
                        </button>
                        <button
                          className={feedback === "not-helpful" ? "active negative" : ""}
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
                      {!queries.length && <div className="empty">运行一次检索后显示记录</div>}
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
                        <div
                          className={
                            selectedDocumentId === document.id
                              ? "knowledge-document-row active"
                              : `knowledge-document-row${document.enabled ? "" : " disabled"}`
                          }
                          key={document.id}
                        >
                          <button
                            className="knowledge-document-select"
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
                                {document.source_type} · {document.chunk_count} 个片段 ·{" "}
                                {(document.content_size / 1024).toFixed(1)} KB
                              </span>
                            </div>
                          </button>
                          <span
                            className={`chip ${document.status === "ready" && document.enabled ? "success" : ""}`}
                          >
                            {document.status === "ready"
                              ? document.enabled
                                ? "已就绪"
                                : "已暂停"
                              : document.status === "processing"
                                ? "处理中"
                                : "失败"}
                          </span>
                          <div className="knowledge-document-actions">
                            <button
                              className="icon-btn subtle"
                              title={document.enabled ? "暂停检索" : "参与检索"}
                              aria-label={
                                document.enabled
                                  ? `暂停 ${document.title}`
                                  : `启用 ${document.title}`
                              }
                              disabled={Boolean(busy)}
                              onClick={() => void toggleDocument(document)}
                            >
                              {document.enabled ? <Eye size={14} /> : <EyeOff size={14} />}
                            </button>
                            <button
                              className="icon-btn subtle"
                              title="重新索引"
                              aria-label={`重新索引 ${document.title}`}
                              disabled={Boolean(busy)}
                              onClick={() => void reindexDocument(document)}
                            >
                              <RefreshCw size={14} />
                            </button>
                            <button
                              className="icon-btn subtle danger"
                              title="删除文档"
                              aria-label={`删除 ${document.title}`}
                              disabled={Boolean(busy)}
                              onClick={() => void removeDocument(document)}
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </div>
                      ))}
                      {!documents.length && <div className="empty">尚未添加文档</div>}
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
                      <span className="panel-help">支持 TXT / Markdown / HTML / JSON / SQL</span>
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
                      disabled={busy === "text" || !title.trim() || !content.trim()}
                    >
                      <Plus size={15} /> {busy === "text" ? "入库中..." : "入库文本"}
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
  const categories = ["全部", ...Array.from(new Set(scenarios.map((item) => item.category)))];
  const filtered = scenarios.filter((item) => category === "全部" || item.category === category);
  const selected = scenarios.find((item) => item.id === selectedId) || filtered[0];
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
      const run = await api<ScenarioRun>(`/scenario-runs/${selectedRun.run_id}/${action}`, {
        method: "POST",
      });
      setSelectedRun(run);
      setRuns((current) => current.map((item) => (item.run_id === run.run_id ? run : item)));
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
          <span className="eyebrow">Agent Team · 定时触发 · 任务留痕 · 人工审批</span>
          <h1>场景中心</h1>
          <p className="section-subtitle">
            把多场景探索中的协作模式落成可配置、可运行、可追踪的企业 AI 控制平面。
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
        <Metric label="运行实例" value={String(runs.length)} hint="可追踪任务" tone="green" />
        <Metric
          label="待审批"
          value={String(runs.filter((item) => item.status === "waiting_approval").length)}
          hint="高风险动作已阻断"
          tone="red"
        />
        <Metric label="已接入模式" value="只读优先" hint="Runbook 可扩展" tone="purple" />
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
                className={selected?.id === item.id ? "scenario-card active" : "scenario-card"}
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
                    <span className="panel-help">任务会创建根实例，步骤完成前保留审计和证据。</span>
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
                <button className="primary" onClick={start} disabled={busy || !objective.trim()}>
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
              className={selectedRun?.run_id === run.run_id ? "run-row active" : "run-row"}
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
              {selectedRun.steps.filter((item) => item.status === "completed").length}/
              {selectedRun.steps.length} 步完成 · 审批 {selectedRun.approvals_granted}/
              {selectedRun.approvals_required}
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
  const [directoryPath, setDirectoryPath] = useState("/workspace/data/sql-optimizer");
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
          <span className="eyebrow">AIOps · TiDB Planner · SQLAdvisor 方法</span>
          <h1>SQL 优化</h1>
          <p className="section-subtitle">
            输入 SQL 与表结构，按 TiDB 版本生成可解释的索引、改写和执行计划建议。
          </p>
        </div>
        <div className="sql-actions">
          <label className="primary file-button">
            <UploadCloud size={16} />
            读取 SQL/DDL
            <input type="file" accept=".sql,.ddl,.txt" multiple onChange={upload} />
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
              <button className="secondary" onClick={() => setDirectoryOpen(false)}>
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
          <span className={result.optimizer_mode === "live" ? "chip success" : "chip simulated"}>
            {result.optimizer_mode === "live" ? "真实 EXPLAIN" : "版本模拟"}
          </span>
        </div>
        <div className="result-meta">
          <span>目标版本 {result.requested_version}</span>
          <span>规则包 {result.profile_version}</span>
          <span>置信度 {result.confidence}</span>
          {result.actual_tidb_version && <span>集群 {result.actual_tidb_version}</span>}
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
                  {node.task} · {node.access_object || "root"} · estRows {node.est_rows}
                </span>
                <small>{node.operator_info}</small>
              </div>
            </div>
          ))}
        </div>
        <div className="recommendation-panel panel">
          <div className="panel-head">
            <h3>优化建议</h3>
            <span className="chip success">{result.recommendations.length} 条</span>
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
                {item.evidence.length > 0 && <small>证据：{item.evidence.join(" · ")}</small>}
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
            <a href={source.url} target="_blank" rel="noreferrer" key={source.url}>
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
