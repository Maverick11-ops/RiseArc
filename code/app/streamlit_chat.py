import html
import json
import os
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests
import streamlit as st
import streamlit.components.v1 as components

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

CHAT_STORE_PATH = ROOT_DIR / "data" / "chat_sessions.json"

try:
    from app.core.sample_payloads import SAMPLE_REQUEST
except Exception:
    SAMPLE_REQUEST = None

try:
    from app.core.tools import (
        build_timeline,
        clamp,
        clamp_llm_metrics,
        clamp_llm_profile,
        clamp_llm_scenario,
        clamp_llm_savings_total,
        clamp_llm_timeline_stats,
        compute_debt_ratio,
        compute_risk_score,
        compute_runway,
        compute_timeline_stats,
        job_stability_label,
        job_stability_weight,
        total_savings_leaks,
    )
    from app.ai.nemotron_client import extract_text, query_nemotron
except Exception:
    build_timeline = None
    clamp = None
    clamp_llm_metrics = None
    clamp_llm_profile = None
    clamp_llm_scenario = None
    clamp_llm_savings_total = None
    clamp_llm_timeline_stats = None
    compute_debt_ratio = None
    compute_risk_score = None
    compute_runway = None
    compute_timeline_stats = None
    job_stability_label = None
    job_stability_weight = None
    total_savings_leaks = None
    extract_text = None
    query_nemotron = None


DEFAULT_API_URL = os.getenv("RISEARC_API_URL", "http://127.0.0.1:8000/analyze")
JOB_STABILITY_OPTIONS = {
    "Stable": "stable",
    "Medium": "medium",
    "Unstable": "unstable",
}
JOB_STABILITY_LABELS = {value: label for label, value in JOB_STABILITY_OPTIONS.items()}


def inject_css() -> None:
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Sora:wght@300;400;600&display=swap');

:root {
  --bg-1: #0b0f1a;
  --bg-2: #0f172a;
  --panel: rgba(20, 25, 40, 0.72);
  --panel-strong: rgba(20, 25, 40, 0.92);
  --line: rgba(148, 163, 184, 0.2);
  --text: #e2e8f0;
  --muted: #94a3b8;
  --accent: #4f46e5;
  --accent-2: #0ea5e9;
  --good: #22c55e;
  --warn: #f97316;
}

html, body, [class*="st-"] {
  font-family: 'Sora', sans-serif;
  color: var(--text);
}

.stApp {
  background: radial-gradient(circle at 10% 20%, rgba(79, 70, 229, 0.18), transparent 45%),
              radial-gradient(circle at 80% 10%, rgba(14, 165, 233, 0.15), transparent 35%),
              linear-gradient(160deg, var(--bg-1), var(--bg-2));
}

[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(11, 15, 26, 0.98), rgba(15, 23, 42, 0.98));
  border-right: 1px solid rgba(148, 163, 184, 0.18);
  min-width: 280px;
}

[data-testid="stSidebar"] .sidebar-brand {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 1.2rem;
  letter-spacing: 0.02em;
  margin-bottom: 1rem;
}

[data-testid="stSidebar"] div[role="radiogroup"] > label {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 0.4rem;
  padding: 0.5rem 0.75rem;
  border-radius: 12px;
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(148, 163, 184, 0.18);
  transition: background 0.2s ease, border 0.2s ease, transform 0.2s ease;
}

[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
  background: rgba(59, 130, 246, 0.12);
  transform: translateX(2px);
}

[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
  background: rgba(79, 70, 229, 0.25);
  border: 1px solid rgba(79, 70, 229, 0.5);
}

div[role="tooltip"], div[data-baseweb="tooltip"] {
  display: none !important;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.35rem 0.6rem;
  border-radius: 999px;
  font-size: 0.75rem;
  border: 1px solid rgba(148, 163, 184, 0.25);
  background: rgba(15, 23, 42, 0.6);
  color: var(--muted);
}

.status-pill.ready {
  color: #c7f9cc;
  border-color: rgba(34, 197, 94, 0.4);
}

.section {
  margin-top: 1.2rem;
  margin-bottom: 1.2rem;
}

h1, h2, h3, h4 {
  font-family: 'Space Grotesk', sans-serif;
  letter-spacing: -0.5px;
}

.hero {
  background: linear-gradient(135deg, rgba(79, 70, 229, 0.16), rgba(14, 165, 233, 0.12));
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 28px 32px;
  box-shadow: 0 20px 60px rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(12px);
}

.hero-title {
  font-size: 2.2rem;
  margin-bottom: 0.4rem;
}

.page-title {
  font-size: 1.8rem;
  font-weight: 700;
  margin: 0.4rem 0 0.2rem 0;
}

