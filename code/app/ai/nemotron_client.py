import os
from typing import Any, Dict
from urllib.parse import urlparse, urlunparse

import requests

NEMOTRON_URL = os.getenv("NEMOTRON_URL", "http://127.0.0.1:30000/v1/chat/completions")
NEMOTRON_MODEL = os.getenv("NEMOTRON_MODEL", "local-model")
NEMOTRON_TIMEOUT = float(os.getenv("NEMOTRON_TIMEOUT", "90"))
NEMOTRON_HEALTH_TIMEOUT = float(os.getenv("NEMOTRON_HEALTH_TIMEOUT", "1.2"))


def _base_url() -> str:
    parsed = urlparse(NEMOTRON_URL)
    base = parsed._replace(path="", params="", query="", fragment="")
    return urlunparse(base)


def check_nemotron_online(timeout: float | None = None) -> bool:
    base = _base_url().rstrip("/")
    health_timeout = timeout if timeout is not None else NEMOTRON_HEALTH_TIMEOUT
    for path in ("/health", "/v1/models"):
        try:
            resp = requests.get(f"{base}{path}", timeout=health_timeout)
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
    payload = {
        "model": NEMOTRON_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2 if temperature is None else float(temperature),
    }
    if max_tokens is not None:
        payload["max_tokens"] = int(max_tokens)
    resp = requests.post(NEMOTRON_URL, json=payload, timeout=NEMOTRON_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def extract_text(response: Dict[str, Any]) -> str:
    choices = response.get("choices") or []
    if not choices:
        return str(response)
    choice = choices[0]
    message = choice.get("message") if isinstance(choice, dict) else None
    if isinstance(message, dict):
        return message.get("content", "").strip()
    text = choice.get("text") if isinstance(choice, dict) else None
    if text:
        return str(text).strip()
    return str(response)
