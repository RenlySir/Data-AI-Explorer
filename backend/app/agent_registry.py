from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

import httpx
from pydantic import BaseModel, Field

from app.model_registry import MODEL_CONNECTIONS, MODEL_SECRETS, ModelConnection, active_model_config
from app.product_catalog import PRODUCT_MODULES, ProductModule


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


ApprovalPolicy = Literal["read_only", "human_approval"]
AgentStatus = Literal["ready", "disabled", "error"]
ModelSource = Literal["registry", "environment"]


class AgentTool(BaseModel):
    id: str
    feature_id: str
    name: str
    api_ref: str
    risk: Literal["read", "propose", "approval"]


class AgentTemplate(BaseModel):
    id: str
    module_id: str
    module_name: str
    name: str
    summary: str
    owner_role: str
    domain: str
    target_page: str | None
    capabilities: list[str]
    tools: list[AgentTool]
    approval_policy: ApprovalPolicy
    system_prompt: str


class AgentCreate(BaseModel):
    template_id: str
    name: str | None = Field(default=None, min_length=1, max_length=100)
    model_connection_id: str | None = None
    enabled: bool = True


class AgentProvisionRequest(BaseModel):
    template_ids: list[str] = Field(default_factory=list)
    model_connection_id: str | None = None


class ModuleAgent(BaseModel):
    id: str
    template_id: str
    module_id: str
    module_name: str
    name: str
    summary: str
    status: AgentStatus
    enabled: bool
    model_source: ModelSource
    model_connection_id: str | None
    model_connection_name: str
    model: str
    capabilities: list[str]
    tools: list[AgentTool]
    approval_policy: ApprovalPolicy
    system_prompt: str
    target_page: str | None
    created_at: str
    updated_at: str
    last_tested_at: str | None = None
    last_invoked_at: str | None = None
    last_error: str | None = None


class AgentProvisionResult(BaseModel):
    requested: int
    created: list[ModuleAgent]
    existing: list[ModuleAgent]
    model_connection_name: str


class AgentEnabledUpdate(BaseModel):
    enabled: bool


class AgentCheck(BaseModel):
    key: str
    label: str
    passed: bool
    detail: str


class AgentTestResult(BaseModel):
    agent_id: str
    passed: bool
    status: AgentStatus
    checks: list[AgentCheck]
    tested_at: str


class AgentInvokeRequest(BaseModel):
    input: str = Field(min_length=1, max_length=4000)


class AgentInvokeResult(BaseModel):
    run_id: str
    agent_id: str
    answer: str
    execution_mode: Literal["advisory"] = "advisory"
    approval_required: bool
    available_tools: list[str]
    created_at: str


MODULE_AGENTS: dict[str, ModuleAgent] = {}

MODULE_TOOL_DEFAULTS: dict[str, list[tuple[str, str, str]]] = {
    "aiops": [
        ("aiops-event-center", "查看事件详情", "GET /api/v1/incidents/{incident_id}"),
        ("aiops-runbook", "查看处置场景", "GET /api/v1/scenarios"),
    ],
    "scenario-command": [
        ("scenario-catalog", "查看场景模板", "GET /api/v1/scenarios"),
        ("scenario-run", "创建场景运行", "POST /api/v1/scenarios/{scenario_id}/runs"),
        ("scenario-run", "查看运行状态", "GET /api/v1/scenario-runs"),
        ("scenario-run", "推进受控步骤", "POST /api/v1/scenario-runs/{run_id}/advance"),
        ("scenario-run", "审批当前步骤", "POST /api/v1/scenario-runs/{run_id}/approve"),
    ],
    "task-approval": [
        ("task-queue", "查看运行任务", "GET /api/v1/scenario-runs"),
    ],
}


def _requires_approval(module: ProductModule) -> bool:
    guarded_terms = ("审批", "人工确认", "二次认证", "回滚")
    return module.domain == "collaboration" or any(
        any(term in guardrail for term in guarded_terms)
        for feature in module.features
        for guardrail in feature.guardrails
    )


def _tool_risk(api_ref: str, approval_policy: ApprovalPolicy) -> Literal["read", "propose", "approval"]:
    methods = api_ref.split(" ", 1)[0].upper()
    if methods == "GET":
        return "read"
    return "approval" if approval_policy == "human_approval" else "propose"


