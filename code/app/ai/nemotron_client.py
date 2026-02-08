import os
from typing import Any, Dict
from urllib.parse import urlparse, urlunparse

import requests

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - handled at runtime
    OpenAI = None

NIM_BASE_URL = os.getenv("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
NEMOTRON_MODEL = os.getenv("NEMOTRON_MODEL", "nvidia/nemotron-3-nano-30b-a3b")
NEMOTRON_TIMEOUT = float(os.getenv("NEMOTRON_TIMEOUT", "90"))
NEMOTRON_HEALTH_TIMEOUT = float(os.getenv("NEMOTRON_HEALTH_TIMEOUT", "2.0"))
NEMOTRON_API_KEY = os.getenv("NVIDIA_API_KEY") or os.getenv("NEMOTRON_API_KEY") or os.getenv("OPENAI_API_KEY")
NEMOTRON_DEFAULT_MAX_TOKENS = int(os.getenv("NEMOTRON_DEFAULT_MAX_TOKENS", "800"))


def _base_url() -> str:
    parsed = urlparse(NIM_BASE_URL)
    path = parsed.path.rstrip("/")
    if path.endswith("/chat/completions"):
        path = path[: -len("/chat/completions")]
    elif path.endswith("/completions"):
        path = path[: -len("/completions")]
    base = parsed._replace(path=path, params="", query="", fragment="")
    return urlunparse(base)


def _get_client() -> OpenAI | None:
    if OpenAI is None:
        return None
    return OpenAI(base_url=_base_url(), api_key=NEMOTRON_API_KEY)


def check_nemotron_online(timeout: float | None = None) -> bool:
    base = _base_url().rstrip("/")
    health_timeout = timeout if timeout is not None else NEMOTRON_HEALTH_TIMEOUT
    headers = {"Authorization": f"Bearer {NEMOTRON_API_KEY}"} if NEMOTRON_API_KEY else {}
    for path in ("/health", "/v1/models", "/models"):
        try:
            resp = requests.get(f"{base}{path}", timeout=health_timeout, headers=headers)
            if resp.ok:
                return True
        except Exception:
            continue
    return False


def query_nemotron(
    prompt: str,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> Dict[str, Any]:
    client = _get_client()
    if client is None:
        raise RuntimeError("OpenAI client is unavailable. Install the openai package.")
    if not NEMOTRON_API_KEY:
        raise RuntimeError("Missing NVIDIA_API_KEY. Set the environment variable and restart the app.")

    extra_body: Dict[str, Any] = {}
    reasoning_budget = os.getenv("NEMOTRON_REASONING_BUDGET")
    if reasoning_budget is None or reasoning_budget == "":
        extra_body["reasoning_budget"] = 0
    else:
        extra_body["reasoning_budget"] = int(reasoning_budget)
    enable_thinking = os.getenv("NEMOTRON_ENABLE_THINKING", "").lower() in {"1", "true", "yes"}
    extra_body["chat_template_kwargs"] = {"enable_thinking": enable_thinking}

    token_limit = int(max_tokens) if max_tokens is not None else NEMOTRON_DEFAULT_MAX_TOKENS
    response = client.chat.completions.create(
        model=NEMOTRON_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2 if temperature is None else float(temperature),
        max_tokens=token_limit,
        extra_body=extra_body,
        timeout=NEMOTRON_TIMEOUT,
    )
    try:
        return response.model_dump()
    except AttributeError:
        return response  # type: ignore[return-value]


def extract_text(response: Dict[str, Any]) -> str:
    choices = response.get("choices") or []
    if not choices:
        return str(response)
    choice = choices[0]
    message = choice.get("message") if isinstance(choice, dict) else None
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        reasoning = message.get("reasoning")
        if isinstance(reasoning, str) and reasoning.strip():
            return reasoning.strip()
        reasoning = message.get("reasoning_content")
        if isinstance(reasoning, str) and reasoning.strip():
            return reasoning.strip()
        return ""
    text = choice.get("text") if isinstance(choice, dict) else None
    if text:
        return str(text).strip()
    return str(response)
