import os
import requests
from typing import Any, Dict, Union

NEMOTRON_URL = os.getenv("NEMOTRON_URL", "http://127.0.0.1:30000/v1/chat/completions")
TIMEOUT = float(os.getenv("NEMOTRON_TIMEOUT", "30"))

def query_nemotron(prompt: str) -> Union[Dict[str, Any], str]:
    """
    Send a prompt to the local Nemotron HTTP endpoint and return the parsed JSON
    or a fallback string on error. Keep this minimal so other code can import it.
    """
    payload = {"model": "local-model", "messages": [{"role": "user", "content": prompt}]}
    try:
        resp = requests.post(NEMOTRON_URL, json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return f"[nemotron error] {e}"