def _template_from_module(module: ProductModule) -> AgentTemplate:
    active_features = [item for item in module.features if item.delivery_state != "planned"]
    approval_policy: ApprovalPolicy = "human_approval" if _requires_approval(module) else "read_only"
    tools = [
        AgentTool(
            id=f"{feature.id}:{index}",
            feature_id=feature.id,
            name=feature.name,
            api_ref=api_ref,
            risk=_tool_risk(api_ref, approval_policy),
        )
        for feature in active_features
        for index, api_ref in enumerate(feature.api_refs, start=1)
    ]
    existing_refs = {item.api_ref for item in tools}
    for feature_id, name, api_ref in MODULE_TOOL_DEFAULTS.get(module.id, []):
        if api_ref in existing_refs:
            continue
        tools.append(
            AgentTool(
                id=f"{feature_id}:default:{len(tools) + 1}",
                feature_id=feature_id,
                name=name,
                api_ref=api_ref,
                risk=_tool_risk(api_ref, approval_policy),
            )
        )
    target_page = next((item.target_page for item in active_features if item.target_page), None)
    safety_rule = (
        "高风险动作只能形成待审批方案，不得声称已经执行；批准后也必须由受控执行器完成。"
        if approval_policy == "human_approval"
        else "默认进行只读分析；写操作只能提出建议，不得声称已经执行。"
    )
    capabilities = [item.name for item in active_features]
    return AgentTemplate(
        id=f"tpl-{module.id}",
        module_id=module.id,
        module_name=module.name,
        name=f"{module.name} Agent",
        summary=module.summary,
        owner_role=module.owner_role,
        domain=module.domain,
        target_page=target_page,
        capabilities=capabilities,
        tools=tools,
        approval_policy=approval_policy,
        system_prompt=(
            f"你是 Aegis AI 的{module.name}专用 Agent，责任角色为{module.owner_role}。"
            f"你的业务范围是：{module.summary} "
            f"仅能围绕已授权能力工作：{'、'.join(capabilities)}。"
            "只能引用允许工具清单，不得虚构工具结果、数据、告警或执行状态。"
            f"{safety_rule} 回答应先给结论，再给证据、下一步和风险边界。"
        ),
    )


AGENT_TEMPLATES = [_template_from_module(module) for module in PRODUCT_MODULES]
AGENT_TEMPLATE_BY_ID = {item.id: item for item in AGENT_TEMPLATES}


def _active_registry_connection() -> ModelConnection | None:
    return next(
        (item for item in MODEL_CONNECTIONS.values() if item.is_default and item.status == "ready"),
        None,
    )


def resolve_model(connection_id: str | None = None) -> tuple[ModelSource, ModelConnection | None, str, str]:
    if connection_id:
        connection = MODEL_CONNECTIONS.get(connection_id)
        if not connection:
            raise ValueError("model connection not found")
        if connection.status != "ready":
            raise ValueError("model connection must be verified before creating an agent")
        return "registry", connection, connection.name, connection.model or "服务默认模型"

    connection = _active_registry_connection()
    if connection:
        return "registry", connection, connection.name, connection.model or "服务默认模型"

    endpoint, model, _ = active_model_config()
    if endpoint and model:
        return "environment", None, "环境模型网关", model
    raise ValueError("connect and activate a verified model before creating an agent")


def create_agent(payload: AgentCreate) -> tuple[ModuleAgent, bool]:
    template = AGENT_TEMPLATE_BY_ID.get(payload.template_id)
    if not template:
        raise KeyError("agent template not found")

    source, connection, connection_name, model = resolve_model(payload.model_connection_id)
    existing = next((item for item in MODULE_AGENTS.values() if item.template_id == template.id), None)
    if existing:
        return existing, False

    timestamp = now_iso()
    item = ModuleAgent(
        id=f"agt-{uuid4().hex[:10]}",
        template_id=template.id,
        module_id=template.module_id,
        module_name=template.module_name,
        name=payload.name or template.name,
        summary=template.summary,
        status="ready" if payload.enabled else "disabled",
        enabled=payload.enabled,
        model_source=source,
        model_connection_id=connection.id if connection else None,
        model_connection_name=connection_name,
        model=model,
        capabilities=template.capabilities,
        tools=template.tools,
        approval_policy=template.approval_policy,
        system_prompt=template.system_prompt,
        target_page=template.target_page,
        created_at=timestamp,
        updated_at=timestamp,
    )
    MODULE_AGENTS[item.id] = item
    return item, True


def provision_agents(payload: AgentProvisionRequest) -> AgentProvisionResult:
    template_ids = payload.template_ids or [item.id for item in AGENT_TEMPLATES]
    unknown = sorted(set(template_ids) - set(AGENT_TEMPLATE_BY_ID))
    if unknown:
        raise KeyError(f"agent template not found: {', '.join(unknown)}")

    _, _, connection_name, _ = resolve_model(payload.model_connection_id)
    created: list[ModuleAgent] = []
    existing: list[ModuleAgent] = []
    for template_id in dict.fromkeys(template_ids):
        item, was_created = create_agent(
            AgentCreate(template_id=template_id, model_connection_id=payload.model_connection_id)
        )
        (created if was_created else existing).append(item)
    return AgentProvisionResult(
        requested=len(dict.fromkeys(template_ids)),
        created=created,
        existing=existing,
        model_connection_name=connection_name,
    )


