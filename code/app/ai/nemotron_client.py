import requests

LLAMA_URL = "http://192.168.2.111:30000"

def query_nemotron(prompt: str, max_tokens: int = 256):
    payload = {
        "model": "local-model",
        "prompt": prompt,
        "max_tokens": max_tokens
    }

    response = requests.post(LLAMA_URL, json=payload)
    return response.json()
