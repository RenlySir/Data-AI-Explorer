from __future__ import annotations

import ipaddress
import os
import socket
from datetime import datetime, timezone
from typing import Any, Literal
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from pydantic import BaseModel, Field, SecretStr, field_validator


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


ProviderId = Literal["openai", "deepseek", "qwen", "zhipu", "moonshot", "ollama", "vllm", "custom"]
DeploymentKind = Literal["public", "private"]


class ModelProvider(BaseModel):
    id: ProviderId
    name: str
    deployment: DeploymentKind
    protocol: str = "openai-compatible"
    default_base_url: str
    model_placeholder: str
    api_key_required: bool
    description: str


class ModelConnectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    provider: ProviderId
    deployment: DeploymentKind
    base_url: str = Field(min_length=8, max_length=2048)
    model: str = Field(min_length=1, max_length=200)
    api_key: SecretStr | None = None
    test_on_create: bool = True
    set_default: bool = True

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        parsed = urlparse(value.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("base_url must be an HTTP(S) URL")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("base_url cannot contain credentials, query, or fragment")
        return value.strip().rstrip("/")


class ModelConnection(BaseModel):
    id: str
    name: str
    provider: ProviderId
    provider_name: str
    deployment: DeploymentKind
    protocol: str
    base_url: str
    model: str
    status: Literal["ready", "unverified", "error"]
    is_default: bool = False
    has_credential: bool = False
    capabilities: list[str] = Field(default_factory=lambda: ["chat", "text2sql", "chart-reasoning"])
    last_error: str | None = None
    last_tested_at: str | None = None
    created_at: str


PROVIDERS = [
    ModelProvider(id="openai", name="OpenAI", deployment="public", default_base_url="https://api.openai.com/v1", model_placeholder="输入已开通的模型 ID", api_key_required=True, description="OpenAI 公有云 API"),
    ModelProvider(id="deepseek", name="DeepSeek", deployment="public", default_base_url="https://api.deepseek.com", model_placeholder="deepseek-chat", api_key_required=True, description="DeepSeek 公有云兼容接口"),
    ModelProvider(id="qwen", name="通义千问", deployment="public", default_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1", model_placeholder="qwen-plus", api_key_required=True, description="阿里云百炼兼容接口"),
    ModelProvider(id="zhipu", name="智谱 GLM", deployment="public", default_base_url="https://open.bigmodel.cn/api/paas/v4", model_placeholder="glm-4-plus", api_key_required=True, description="智谱开放平台兼容接口"),
    ModelProvider(id="moonshot", name="Moonshot", deployment="public", default_base_url="https://api.moonshot.cn/v1", model_placeholder="输入已开通的模型 ID", api_key_required=True, description="Moonshot 公有云兼容接口"),
    ModelProvider(id="ollama", name="Ollama", deployment="private", default_base_url="http://host.docker.internal:11434", model_placeholder="qwen2.5:14b", api_key_required=False, description="本机或企业内网 Ollama"),
    ModelProvider(id="vllm", name="vLLM", deployment="private", default_base_url="http://model-gateway.internal:8000/v1", model_placeholder="企业模型 ID", api_key_required=False, description="企业私有化 vLLM 服务"),
    ModelProvider(id="custom", name="OpenAI-Compatible", deployment="private", default_base_url="http://model-gateway.internal/v1", model_placeholder="模型 ID", api_key_required=False, description="TGI、LiteLLM 或企业自建网关"),
]
PROVIDER_BY_ID = {item.id: item for item in PROVIDERS}
MODEL_CONNECTIONS: dict[str, ModelConnection] = {}
MODEL_SECRETS: dict[str, str] = {}


def _host_allowed(base_url: str) -> bool:
    parsed = urlparse(base_url)
    host = (parsed.hostname or "").lower()
    exact = {item.strip().lower() for item in os.getenv("MODEL_ALLOWED_HOSTS", "").split(",") if item.strip()}
    if host in exact:
        return True
    try:
        addresses = {ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(host, None)}
    except (OSError, ValueError):
        return False
    if not addresses or any(address.is_link_local or address.is_multicast or address.is_unspecified for address in addresses):
        return False
    private = all(address.is_private or address.is_loopback for address in addresses)
    if private:
        return os.getenv("MODEL_ALLOW_PRIVATE_HOSTS", "true").lower() in {"1", "true", "yes"}
    return parsed.scheme == "https"


def create_connection(payload: ModelConnectionCreate) -> ModelConnection:
    provider = PROVIDER_BY_ID[payload.provider]
    if payload.deployment != provider.deployment:
        raise ValueError("deployment does not match selected provider")
    if provider.api_key_required and not payload.api_key:
        raise ValueError(f"{provider.name} requires an API Key")
    item = ModelConnection(
        id=f"mdl-{uuid4().hex[:10]}",
        name=payload.name,
        provider=payload.provider,
        provider_name=provider.name,
        deployment=payload.deployment,
        protocol=provider.protocol,
        base_url=payload.base_url,
        model=payload.model,
        status="unverified",
        has_credential=bool(payload.api_key and payload.api_key.get_secret_value()),
        is_default=False,
        created_at=now_iso(),
    )
    MODEL_CONNECTIONS[item.id] = item
    MODEL_SECRETS[item.id] = payload.api_key.get_secret_value() if payload.api_key else ""
    return item


def _models_url(item: ModelConnection) -> str:
    if item.provider == "ollama":
        return item.base_url.rstrip("/") + "/api/tags"
    base = item.base_url.rstrip("/")
    return base + "/models" if base.endswith(("/v1", "/v4")) else base + "/v1/models"


def _chat_url(item: ModelConnection) -> str:
    base = item.base_url.rstrip("/")
    return base + "/chat/completions" if base.endswith(("/v1", "/v4")) else base + "/v1/chat/completions"


def set_default_connection(connection_id: str) -> ModelConnection:
    selected = MODEL_CONNECTIONS[connection_id]
    if selected.status != "ready":
        raise ValueError("only a verified model can be set as default")
    for item_id, item in list(MODEL_CONNECTIONS.items()):
        MODEL_CONNECTIONS[item_id] = item.model_copy(update={"is_default": item_id == connection_id})
    return MODEL_CONNECTIONS[connection_id]


def test_connection(item: ModelConnection, set_default: bool = False) -> ModelConnection:
    if not _host_allowed(item.base_url):
        updated = item.model_copy(update={"status": "error", "last_error": "model host is not allowed", "last_tested_at": now_iso()})
        MODEL_CONNECTIONS[item.id] = updated
        return updated
    headers = {}
    secret = MODEL_SECRETS.get(item.id, "")
    if secret:
        headers["Authorization"] = f"Bearer {secret}"
    try:
        with httpx.Client(timeout=8, follow_redirects=False) as client:
            response = client.get(_models_url(item), headers=headers)
            response.raise_for_status()
            probe = client.post(
                _chat_url(item),
                headers=headers,
                json={
                    "model": item.model,
                    "temperature": 0,
                    "max_tokens": 2,
                    "messages": [{"role": "user", "content": "Reply OK"}],
                },
            )
            probe.raise_for_status()
            payload = probe.json()
            if not isinstance(payload.get("choices"), list) or not payload["choices"]:
                raise ValueError("model response is missing choices")
        updated = item.model_copy(update={"status": "ready", "last_error": None, "last_tested_at": now_iso()})
        MODEL_CONNECTIONS[item.id] = updated
        if set_default or not any(connection.is_default for connection in MODEL_CONNECTIONS.values()):
            return set_default_connection(item.id)
        return updated
    except httpx.HTTPStatusError as exc:
        error = f"model endpoint returned HTTP {exc.response.status_code}"
    except Exception as exc:
        error = f"model connection failed: {exc.__class__.__name__}"
    updated = item.model_copy(update={"status": "error", "last_error": error, "last_tested_at": now_iso()})
    MODEL_CONNECTIONS[item.id] = updated
    return updated


def active_model_config() -> tuple[str, str, str]:
    active = next((item for item in MODEL_CONNECTIONS.values() if item.is_default and item.status == "ready"), None)
    if active:
        return active.base_url, active.model, MODEL_SECRETS.get(active.id, "")
    return (
        os.getenv("MODEL_GATEWAY_BASE_URL", "").strip(),
        os.getenv("MODEL_GATEWAY_MODEL", "").strip(),
        os.getenv("MODEL_GATEWAY_API_KEY", ""),
    )