def set_agent_enabled(item: ModuleAgent, enabled: bool) -> ModuleAgent:
    updated = item.model_copy(
        update={
            "enabled": enabled,
            "status": "ready" if enabled else "disabled",
            "updated_at": now_iso(),
            "last_error": None if enabled else item.last_error,
        }
    )
    MODULE_AGENTS[item.id] = updated
    return updated


def _bound_model(item: ModuleAgent) -> tuple[str, str, str]:
    if item.model_source == "registry":
        connection = MODEL_CONNECTIONS.get(item.model_connection_id or "")
        if not connection or connection.status != "ready":
            raise ValueError("the bound model connection is no longer ready")
        base = connection.base_url.rstrip("/")
        url = base + "/chat/completions" if base.endswith(("/v1", "/v4")) else base + "/v1/chat/completions"
        return url, connection.model, MODEL_SECRETS.get(connection.id, "")
    endpoint, model, secret = active_model_config()
    if not endpoint or not model:
        raise ValueError("the environment model gateway is no longer ready")
    base = endpoint.rstrip("/")
    url = base + "/chat/completions" if base.endswith(("/v1", "/v4")) else base + "/v1/chat/completions"
    return url, model, secret


def test_agent(item: ModuleAgent) -> AgentTestResult:
    timestamp = now_iso()
    try:
        _bound_model(item)
        model_ready = True
        model_detail = f"已绑定 {item.model_connection_name} / {item.model}"
    except ValueError as exc:
        model_ready = False
        model_detail = str(exc)
    checks = [
        AgentCheck(key="enabled", label="Agent 已启用", passed=item.enabled, detail="可接收任务" if item.enabled else "当前已停用"),
        AgentCheck(key="model", label="模型连接可用", passed=model_ready, detail=model_detail),
        AgentCheck(key="capabilities", label="模块能力已装配", passed=bool(item.capabilities), detail=f"{len(item.capabilities)} 项能力"),
        AgentCheck(key="policy", label="安全策略已生效", passed=True, detail="人工审批" if item.approval_policy == "human_approval" else "只读分析"),
    ]
    passed = all(check.passed for check in checks)
    status: AgentStatus = "ready" if passed else ("disabled" if not item.enabled else "error")
    updated = item.model_copy(
        update={
            "status": status,
            "last_tested_at": timestamp,
            "updated_at": timestamp,
            "last_error": None if passed else next(check.detail for check in checks if not check.passed),
        }
    )
    MODULE_AGENTS[item.id] = updated
    return AgentTestResult(agent_id=item.id, passed=passed, status=status, checks=checks, tested_at=timestamp)


def invoke_agent(item: ModuleAgent, payload: AgentInvokeRequest) -> AgentInvokeResult:
    if not item.enabled:
        raise ValueError("agent is disabled")
    url, model, secret = _bound_model(item)
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["Authorization"] = f"Bearer {secret}"
    request_body: dict[str, Any] = {
        "messages": [
            {"role": "system", "content": item.system_prompt},
            {
                "role": "user",
                "content": (
                    f"用户任务：{payload.input.strip()}\n"
                    f"允许工具：{', '.join(tool.api_ref for tool in item.tools) or '当前无可调用工具，只能给出分析建议'}\n"
                    "当前为建议模式，不要声称已经调用工具。"
                ),
            },
        ],
        "temperature": 0.2,
        "max_tokens": 800,
    }
    if model:
        request_body["model"] = model
    try:
        with httpx.Client(timeout=30, follow_redirects=False) as client:
            response = client.post(url, headers=headers, json=request_body)
            response.raise_for_status()
            result = response.json()
        answer = result["choices"][0]["message"]["content"].strip()
        if not answer:
            raise ValueError("model returned an empty answer")
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"model endpoint returned HTTP {exc.response.status_code}") from exc
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise RuntimeError("model returned an invalid chat response") from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(f"model request failed: {exc.__class__.__name__}") from exc

    timestamp = now_iso()
    MODULE_AGENTS[item.id] = item.model_copy(
        update={"last_invoked_at": timestamp, "updated_at": timestamp, "last_error": None}
    )
    return AgentInvokeResult(
        run_id=f"run-{uuid4().hex[:10]}",
        agent_id=item.id,
        answer=answer,
        approval_required=item.approval_policy == "human_approval",
        available_tools=[tool.api_ref for tool in item.tools],
        created_at=timestamp,
    )


def mark_model_unavailable(connection_id: str) -> None:
    timestamp = now_iso()
    for agent_id, item in list(MODULE_AGENTS.items()):
        if item.model_connection_id == connection_id:
            MODULE_AGENTS[agent_id] = item.model_copy(
                update={
                    "status": "error",
                    "updated_at": timestamp,
                    "last_error": "the bound model connection was removed",
                }
            )