.page-subtitle {
  color: var(--muted);
  margin-bottom: 0.8rem;
}

.hero-subtitle {
  color: var(--muted);
  font-size: 1rem;
  max-width: 720px;
}

.badge {
  display: inline-block;
  padding: 4px 10px;
  font-size: 0.75rem;
  border-radius: 999px;
  background: rgba(79, 70, 229, 0.18);
  color: #c7d2fe;
  border: 1px solid rgba(79, 70, 229, 0.35);
  margin-bottom: 12px;
}

.card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 18px 18px 16px 18px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.35);
  backdrop-filter: blur(10px);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.45);
}

.card-title {
  font-weight: 600;
  margin-bottom: 6px;
}

.card-text {
  color: var(--muted);
  font-size: 0.9rem;
}

.stButton > button {
  background: linear-gradient(120deg, #4f46e5, #0ea5e9);
  color: white;
  border-radius: 10px;
  padding: 0.55rem 1.1rem;
  border: none;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.stButton > button:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 20px rgba(79, 70, 229, 0.35);
}

div[data-testid="stMetric"] {
  background: var(--panel-strong);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 12px 16px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.4);
}

div[data-testid="stMetric"] label {
  color: var(--muted) !important;
}

.stTextInput input, .stNumberInput input, .stSelectbox select, .stSlider {
  background: rgba(15, 23, 42, 0.6) !important;
  border: 1px solid rgba(148, 163, 184, 0.3) !important;
  color: var(--text) !important;
  border-radius: 10px !important;
}

div[data-testid="stChatMessage"] {
  background: var(--panel-strong);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 8px 12px;
  margin-bottom: 8px;
}

div[data-testid="stChatMessage"] [data-testid="stIcon"],
span.material-symbols-rounded,
span.material-symbols-outlined,
span.material-icons {
  display: none !important;
}

.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 18px 20px;
  margin-bottom: 16px;
}

.field-label {
  font-size: 0.85rem;
  color: var(--muted);
  margin-bottom: 6px;
}

div[data-baseweb="slider"] {
  padding: 6px 8px 2px 8px;
}

div[data-baseweb="input"] {
  padding: 4px 6px;
}

.typing {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--muted);
}

.typing .dots span {
  display: inline-block;
  width: 6px;
  height: 6px;
  background: var(--muted);
  border-radius: 50%;
  margin-right: 3px;
  animation: bounce 1s infinite;
}

.typing .dots span:nth-child(2) { animation-delay: 0.2s; }
.typing .dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.6; }
  40% { transform: translateY(-4px); opacity: 1; }
}

.fade-in {
  animation: fadeUp 0.7s ease;
}

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_tooltip_killer() -> None:
    components.html(
        """
        <script>
        const removeTitles = () => {
          document.querySelectorAll('[title]').forEach((el) => el.removeAttribute('title'));
        };
        removeTitles();
        const observer = new MutationObserver(removeTitles);
        observer.observe(document.body, { childList: true, subtree: true });
        </script>
        """,
        height=0,
    )


