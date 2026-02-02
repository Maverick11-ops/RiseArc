# streamlit_chat.py
import os
import sys
import json
import streamlit as st
from typing import List, Dict, Any

# --- Robust import handling -------------------------------------------------
# Ensure project root is on sys.path so `app` package imports work when Streamlit runs.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Try to import simulator and nemotron client with clear fallbacks
_simulator = None
_query_nemotron = None

try:
    from finance import simulator as _simulator  # type: ignore
except Exception as e:
    _simulator = None
    _simulator_import_error = e

try:
    # Expect query_nemotron(prompt: str) -> Union[str, dict]
    from ai.nemotron_client import query_nemotron as _query_nemotron  # type: ignore
except Exception as e:
    _query_nemotron = None
    _nemotron_import_error = e

# Provide a safe placeholder for query_nemotron if the real client isn't available
def _placeholder_query_nemotron(prompt: str) -> str:
    return (
        "[Nemotron client not available] Install or start your model server and ensure "
        "app.ai.nemotron_client.query_nemotron is importable. Prompt was: "
        + (prompt if len(prompt) < 1000 else prompt[:1000] + "...")
    )

if _query_nemotron is None:
    query_nemotron = _placeholder_query_nemotron
else:
    query_nemotron = _query_nemotron

# --- Streamlit UI ----------------------------------------------------------
st.set_page_config(page_title="RiseArc Chat", layout="wide")
st.title("RiseArc Chat")

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
    st.caption("Nemotron must be running and reachable at NEMOTRON_URL for model responses.")

# Show import errors (if any) so you can fix them quickly
if _simulator is None:
    st.sidebar.error("Simulator import failed. Ensure `app.finance.simulator` exists and project root is correct.")
    if "_simulator_import_error" in globals():
        st.sidebar.caption(str(_simulator_import_error))

if _query_nemotron is None:
    st.sidebar.warning("Nemotron client not importable. Model responses will use a placeholder until fixed.")
    if "_nemotron_import_error" in globals():
        st.sidebar.caption(str(_nemotron_import_error))

# Helper functions
def append_message(role: str, content: str):
    st.session_state.messages.append({"role": role, "content": content})

def render_messages():
    for msg in st.session_state.messages[1:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            st.markdown(f"**You**: {content}")
        elif role in ("assistant", "nemotron"):
            st.markdown(f"**Nemotron**: {content}")
        else:
            st.markdown(f"**{role}**: {content}")

def build_prompt_with_structured_data(user_text: str, baseline: Dict[str, Any], scenarios: List[Dict[str, Any]]):
    payload = {
        "task": "generate_advice_from_structured_simulator",
        "user_question": user_text,
        "baseline": baseline,
        "scenarios": scenarios[:3] if scenarios else []
    }
    return json.dumps(payload)

# Main chat area
render_messages()
user_input = st.text_input("Message", key="input", placeholder="Ask about your finances or run a what-if scenario")

if st.button("Send") and user_input.strip():
    append_message("user", user_input)

    baseline = None
    scenarios = None

    # Run simulator locally if available
    if run_simulator_before_model and _simulator is not None:
        # Try to parse simple inline numbers from the user message; fallback to defaults
        try:
            parts = {k: float(v) for k, v in 
                     [p.split(":") for p in user_input.replace(",", " ").split() if ":" in p]}
            income = parts.get("income", 3000.0)
            expenses = parts.get("expenses", 2500.0)
            savings = parts.get("savings", 10000.0)
        except Exception:
            income, expenses, savings = 3000.0, 2500.0, 10000.0

        # Use the simulator functions directly
        try:
            baseline = _simulator.run_simulation(income, expenses, savings)
            scenarios_payload = _simulator.generate_what_if_scenarios(income, expenses, savings)
            scenarios = scenarios_payload.get("scenarios", [])
        except Exception as e:
            baseline = None
            scenarios = None
            append_message("assistant", f"[Simulator error] {e}")

    # Build prompt for Nemotron
    if run_simulator_before_model and baseline is not None and include_top_scenarios:
        prompt = build_prompt_with_structured_data(user_input, baseline, scenarios)
    elif run_simulator_before_model and baseline is not None:
        prompt = json.dumps({"task": "generate_advice_from_baseline", "user_question": user_input, "baseline": baseline})
    else:
        prompt = json.dumps({"task": "free_text_response", "user_question": user_input})

    # Call Nemotron (or placeholder)
    try:
        resp = query_nemotron(prompt)
        # Normalize response to text
        model_text = ""
        if isinstance(resp, dict):
            # Common OpenAI-like shape
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
                model_text = json.dumps(resp)
        else:
            model_text = str(resp)
    except Exception as e:
        model_text = f"[Error contacting Nemotron] {e}"

    append_message("assistant", model_text)
    st.experimental_rerun()

# Debug panels
with st.expander("Structured Simulator Output"):
    if baseline:
        st.subheader("Baseline")
        st.json(baseline)
    if scenarios:
        st.subheader("Top Scenarios")
        for s in scenarios:
            st.write(s.get("name", "scenario"))
            st.json(s.get("metrics", {}))

with st.expander("Conversation JSON"):
    st.json(st.session_state.messages)
