# streamlit_chat.py
import os
import json
import streamlit as st
from typing import List, Dict, Any
from app.ai.nemotron_client import query_nemotron
from app.finance import simulator

# Config
NEMOTRON_URL = os.getenv("NEMOTRON_URL", "http://127.0.0.1:30000/v1/chat/completions")
WHATIF_ENDPOINT = None  # not used directly; we call simulator functions locally

st.set_page_config(page_title="RiseArc", layout="wide")
st.title("RiseArc")

# Session state for messages
if "messages" not in st.session_state:
    st.session_state.messages: List[Dict[str, Any]] = [
        {"role": "system", "content": "You are Nemotron, an assistant that uses structured simulator outputs to advise users."}
    ]

# Sidebar controls
with st.sidebar:
    st.header("Controls")
    run_simulator_before_model = st.checkbox("Run simulator before asking Nemotron", value=True)
    include_top_scenarios = st.checkbox("Include top what-if scenarios in prompt", value=True)
    st.markdown("---")
    st.caption("Nemotron must be running and reachable at NEMOTRON_URL.")

# Chat input area
def render_messages():
    for msg in st.session_state.messages[1:]:
        if msg["role"] == "user":
            st.markdown(f"**You**: {msg['content']}")
        else:
            st.markdown(f"**Nemotron**: {msg['content']}")

render_messages()

user_input = st.text_input("Message", key="input", placeholder="Ask about your finances or run a what-if scenario")

def append_message(role: str, content: str):
    st.session_state.messages.append({"role": role, "content": content})

def build_prompt_with_structured_data(user_text: str, baseline: Dict[str, Any], scenarios: List[Dict[str, Any]]):
    """
    Build a compact JSON-wrapped prompt that gives Nemotron:
    - the user question
    - the baseline metrics
    - a few scenarios
    Nemotron is expected to parse the JSON and generate user-facing text.
    """
    payload = {
        "task": "generate_advice_from_structured_simulator",
        "user_question": user_text,
        "baseline": baseline,
        "scenarios": scenarios[:3] if scenarios else []
    }
    return json.dumps(payload)

if st.button("Send") and user_input.strip():
    append_message("user", user_input)

    # Optionally run simulator first
    baseline = None
    scenarios = None
    if run_simulator_before_model:
        # For simplicity, try to parse numbers from the user message; otherwise use defaults
        # This is intentionally conservative: we do not infer complex financials here.
        # Use defaults if parsing fails.
        try:
            # Expect a JSON-like snippet in the message or simple "income:3000 expenses:2500 savings:10000"
            parts = {k: float(v) for k, v in 
                     [p.split(":") for p in user_input.replace(",", " ").split() if ":" in p]}
            income = parts.get("income", 3000.0)
            expenses = parts.get("expenses", 2500.0)
            savings = parts.get("savings", 10000.0)
        except Exception:
            income, expenses, savings = 3000.0, 2500.0, 10000.0

        baseline = simulator.run_simulation(income, expenses, savings)
        scenarios_payload = simulator.generate_what_if_scenarios(income, expenses, savings)
        scenarios = scenarios_payload.get("scenarios", [])

    # Build prompt for Nemotron
    if run_simulator_before_model and include_top_scenarios:
        prompt = build_prompt_with_structured_data(user_input, baseline, scenarios)
    elif run_simulator_before_model:
        prompt = json.dumps({"task": "generate_advice_from_baseline", "user_question": user_input, "baseline": baseline})
    else:
        prompt = json.dumps({"task": "free_text_response", "user_question": user_input})

    # Call Nemotron via your client
    try:
        # query_nemotron should accept a string prompt; adapt if your client expects different shape
        resp = query_nemotron(prompt)
        # If the model returns a nested structure, extract text safely
        model_text = ""
        if isinstance(resp, dict):
            # common shapes: {'choices':[{'message':{'content': '...'}}]}
            choices = resp.get("choices") or []
            if choices:
                first = choices[0]
                if isinstance(first, dict):
                    msg = first.get("message") or first.get("text") or {}
                    if isinstance(msg, dict):
                        model_text = msg.get("content", "") or msg.get("text", "")
                    else:
                        model_text = str(msg)
                else:
                    model_text = str(first)
            else:
                # fallback: stringify whole response
                model_text = json.dumps(resp)
        else:
            model_text = str(resp)
    except Exception as e:
        model_text = f"[Error contacting Nemotron] {e}"

    append_message("assistant", model_text)

    # Rerender messages
    st.experimental_rerun()

# Optional panels for debugging structured outputs
with st.expander("Structured Simulator Output"):
    if "baseline" in locals() and baseline:
        st.subheader("Baseline")
        st.json(baseline)
    if "scenarios" in locals() and scenarios:
        st.subheader("Top Scenarios")
        for s in scenarios:
            st.write(s["name"])
            st.json(s["metrics"])

with st.expander("Conversation JSON"):
    st.json(st.session_state.messages)