def post_analyze(api_url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    resp = requests.post(api_url, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


def sanitize_llm_output(text: str) -> str:
    if not text:
        return ""
    cleaned = html.unescape(text)
    cleaned = unicodedata.normalize("NFKC", cleaned)
    cleaned = cleaned.replace("\u00ad", "")  # soft hyphen
    cleaned = re.sub(r"[\u200B-\u200D\uFEFF]", "", cleaned)
    cleaned = re.sub(r"<br\s*/?>", "\n", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"</(p|div|li|h\d)>", "\n", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    cleaned = cleaned.replace("&nbsp;", " ")
    cleaned = re.sub(r"(\*\*|__)(.*?)\1", r"\2", cleaned)
    cleaned = re.sub(r"(\*|_)([^*_]+)\1", r"\2", cleaned)
    cleaned = cleaned.replace("`", "")
    cleaned = re.sub(r"[\t\r ]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = cleaned.strip()
    return cleaned


def build_prompt(
    profile: Dict[str, Any],
    scenario: Dict[str, Any],
    metrics: Dict[str, float],
    alert: str,
    savings_total: float,
    timeline_stats: Dict[str, float],
    job_stability_value: str,
    job_stability_weight_value: float,
) -> str:
    def money(value: float) -> str:
        return f"${value:,.0f}"

    return f"""
You are RiseArc, a financial assistant powered by Nemotron-3-Nano.
Generate a concise, practical summary based on the user's profile and scenario.

Return in this format:
Summary:
- ...
- ...
- ...
Actions:
- ...
- ...
- ...
Warnings:
- ...

User Profile:
- Monthly income: {money(profile['income_monthly'])}
- Monthly expenses: {money(profile['expenses_monthly'])}
- Savings: {money(profile['savings'])}
- Total debt: {money(profile['debt'])}
- Industry: {profile['industry']}
- Job stability: {job_stability_value} (weight {job_stability_weight_value:+.0f})
- Dependents: {profile['dependents']}

Scenario:
- Months unemployed: {scenario['months_unemployed']}
- Expense cut: {scenario['expense_cut_pct']:.0f}%
- Severance: {money(scenario['severance'])}

Computed Metrics:
- Runway (months): {metrics['runway_months']:.1f}
- Risk score (0-100): {metrics['risk_score']:.0f}
- Adjusted risk score (0-100): {metrics['adjusted_risk_score']:.0f}
- Debt ratio: {metrics['debt_ratio']:.2f}
- Monthly expenses after cut: {money(metrics['monthly_expenses_cut'])}
- Estimated savings leaks (monthly): {money(savings_total)}
- Timeline signals: months_until_zero={timeline_stats['months_until_zero']:.0f}, max_drawdown={money(timeline_stats['max_drawdown'])}, trend_slope={money(timeline_stats['trend_slope'])}

Alert Context:
{alert}
""".strip()


def local_analysis(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not all(
        [
            build_timeline,
            clamp,
            clamp_llm_metrics,
            clamp_llm_profile,
            clamp_llm_scenario,
            clamp_llm_savings_total,
            clamp_llm_timeline_stats,
            compute_debt_ratio,
            compute_risk_score,
            compute_runway,
            compute_timeline_stats,
            job_stability_label,
            job_stability_weight,
            total_savings_leaks,
            query_nemotron,
            extract_text,
        ]
    ):
        raise RuntimeError("Local analysis is unavailable (missing core tool imports).")

    profile = payload["profile"]
    scenario = payload["scenario"]

    monthly_expenses_cut = profile["expenses_monthly"] * (1 - scenario["expense_cut_pct"] / 100.0)
    runway_months = compute_runway(profile["savings"], monthly_expenses_cut, scenario["severance"])
    debt_ratio = compute_debt_ratio(profile["debt"], profile["income_monthly"])
    risk_score = compute_risk_score(
        runway_months, debt_ratio, profile["job_stability"], profile["industry"]
    )

    adjusted_risk = risk_score
    alert = "No alerts yet."
    news_event = payload.get("news_event")
    if news_event:
        delta = news_event["risk_delta"]
        if news_event.get("industry") and news_event["industry"] != profile["industry"]:
            delta *= 0.5
        adjusted_risk = clamp(risk_score + delta, 0.0, 100.0)
        alert = f"Headline: {news_event['headline']} | Risk adjusted by {delta:+.0f} to {adjusted_risk:.0f}."

    timeline = build_timeline(
        profile["savings"], monthly_expenses_cut, scenario["months_unemployed"], scenario["severance"]
    )
    timeline_stats = compute_timeline_stats(timeline)
    savings_total = total_savings_leaks([s["monthly_cost"] for s in payload["subscriptions"]])

    metrics = {
        "monthly_expenses_cut": monthly_expenses_cut,
        "runway_months": runway_months,
        "debt_ratio": debt_ratio,
        "risk_score": risk_score,
        "adjusted_risk_score": adjusted_risk,
    }

    llm_metrics = clamp_llm_metrics(metrics)
    llm_profile = clamp_llm_profile(profile)
    llm_scenario = clamp_llm_scenario(scenario)
    llm_timeline_stats = clamp_llm_timeline_stats(timeline_stats)
    llm_savings_total = clamp_llm_savings_total(savings_total)
    stability_label = job_stability_label(profile["job_stability"])
    stability_weight_value = job_stability_weight(profile["job_stability"])

    prompt = build_prompt(
        llm_profile,
        llm_scenario,
        llm_metrics,
        alert,
        llm_savings_total,
        llm_timeline_stats,
        stability_label,
        stability_weight_value,
    )
    try:
        summary = sanitize_llm_output(extract_text(query_nemotron(prompt)))
    except Exception as exc:
        summary = f"[nemotron error] {exc}"

    return {
        "metrics": metrics,
        "timeline": timeline,
        "savings_total": savings_total,
        "alert": alert,
        "summary": summary,
    }


def get_timeline_stats(timeline: List[float]) -> Dict[str, float]:
    if compute_timeline_stats:
        return compute_timeline_stats(timeline)
    if not timeline:
        return {"months_until_zero": 0.0, "max_drawdown": 0.0, "trend_slope": 0.0}
    months_until_zero = next((i for i, v in enumerate(timeline) if v <= 0), len(timeline) - 1)
    max_drawdown = max(timeline) - min(timeline)
    trend_slope = (timeline[-1] - timeline[0]) / max(len(timeline) - 1, 1)
    return {
        "months_until_zero": float(months_until_zero),
        "max_drawdown": float(max_drawdown),
        "trend_slope": float(trend_slope),
    }


def build_risk_drivers(profile: Dict[str, Any], metrics: Dict[str, float]) -> List[str]:
    drivers: List[str] = []
    runway = metrics.get("runway_months", 0)
    debt_ratio = metrics.get("debt_ratio", 0)
    risk_score = metrics.get("risk_score", 0)

    if runway < 3:
        drivers.append("Low cash runway under 3 months.")
    elif runway < 6:
        drivers.append("Runway below 6 months.")

    if debt_ratio > 0.6:
        drivers.append("Debt load is high relative to annual income.")
    elif debt_ratio > 0.4:
        drivers.append("Debt load is trending elevated.")

    if profile.get("job_stability") == "unstable":
        drivers.append("Income stability is flagged as unstable.")
    elif profile.get("job_stability") == "medium":
        drivers.append("Income stability is moderate (contract/gig).")

    if profile.get("industry") in {"Tech", "Retail", "Hospitality"}:
        drivers.append(f"Industry exposure adds volatility ({profile['industry']}).")

    if risk_score >= 75:
        drivers.append("Overall risk score is high.")
    elif risk_score >= 60:
        drivers.append("Overall risk score is elevated.")

    if not drivers:
        drivers.append("No major risk drivers detected.")

    return drivers


def apply_demo_profile() -> None:
    if not SAMPLE_REQUEST:
        return
    profile = SAMPLE_REQUEST.get("profile", {})
    scenario = SAMPLE_REQUEST.get("scenario", {})
    st.session_state.profile = profile
    st.session_state.show_profile_dialog = False
    if scenario:
        st.session_state["months_unemployed"] = scenario.get("months_unemployed", 6)
        st.session_state["expense_cut"] = scenario.get("expense_cut_pct", 15)
        st.session_state["severance"] = scenario.get("severance", 3000.0)
    if SAMPLE_REQUEST.get("news_event"):
        st.session_state["news_event"] = "Tech layoff wave"
    for item in SAMPLE_REQUEST.get("subscriptions", []):
        key = f"sub_{item['name']}"
        st.session_state[key] = True


def load_chat_sessions() -> List[Dict[str, Any]]:
    if not CHAT_STORE_PATH.exists():
        return []
    try:
        with CHAT_STORE_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data.get("sessions", [])
    except Exception:
        return []


def save_chat_sessions(sessions: List[Dict[str, Any]]) -> None:
    CHAT_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"sessions": sessions}
    with CHAT_STORE_PATH.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def save_current_chat_session(name: str, messages: List[Dict[str, str]]) -> None:
    if not messages:
        return
    sessions = load_chat_sessions()
    chat_id = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    seed_title = ""
    for msg in messages:
        if msg["role"] == "user":
            seed_title = msg["content"]
            break
    title = name.strip() or (seed_title[:32] if seed_title else f"Conversation {len(sessions) + 1}")
    sessions.insert(
        0,
        {
            "id": chat_id,
            "name": title,
            "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
            "messages": messages,
        },
    )
    save_chat_sessions(sessions)


def load_chat_session(chat_id: str) -> List[Dict[str, str]]:
    sessions = load_chat_sessions()
    for session in sessions:
        if session["id"] == chat_id:
            return session.get("messages", [])
    return []


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown('<div class="sidebar-brand">RiseArc</div>', unsafe_allow_html=True)
        st.caption("Financial intelligence console")

        options = ["Landing", "Command Center", "Chat"]
        st.markdown("Navigation")
        for option in options:
            is_active = st.session_state.active_view == option
            button_type = "primary" if is_active else "secondary"
            if st.button(option, use_container_width=True, type=button_type):
                st.session_state.active_view = option

        st.markdown("---")
        if st.button("Edit profile", use_container_width=True):
            st.session_state.show_profile_dialog = True

        if SAMPLE_REQUEST and st.button("Load demo profile", use_container_width=True):
            apply_demo_profile()

        st.markdown("---")
        st.markdown("Chat History")
        sessions = load_chat_sessions()
        session_labels = ["Current session"] + [
            f"{item['name']} - {item['created_at']}" for item in sessions
        ]
        selected_label = st.selectbox("Conversations", session_labels, label_visibility="visible")
        if selected_label != "Current session":
            selected_index = session_labels.index(selected_label) - 1
            selected_id = sessions[selected_index]["id"]
            if st.session_state.chat_session_id != selected_id:
                if st.session_state.chat_session_id == "current":
                    st.session_state.draft_chat = st.session_state.chat_history
                st.session_state.chat_session_id = selected_id
                st.session_state.chat_history = load_chat_session(selected_id)
                st.session_state.active_view = "Chat"
                st.rerun()
        else:
            if st.session_state.chat_session_id != "current":
                st.session_state.chat_history = st.session_state.draft_chat
            st.session_state.chat_session_id = "current"

        st.text_input("Conversation name", key="chat_save_name", placeholder="Budget review")
        if st.button("Save conversation", use_container_width=True):
            save_current_chat_session(st.session_state.chat_save_name, st.session_state.chat_history)
            st.session_state.chat_save_name = ""
            st.rerun()

        if st.button("New conversation", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.chat_session_id = "current"
            st.rerun()

        st.markdown("---")
        mode = "API" if st.session_state.use_api else "Local"
        mode_class = "ready" if st.session_state.use_api else ""
        st.markdown(
            f'<div class="status-pill {mode_class}">Mode: {mode}</div>',
            unsafe_allow_html=True,
        )
        profile_ready = st.session_state.profile is not None
        profile_class = "ready" if profile_ready else ""
        profile_label = "Profile: Ready" if profile_ready else "Profile: Incomplete"
        st.markdown(
            f'<div class="status-pill {profile_class}">{profile_label}</div>',
            unsafe_allow_html=True,
        )
        if query_nemotron:
            st.markdown('<div class="status-pill ready">Nemotron: Ready</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-pill">Nemotron: Offline</div>', unsafe_allow_html=True)


def init_state() -> None:
    if "profile" not in st.session_state:
        st.session_state.profile = None
    if "show_profile_dialog" not in st.session_state:
        st.session_state.show_profile_dialog = True
    if "active_view" not in st.session_state:
        st.session_state.active_view = "Landing"
    if "use_api" not in st.session_state:
        st.session_state.use_api = True
    if "api_url" not in st.session_state:
        st.session_state.api_url = DEFAULT_API_URL
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "chat_session_id" not in st.session_state:
        st.session_state.chat_session_id = "current"
    if "draft_chat" not in st.session_state:
        st.session_state.draft_chat = []
    if "chat_save_name" not in st.session_state:
        st.session_state.chat_save_name = ""
    if "result" not in st.session_state:
        st.session_state.result = None


@st.dialog("Welcome to RiseArc")
def profile_dialog() -> None:
    st.markdown("Fill in your financial profile once. You can update it anytime.")
    profile = st.session_state.profile or {}
    with st.form("profile_form"):
        income = st.number_input(
            "Monthly income", min_value=0.0, value=float(profile.get("income_monthly", 5200.0)), step=100.0
        )
        expenses = st.number_input(
            "Monthly expenses", min_value=0.0, value=float(profile.get("expenses_monthly", 3400.0)), step=100.0
        )
        savings = st.number_input(
            "Savings", min_value=0.0, value=float(profile.get("savings", 12000.0)), step=500.0
        )
        debt = st.number_input(
            "Total debt", min_value=0.0, value=float(profile.get("debt", 15000.0)), step=500.0
        )
        industries = ["Tech", "Finance", "Healthcare", "Education", "Retail", "Manufacturing", "Hospitality", "Other"]
        industry_value = profile.get("industry", "Tech")
        industry_index = industries.index(industry_value) if industry_value in industries else 0
        industry = st.selectbox("Industry", industries, index=industry_index)

        job_keys = list(JOB_STABILITY_OPTIONS.keys())
        current_job = JOB_STABILITY_LABELS.get(profile.get("job_stability", "stable"), "Stable")
        job_index = job_keys.index(current_job) if current_job in job_keys else 0
        job_label = st.selectbox("Job stability", job_keys, index=job_index)
        job_stability = JOB_STABILITY_OPTIONS[job_label]
        dependents = st.number_input("Dependents", min_value=0, value=int(profile.get("dependents", 0)), step=1)
        submitted = st.form_submit_button("Save profile")

    if submitted:
        st.session_state.profile = {
            "income_monthly": income,
            "expenses_monthly": expenses,
            "savings": savings,
            "debt": debt,
            "industry": industry,
            "job_stability": job_stability,
            "dependents": int(dependents),
        }
        st.session_state.show_profile_dialog = False
        st.success("Profile saved.")
        st.rerun()


def render_landing() -> None:
    st.markdown(
        """
        <div class="hero fade-in">
          <span class="badge">Nemotron-3-Nano Powered</span>
          <div class="hero-title">RiseArc Financial Guardian</div>
          <div class="hero-subtitle">
            A proactive financial intelligence layer that simulates risk, surfaces savings, and delivers
            clear actions. Built for speed, clarity, and real-world decisions.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("\n")
    stats = st.columns(3)
    stat_cards = [
        ("60s", "Risk scan turnaround"),
        ("24/7", "Guardian monitoring"),
        ("3x", "Faster scenario planning"),
    ]
    for col, (value, label) in zip(stats, stat_cards):
        with col:
            st.markdown(
                f"""
                <div class="card fade-in">
                  <div class="card-title">{value}</div>
                  <div class="card-text">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("\n")
    cols = st.columns(3)
    cards = [
        ("Survival Simulator", "Stress-test your finances instantly with job-loss and expense-shift scenarios."),
        ("Guardian Alerts", "Risk signals update based on industry news and profile exposure."),
        ("Savings Engine", "Identify recurring leaks and quantify immediate monthly savings."),
    ]
    for col, (title, text) in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div class="card fade-in">
                  <div class="card-title">{title}</div>
                  <div class="card-text">{text}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("\n")
    steps = st.columns(3)
    step_cards = [
        ("1. Profile", "Secure your baseline with one-time onboarding."),
        ("2. Simulate", "Run stress tests in seconds and view the timeline."),
        ("3. Act", "Receive clear steps and guardrails from RiseArc."),
    ]
    for col, (title, text) in zip(steps, step_cards):
        with col:
            st.markdown(
                f"""
                <div class="card fade-in">
                  <div class="card-title">{title}</div>
                  <div class="card-text">{text}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("\n")
    cta_cols = st.columns([2, 1])
    with cta_cols[0]:
        st.markdown(
            """
            <div class="card">
              <div class="card-title">Ready to run your first survival scan?</div>
              <div class="card-text">Enter your profile and let RiseArc do the hard thinking.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with cta_cols[1]:
        if st.button("Enter Command Center", type="primary"):
            st.session_state.active_view = "Command Center"
            st.rerun()


def build_payload_from_state(
    profile: Dict[str, Any],
    months_unemployed: int,
    expense_cut_pct: float,
    severance: float,
    subscriptions: Dict[str, float],
    news_event: Dict[str, Any],
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "profile": profile,
        "scenario": {
            "months_unemployed": months_unemployed,
            "expense_cut_pct": expense_cut_pct,
            "severance": severance,
        },
        "subscriptions": [
            {"name": name, "monthly_cost": cost}
            for name, cost in subscriptions.items()
            if cost > 0
        ],
        "news_event": news_event,
    }
    return payload


def render_command_center() -> None:
    st.subheader("Command Center")

    if not st.session_state.profile:
        st.info("Please complete your profile to unlock the full experience.")
        if st.button("Complete profile"):
            st.session_state.show_profile_dialog = True
        return

    profile = st.session_state.profile

    top = st.columns([2, 1])
    with top[0]:
        st.markdown(
            f"""
            <div class="card">
              <div class="card-title">Profile Snapshot</div>
              <div class="card-text">Income: ${profile['income_monthly']:,.0f} | Expenses: ${profile['expenses_monthly']:,.0f}</div>
              <div class="card-text">Savings: ${profile['savings']:,.0f} | Debt: ${profile['debt']:,.0f}</div>
              <div class="card-text">Industry: {profile['industry']} | Stability: {JOB_STABILITY_LABELS.get(profile['job_stability'], profile['job_stability'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with top[1]:
        if st.button("Edit profile"):
            st.session_state.show_profile_dialog = True

    st.markdown("\n")

    left, right = st.columns([1.2, 1])
    with left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Scenario Controls</div>', unsafe_allow_html=True)
        st.markdown('<div class="card-text">Stress-test your financial runway.</div>', unsafe_allow_html=True)
        st.markdown('<div class="field-label">Months unemployed</div>', unsafe_allow_html=True)
        months_unemployed = st.slider("", min_value=1, max_value=18, value=6, key="months_unemployed", label_visibility="collapsed")
        st.markdown('<div class="field-label">Expense cut (%)</div>', unsafe_allow_html=True)
        expense_cut_pct = st.slider("", min_value=0, max_value=50, value=15, key="expense_cut", label_visibility="collapsed")
        st.markdown('<div class="field-label">Severance / payout</div>', unsafe_allow_html=True)
        severance = st.number_input(
            "",
            min_value=0.0,
            value=3000.0,
            step=500.0,
            key="severance",
            label_visibility="collapsed",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Guardian Signals</div>', unsafe_allow_html=True)
        st.markdown('<div class="card-text">Simulated signals that influence the risk engine.</div>', unsafe_allow_html=True)
        news_events = {
            "None": None,
            "Tech layoff wave": {
                "headline": "Large tech firms announce new layoffs",
                "risk_delta": 15,
                "industry": "Tech",
            },
            "Inflation spike": {
                "headline": "Inflation data surprises to the upside",
                "risk_delta": 10,
                "industry": None,
            },
            "Healthcare hiring boom": {
                "headline": "Hospitals report aggressive hiring plans",
                "risk_delta": -6,
                "industry": "Healthcare",
            },
            "Retail slowdown": {
                "headline": "Retail sales dip for two straight months",
                "risk_delta": 8,
                "industry": "Retail",
            },
        }
        st.markdown('<div class="field-label">Simulate news event</div>', unsafe_allow_html=True)
        event_name = st.selectbox("", list(news_events.keys()), key="news_event", label_visibility="collapsed")
        news_event = news_events[event_name]
        st.markdown('<div class="card-title" style="margin-top:1rem;">Savings Leak Detector</div>', unsafe_allow_html=True)
        subscription_defaults = {
            "Netflix": 15.49,
            "Spotify": 10.99,
            "Amazon Prime": 14.99,
            "Disney+": 10.99,
            "Hulu": 7.99,
            "iCloud+": 2.99,
            "Adobe": 22.99,
            "Gym Membership": 45.00,
        }
        subscriptions: Dict[str, float] = {}
        for name, cost in subscription_defaults.items():
            checked = st.checkbox(f"{name} (${cost:.2f})", value=False, key=f"sub_{name}")
            subscriptions[name] = cost if checked else 0.0
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("\n")

    with st.expander("Connectivity", expanded=False):
        run_cols = st.columns([1, 1])
        with run_cols[0]:
            st.markdown('<div class="field-label">API URL</div>', unsafe_allow_html=True)
            api_url = st.text_input("", value=st.session_state.api_url, key="api_url", label_visibility="collapsed")
        with run_cols[1]:
            st.markdown('<div class="field-label">Use API</div>', unsafe_allow_html=True)
            use_api = st.checkbox("", value=st.session_state.use_api, key="use_api", label_visibility="collapsed")

    disabled = st.session_state.profile is None
    if st.button("Run Analysis", type="primary", disabled=disabled):
        payload = build_payload_from_state(
            profile=profile,
            months_unemployed=int(months_unemployed),
            expense_cut_pct=float(expense_cut_pct),
            severance=severance,
            subscriptions=subscriptions,
            news_event=news_event,
        )

        with st.spinner("Running analysis..."):
            if use_api:
                try:
                    result = post_analyze(api_url, payload)
                    st.session_state.result = result
                    st.success("Analysis complete (API).")
                except Exception as exc:
                    st.warning("API unreachable, falling back to local analysis.")
                    try:
                        result = local_analysis(payload)
                        st.session_state.result = result
                        st.success("Analysis complete (local).")
                    except Exception as local_exc:
                        st.error(f"Request failed: {exc}")
                        st.error(f"Local analysis failed: {local_exc}")
            else:
                try:
                    result = local_analysis(payload)
                    st.session_state.result = result
                    st.success("Analysis complete (local).")
                except Exception as local_exc:
                    st.error(f"Local analysis failed: {local_exc}")

    result = st.session_state.result
    if result:
        metrics = result.get("metrics", {})
        m1, m2, m3 = st.columns(3)
        m1.metric("Runway (months)", f"{metrics.get('runway_months', 0):.1f}")
        m2.metric("Risk score", f"{metrics.get('risk_score', 0):.0f}/100")
        m3.metric("Adjusted risk", f"{metrics.get('adjusted_risk_score', 0):.0f}/100")
        st.progress(min(int(metrics.get("risk_score", 0)), 100))

        st.subheader("Survival Timeline")
        timeline = result.get("timeline", [])
        if timeline:
            st.line_chart(timeline, height=220)

        timeline_stats = get_timeline_stats(timeline)
        risk_drivers = build_risk_drivers(profile, metrics)

        insights_cols = st.columns(2)
        with insights_cols[0]:
            drivers_list = "".join([f"<li>{item}</li>" for item in risk_drivers])
            st.markdown(
                f"""
                <div class="card">
                  <div class="card-title">Risk Drivers</div>
                  <ul class="card-text">{drivers_list}</ul>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with insights_cols[1]:
            st.markdown(
                f"""
                <div class="card">
                  <div class="card-title">Timeline Insights</div>
                  <div class="card-text">Months until zero: {timeline_stats['months_until_zero']:.0f}</div>
                  <div class="card-text">Max drawdown: ${timeline_stats['max_drawdown']:,.0f}</div>
                  <div class="card-text">Trend slope: ${timeline_stats['trend_slope']:,.0f} / month</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.subheader("Alert")
        st.info(result.get("alert", "No alerts yet."))

        st.subheader("Savings Impact")
        st.metric("Potential monthly savings", f"${result.get('savings_total', 0):,.2f}")

        st.subheader("Nemotron Summary")
        summary_text = sanitize_llm_output(result.get("summary", ""))
        st.text(summary_text)


def render_chat() -> None:
    st.subheader("RiseArc Assistant")
    header_cols = st.columns([3, 1])
    with header_cols[0]:
        st.caption("Ask questions and get tailored guidance based on your saved profile.")
    with header_cols[1]:
        if st.button("Clear chat"):
            st.session_state.chat_history = []
            st.rerun()

    if not st.session_state.profile:
        st.info("Complete your profile to unlock the assistant.")
        return

    for message in st.session_state.chat_history:
        avatar = "🤖" if message["role"] == "assistant" else "👤"
        with st.chat_message(message["role"], avatar=avatar):
            st.text(message["content"])

    if not query_nemotron:
        st.warning("Nemotron is not connected. Start the model server to enable chat.")
        return

    quick_input = None
    if not st.session_state.chat_history:
        st.caption("Try a quick prompt:")
        suggestion_cols = st.columns(3)
        suggestions = [
            "How long can I last if income drops by 20%?",
            "What should I prioritize to lower my risk score?",
            "Can I afford a $500 emergency expense next month?",
        ]
        for col, text in zip(suggestion_cols, suggestions):
            with col:
                if st.button(text, use_container_width=True):
                    quick_input = text

    user_input = quick_input or st.chat_input("Ask RiseArc about your finances")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="👤"):
            st.text(user_input)

        profile = st.session_state.profile
        metrics = (st.session_state.result or {}).get("metrics", {})
        llm_profile = clamp_llm_profile(profile) if clamp_llm_profile else profile
        llm_metrics = clamp_llm_metrics(metrics) if (metrics and clamp_llm_metrics) else metrics
        stability_label = (
            job_stability_label(profile["job_stability"]) if job_stability_label else profile["job_stability"]
        )
        stability_weight_value = job_stability_weight(profile["job_stability"]) if job_stability_weight else 0.0
        context_lines: List[str] = [
            "You are RiseArc, a financial assistant. Be concise, practical, and grounded in the user's data.",
            "Provide educational guidance, not professional financial advice.",
            "Always reply to the user in the same font.",
            "Always be helpful, polite, and professional",
            "Always reply to the user in human language, and don't always give a 500 word reply to prompts from the user that don't require that many words in your response.",
            (
                "Profile: income "
                f"{llm_profile['income_monthly']}, expenses {llm_profile['expenses_monthly']}, "
                f"savings {llm_profile['savings']}, debt {llm_profile['debt']}, "
                f"industry {llm_profile['industry']}, stability {stability_label} "
                f"(weight {stability_weight_value:+.0f}), dependents {llm_profile['dependents']}"
            ),
        ]
        if llm_metrics:
            context_lines.append(
                "Latest metrics: runway "
                f"{llm_metrics.get('runway_months', 0):.1f} months, risk {llm_metrics.get('risk_score', 0):.0f}/100, "
                f"adjusted risk {llm_metrics.get('adjusted_risk_score', 0):.0f}/100."
            )

        history_text = "\n".join(
            [f"{m['role'].title()}: {m['content']}" for m in st.session_state.chat_history[-6:]]
        )
        prompt = "\n".join(context_lines + [history_text, "Assistant:"])

        with st.chat_message("assistant", avatar="🤖"):
            typing_placeholder = st.empty()
            typing_placeholder.markdown(
                '<div class="typing">RiseArc is thinking <span class="dots"><span></span><span></span><span></span></span></div>',
                unsafe_allow_html=True,
            )
            try:
                response = sanitize_llm_output(extract_text(query_nemotron(prompt)))
            except Exception as exc:
                response = f"[nemotron error] {exc}"
            typing_placeholder.text(response)

        st.session_state.chat_history.append({"role": "assistant", "content": response})


def main() -> None:
    st.set_page_config(page_title="RiseArc", layout="wide")
    inject_css()
    inject_tooltip_killer()
    init_state()
    render_sidebar()

    if st.session_state.show_profile_dialog:
        profile_dialog()

    st.markdown(f"<div class='page-title'>{st.session_state.active_view}</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-subtitle'>Nemotron-powered financial intelligence</div>", unsafe_allow_html=True)

    if st.session_state.active_view == "Landing":
        render_landing()
    elif st.session_state.active_view == "Command Center":
        render_command_center()
    else:
        render_chat()


if __name__ == "__main__":
    main()
