import os
from typing import Any, Dict

import requests

NEMOTRON_URL = os.getenv("NEMOTRON_URL", "http://127.0.0.1:30000/v1/chat/completions")
NEMOTRON_MODEL = os.getenv("NEMOTRON_MODEL", "local-model")
NEMOTRON_TIMEOUT = float(os.getenv("NEMOTRON_TIMEOUT", "90"))


def query_nemotron(prompt: str) -> Dict[str, Any]:
    payload = {
        "model": NEMOTRON_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
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
