import html
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st
import streamlit.components.v1 as components

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))


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
        adjust_risk_for_scenario,
        job_stability_label,
        job_stability_weight,
        total_savings_leaks,
    )
    from app.ai.nemotron_client import check_nemotron_online, extract_text, query_nemotron
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
    adjust_risk_for_scenario = None
    job_stability_label = None
    job_stability_weight = None
    total_savings_leaks = None
    extract_text = None
    query_nemotron = None
    check_nemotron_online = None


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
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,400..700,0..1,-50..200&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,400..700,0..1,-50..200&display=swap');
@import url('https://fonts.googleapis.com/icon?family=Material+Icons');

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

div.block-container {
  padding-top: 2.2rem;
  padding-bottom: 2.2rem;
}

[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(11, 15, 26, 0.98), rgba(15, 23, 42, 0.98));
  border-right: 1px solid rgba(148, 163, 184, 0.18);
  min-width: 280px;
}

[data-testid="stSidebar"] .block-container {
  padding: 1.6rem 1.2rem 2rem 1.2rem;
}

[data-testid="stSidebar"] header,
[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"],
[data-testid="stSidebar"] [data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebar"] button[aria-label*="keyboard"],
[data-testid="stSidebar"] button[title*="keyboard"] {
  display: none !important;
  pointer-events: none !important;
  width: 0 !important;
  height: 0 !important;
  overflow: hidden !important;
}

[data-testid="stSidebar"] .sidebar-brand {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 1.2rem;
  letter-spacing: 0.02em;
  margin-bottom: 1rem;
}

div[role="tooltip"], div[data-baseweb="tooltip"] {
  display: none !important;
}

*[title*="keyboard_double_arrow"],
*[title*="keyboard-double-arrow"],
*[aria-label*="keyboard_double_arrow"],
*[aria-label*="keyboard-double-arrow"] {
  display: none !important;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.2rem 0.5rem;
  border-radius: 999px;
  font-size: 0.8rem;
  border: 1px solid rgba(148, 163, 184, 0.25);
  background: rgba(15, 23, 42, 0.6);
  color: var(--muted);
}

.status-stack {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  gap: 0.6rem;
  margin-top: 0.6rem;
}

.status-pill.ready {
  color: #c7f9cc;
  border-color: rgba(34, 197, 94, 0.4);
}

.section {
  margin-top: 1.8rem;
  margin-bottom: 1.8rem;
}

h1, h2, h3, h4 {
  font-family: 'Space Grotesk', sans-serif;
  letter-spacing: -0.5px;
}

.hero {
  background: linear-gradient(135deg, rgba(79, 70, 229, 0.16), rgba(14, 165, 233, 0.12));
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 32px 36px;
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
  margin: 0.8rem 0 0.4rem 0;
}

.page-subtitle {
  color: var(--muted);
  margin-bottom: 1.2rem;
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
  padding: 22px 22px 20px 22px;
  margin-bottom: 16px;
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
  margin-bottom: 8px;
}

.card-text {
  color: var(--muted);
  font-size: 0.9rem;
  margin-bottom: 6px;
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

.stTextInput, .stNumberInput, .stSelectbox, .stSlider {
  margin-bottom: 0.7rem;
}

div[data-testid="stChatMessage"] {
  background: var(--panel-strong);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 12px 16px;
  margin-bottom: 12px;
}

div[data-testid="stChatMessage"] [data-testid="stIcon"] {
  display: none !important;
}

span.material-symbols-rounded,
span.material-symbols-outlined,
span.material-icons {
  font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons', sans-serif !important;
  font-variation-settings: 'FILL' 0, 'wght' 500, 'GRAD' 0, 'opsz' 24;
}

button[data-testid="stSidebarCollapseButton"] span {
  display: none !important;
}

button[data-testid="stSidebarCollapseButton"]::after {
  content: "";
  width: 8px;
  height: 8px;
  border-right: 2px solid var(--muted);
  border-bottom: 2px solid var(--muted);
  transform: rotate(45deg);
  display: inline-block;
}

button[data-testid="stSidebarCollapseButton"] svg,
button[data-testid="stSidebarCollapseButton"] i {
  display: none !important;
}

button[data-testid="stSidebarCollapseButton"] {
  font-size: 0 !important;
}

button[data-testid="stSidebarCollapseButton"] * {
  display: none !important;
}

button[data-testid="stSidebarCollapseButton"] {
  color: transparent !important;
}

button[data-testid="stSidebarCollapseButton"] {
  display: none !important;
}

[data-testid="stSidebarCollapsedControl"] {
  display: none !important;
}

.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 22px 24px;
  margin-bottom: 20px;
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

.summary-block {
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.16), rgba(79, 70, 229, 0.12));
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 16px;
  padding: 22px 24px;
  margin-top: 12px;
  margin-bottom: 18px;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.35);
}

.summary-title {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 1.1rem;
  margin-bottom: 0.4rem;
}

.summary-text {
  color: var(--text);
  font-family: 'Sora', sans-serif;
  font-variant-ligatures: none;
  font-feature-settings: "liga" 0;
  white-space: pre-wrap;
  line-height: 1.55;
}

.stMarkdown p {
  margin-bottom: 0.8rem;
}

.stMarkdown ul,
.stMarkdown ol {
  margin-top: 0.4rem;
  margin-bottom: 0.8rem;
}

.section-title {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 1.05rem;
  margin-bottom: 0.4rem;
}

.section-subtitle {
  color: var(--muted);
  margin-bottom: 1rem;
}

.spacer-sm {
  height: 0.8rem;
}

.spacer-md {
  height: 1.4rem;
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
          const matchesLabel = (value) =>
            value &&
            (value.includes('keyboard_double_arrow') ||
             value.includes('keyboard-double-arrow') ||
             value.includes('keyboard double arrow'));

          const scrubRoot = (root) => {
            if (!root || !root.querySelectorAll) return;
            root.querySelectorAll('[title]').forEach((el) => el.removeAttribute('title'));
            root.querySelectorAll('*').forEach((el) => {
              const aria = el.getAttribute && el.getAttribute('aria-label');
              const title = el.getAttribute && el.getAttribute('title');
              if (matchesLabel(aria) || matchesLabel(title)) {
                el.removeAttribute('aria-label');
                el.removeAttribute('title');
                el.textContent = '';
                el.style.display = 'none';
              }
              if (el.shadowRoot) {
                scrubRoot(el.shadowRoot);
              }
            });
          };

          const killCollapseButtons = () => {
            const selectors = [
              '[data-testid="stSidebarCollapseButton"]',
              '[data-testid="stSidebarCollapsedControl"]',
              '[data-testid="stSidebarHeader"]',
              'section[data-testid="stSidebar"] header',
            ];
            selectors.forEach((sel) => {
              document.querySelectorAll(sel).forEach((el) => {
                el.remove();
              });
            });

            document.querySelectorAll('button, div, span').forEach((el) => {
              const aria = el.getAttribute && el.getAttribute('aria-label');
              const title = el.getAttribute && el.getAttribute('title');
              const text = el.textContent || '';
              if (matchesLabel(aria) || matchesLabel(title) || matchesLabel(text)) {
                el.remove();
              }
            });
          };

          scrubRoot(document);
          killCollapseButtons();
          const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
          let node;
          while ((node = walker.nextNode())) {
            const text = node.nodeValue || '';
            if (matchesLabel(text)) {
              node.nodeValue = '';
            }
          }
        };
        removeTitles();
        const observer = new MutationObserver(removeTitles);
        observer.observe(document.body, { childList: true, subtree: true });
        </script>
        """,
        height=0,
    )


def sanitize_llm_output(text: str) -> str:
    if not text:
        return ""
    cleaned = html.unescape(text)
    cleaned = unicodedata.normalize("NFKC", cleaned)
    cleaned = unicodedata.normalize("NFKD", cleaned)
    cleaned = "".join(ch for ch in cleaned if not unicodedata.combining(ch))
    cleaned = cleaned.replace("\u00ad", "")  # soft hyphen
    for hyphen_char in [
        "\u2010",
        "\u2011",
        "\u2012",
        "\u2013",
        "\u2014",
        "\u2015",
        "\u2212",
        "\u2043",
        "\u2212",
        "\u058A",
        "\u00B7",
    ]:
        cleaned = cleaned.replace(hyphen_char, "-")
    cleaned = re.sub(r"[\u200B-\u200D\uFEFF]", "", cleaned)
    cleaned = re.sub(r"<br\s*/?>", "\n", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"</(p|div|li|h\d)>", "\n", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    cleaned = cleaned.replace("&nbsp;", " ")
    cleaned = re.split(r"\n\s*-{3,}\s*\n", cleaned, maxsplit=1)[0]
    cleaned = re.sub(r"(\*\*|__)(.*?)\1", r"\2", cleaned)
    cleaned = re.sub(r"(\*|_)([^*_]+)\1", r"\2", cleaned)
    cleaned = re.sub(r"\\[a-zA-Z]+\\{([^}]*)\\}", r"\\1", cleaned)
    cleaned = cleaned.replace("\\", "")
    cleaned = cleaned.replace("`", "")
    cleaned = cleaned.replace("•", "- ")
    cleaned = cleaned.replace("‣", "- ")
    cleaned = cleaned.replace("·", "- ")
    cleaned = cleaned.replace("–", "-")
    cleaned = cleaned.replace("—", "-")
    cleaned = cleaned.replace("“", '"').replace("”", '"').replace("’", "'")
    compound_map = {
        "shortterm": "short-term",
        "longterm": "long-term",
        "midterm": "mid-term",
        "nearterm": "near-term",
        "yearoveryear": "year-over-year",
        "monthovermonth": "month-over-month",
        "weekoverweek": "week-over-week",
        "quarteroverquarter": "quarter-over-quarter",
        "cashflow": "cash flow",
        "runrate": "run rate",
        "burnrate": "burn rate",
        "breakeven": "break-even",
        "paybackperiod": "payback period",
        "emergencyfund": "emergency fund",
        "highestrate": "highest-rate",
        "debtpayoff": "debt payoff",
    }
    for raw, replacement in compound_map.items():
        cleaned = re.sub(rf"\\b{raw}\\b", replacement, cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"(\d)\s+%", r"\1%", cleaned)
    cleaned = re.sub(r"\b(\d+)\s*%\b", r"\1%", cleaned)
    def _k_to_dollars(match: re.Match) -> str:
        amount = float(match.group(1))
        return f"${amount * 1000:,.0f}"

    cleaned = re.sub(r"\$?(\d+(?:\.\d+)?)\s*k\b", _k_to_dollars, cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"\$(\d+(?:\.\d+)?)\s*([kmb])\b",
        lambda m: f"${m.group(1)}{m.group(2).upper()}",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\$(savings|debt|income|expenses|cash|balance|runway)\b", r"\1", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b~\s*\$(\d[\d,]*)\s*(\d+)\s*=\s*\$?(\d[\d,]*)\b", r"$\1 x \2 = $\3", cleaned)
    money_keywords = r"(cash flow|savings|debt|expenses|income|surplus|deficit|payment|payments|balance|budget|costs?|spend|spending|buffer|reserve)"
    def _prefix_dollar(match: re.Match) -> str:
        return f"{match.group(1)}${match.group(2)}"
    cleaned = re.sub(
        rf"({money_keywords}[^\d$]{{0,40}})(\d{{1,3}}(?:,\d{{3}})+(?:\.\d+)?|\d+(?:\.\d+)?)\b",
        _prefix_dollar,
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"(\\$\\d[\\d,]*)(?=\\$)", r"\\1 - ", cleaned)
    cleaned = re.sub(r"(\\$\\d[\\d,]*)(\\d{1,3}(?:,\\d{3})+)", r"\\1 - \\2", cleaned)
    cleaned = re.sub(r"\\b(\\d{1,2})-(\\d{1,2})\\s+months\\b", r"\\1 to \\2 months", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\\bemergency fund (of|for) 36 months\\b", r"emergency fund \\1 3 to 6 months", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[\t\r ]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = cleaned.strip()
    return cleaned


def strip_trailing_questions(text: str) -> str:
    if not text:
        return ""
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and not lines[-1].strip():
        lines.pop()
    while lines and "?" in lines[-1]:
        lines.pop()
        while lines and not lines[-1].strip():
            lines.pop()
    return "\n".join(lines).strip()


def format_baseline_summary(text: str) -> str:
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    sections: Dict[str, List[str]] = {"Summary": [], "Actions": [], "Warnings": []}
    current = ""
    for line in lines:
        header_match = re.match(r"^(summary|actions|warnings)\s*:\s*$", line, flags=re.IGNORECASE)
        if header_match:
            current = header_match.group(1).capitalize()
            continue
        bullet_match = re.match(r"^[-•]\s*(.+)", line)
        if bullet_match and current:
            sections[current].append(bullet_match.group(1).strip())
            continue
        if current:
            sections[current].append(line)

    def _clean_bullet(text_line: str) -> str:
        cleaned = re.sub(r"\s+", " ", text_line).strip()
        cleaned = re.sub(r"(\d)\s+%", r"\1%", cleaned)
        if cleaned and cleaned[0].isalpha():
            cleaned = cleaned[0].upper() + cleaned[1:]
        if cleaned and cleaned[-1] not in ".!?":
            cleaned += "."
        return cleaned

    output_lines: List[str] = []
    first_section = True
    for header in ["Summary", "Actions", "Warnings"]:
        bullets = [_clean_bullet(item) for item in sections[header] if item.strip()]
        if not bullets:
            continue
        if not first_section:
            output_lines.append("")
        first_section = False
        output_lines.append(f"{header}:")
        for bullet in bullets:
            output_lines.append(f"- {bullet}")
    return "\n".join(output_lines).strip()


def format_nemotron_error(message: str, context: str) -> str:
    base = "Nemotron is unavailable right now. Please start the server and try again."
    if not message:
        return base
    lowered = message.lower()
    if "timeout" in lowered:
        return f"{base} The request timed out."
    if "connection" in lowered or "refused" in lowered:
        return f"{base} We could not reach the server."
    if "unavailable" in lowered:
        return base
    return base


def format_currency(value: float) -> str:
    return f"${value:,.0f}"


def format_readable_text(text: str) -> str:
    if not text:
        return ""
    if "\n" in text:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    if len(sentences) <= 2:
        return text
    return "\n".join(sentences)


@st.cache_data(ttl=5)
def get_nemotron_status() -> bool:
    if not check_nemotron_online:
        return False
    try:
        return bool(check_nemotron_online())
    except Exception:
        return False


def safe_json_from_text(text: str) -> Dict[str, Any]:
    if not text:
        return {}
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    snippet = text[start : end + 1]
    try:
        payload = json.loads(snippet)
    except Exception:
        try:
            payload = json.loads(sanitize_llm_output(snippet))
        except Exception:
            return {}
    return payload if isinstance(payload, dict) else {}


def regex_extract_scenario(text: str) -> Dict[str, Any]:
    if not text:
        return {}
    lowered = text.lower()
    data: Dict[str, Any] = {}

    months_match = re.search(r"(\d+(?:\.\d+)?)\s*(months|month|mos|mo)", lowered)
    if months_match:
        data["months_unemployed"] = int(float(months_match.group(1)))

    percent_match = re.search(r"(\d+(?:\.\d+)?)\s*%.*(expense|cut|reduce|lower)", lowered)
    if percent_match:
        data["expense_cut_pct"] = float(percent_match.group(1))

    severance_match = re.search(r"(severance|payout)[^\d]*\$?([\d,]+)", lowered)
    if severance_match:
        data["severance"] = float(severance_match.group(2).replace(",", ""))

    benefit_match = re.search(r"(benefit|unemployment)[^\d]*\$?([\d,]+)", lowered)
    if benefit_match:
        data["unemployment_benefit_monthly"] = float(benefit_match.group(2).replace(",", ""))

    other_income_match = re.search(r"(side income|freelance|other income)[^\d]*\$?([\d,]+)", lowered)
    if other_income_match:
        data["other_income_monthly"] = float(other_income_match.group(2).replace(",", ""))

    return data


def extract_scenario_from_text(user_text: str, use_model: bool = False) -> Dict[str, Any]:
    if not user_text or not user_text.strip():
        return {}
    if not use_model or not query_nemotron or not extract_text:
        return regex_extract_scenario(user_text)

    schema = {
        "months_unemployed": "int (1-36)",
        "expense_cut_pct": "float (0-70)",
        "severance": "float",
        "unemployment_benefit_monthly": "float",
        "other_income_monthly": "float",
        "extra_monthly_expenses": "float",
        "debt_payment_monthly": "float",
        "healthcare_monthly": "float",
        "dependent_care_monthly": "float",
        "job_search_monthly": "float",
        "one_time_expense": "float",
        "relocation_cost": "float",
    }

    prompt = f"""
You extract scenario details from user text for a financial simulator.
Return ONLY a JSON object. Do not include any extra text.
If a field is unknown, omit it.
Schema: {json.dumps(schema)}

User request: {user_text}
""".strip()

    try:
        raw = extract_text(query_nemotron(prompt))
    except Exception:
        return regex_extract_scenario(user_text)

    parsed = safe_json_from_text(raw)
    if not parsed:
        return regex_extract_scenario(user_text)
    return parsed


def apply_scenario_update(parsed: Dict[str, Any]) -> Dict[str, float]:
    if not parsed:
        return {}

    def clamp_value(value: float, lo: float, hi: float) -> float:
        if clamp:
            return clamp(value, lo, hi)
        return max(lo, min(value, hi))

    ranges = {
        "months_unemployed": (0.0, 36.0),
        "expense_cut_pct": (0.0, 70.0),
        "severance": (0.0, 200000.0),
        "unemployment_benefit_monthly": (0.0, 50000.0),
        "other_income_monthly": (0.0, 50000.0),
        "extra_monthly_expenses": (0.0, 50000.0),
        "debt_payment_monthly": (0.0, 50000.0),
        "healthcare_monthly": (0.0, 50000.0),
        "dependent_care_monthly": (0.0, 50000.0),
        "job_search_monthly": (0.0, 50000.0),
        "one_time_expense": (0.0, 500000.0),
        "relocation_cost": (0.0, 500000.0),
    }

    applied: Dict[str, float] = {}
    for key, (lo, hi) in ranges.items():
        if key not in parsed:
            continue
        try:
            value = float(parsed[key])
        except (TypeError, ValueError):
            continue
        if key == "months_unemployed":
            value = int(round(value))
        applied[key] = clamp_value(value, lo, hi)

    state_map = {
        "months_unemployed": "months_unemployed",
        "expense_cut_pct": "expense_cut",
        "severance": "severance",
        "unemployment_benefit_monthly": "unemployment_benefit_monthly",
        "other_income_monthly": "other_income_monthly",
        "extra_monthly_expenses": "extra_monthly_expenses",
        "debt_payment_monthly": "debt_payment_monthly",
        "healthcare_monthly": "healthcare_monthly",
        "dependent_care_monthly": "dependent_care_monthly",
        "job_search_monthly": "job_search_monthly",
        "one_time_expense": "one_time_expense",
        "relocation_cost": "relocation_cost",
    }
    for key, state_key in state_map.items():
        if key in applied:
            st.session_state[state_key] = applied[key]

    return applied


def profile_signature(profile: Dict[str, Any]) -> str:
    try:
        return json.dumps(profile, sort_keys=True)
    except Exception:
        return str(profile)


def generate_baseline_summary(
    profile: Dict[str, Any],
    monthly_net: float,
    runway_months: float,
) -> str:
    if not query_nemotron or not extract_text:
        return "Nemotron is unavailable right now. Please start the server and try again."

    def money(value: float) -> str:
        return f"${value:,.0f}"

    debt_ratio = compute_debt_ratio(profile.get("debt", 0.0), profile.get("income_monthly", 0.0)) if compute_debt_ratio else 0.0
    risk_score = (
        compute_risk_score(
            runway_months,
            debt_ratio,
            profile.get("job_stability", "stable"),
            profile.get("industry", "Other"),
        )
        if compute_risk_score
        else 0.0
    )

    prompt = (
        "You are RiseArc. Summarize the user's current financial health in plain language. "
        "No formulas, LaTeX, or code. Do not provide investment advice, stock picks, or buy/sell guidance. "
        "Use words like '3 to 6' for ranges (avoid dashes). "
        "Make this as detailed as a scenario analysis: reference cash flow, runway, debt vs savings, and risk. "
        "Use consistent units (do not compare years to a 3 to 6 month range). "
        "Only use '3 to 6 months' when describing an emergency fund target.\n"
        "Write complete sentences with correct grammar and punctuation. "
        "Return in this format with EXACTLY three bullets per section and no extra text. "
        "End after Warnings (no follow-up question).\n"
        "Summary:\n- ...\n- ...\n- ...\n"
        "Actions:\n- ...\n- ...\n- ...\n"
        "Warnings:\n- ...\n- ...\n- ...\n\n"
        f"Profile: income {money(profile.get('income_monthly', 0))}, expenses {money(profile.get('expenses_monthly', 0))}, "
        f"savings {money(profile.get('savings', 0))}, debt {money(profile.get('debt', 0))}, "
        f"industry {profile.get('industry', 'Other')}, stability {profile.get('job_stability', 'stable')}.\n"
        f"Current snapshot: cash flow {money(monthly_net)} per month, runway {runway_months:.1f} months, "
        f"debt ratio {debt_ratio:.2f}, risk score {risk_score:.0f}."
    )
    try:
        cleaned = sanitize_llm_output(extract_text(query_nemotron(prompt)))
        return format_baseline_summary(strip_trailing_questions(cleaned))
    except Exception as exc:
        return format_nemotron_error(str(exc), "baseline summary")


def ensure_baseline_summary(
    profile: Dict[str, Any],
    monthly_net: float,
    runway_months: float,
    show_spinner: bool = False,
) -> str:
    sig = profile_signature(profile)
    cached = st.session_state.get("baseline_summary")
    cached_sig = st.session_state.get("baseline_profile_sig")
    if cached and cached_sig == sig:
        return cached

    if show_spinner:
        with st.spinner("Generating your baseline summary..."):
            summary = generate_baseline_summary(profile, monthly_net, runway_months)
    else:
        summary = generate_baseline_summary(profile, monthly_net, runway_months)

    if summary.startswith("[nemotron error]"):
        return format_nemotron_error(summary, "baseline summary")

    st.session_state.baseline_summary = summary
    st.session_state.baseline_profile_sig = sig
    return summary


def build_prompt(
    profile: Dict[str, Any],
    scenario: Dict[str, Any],
    metrics: Dict[str, float],
    alert: str,
    savings_total: float,
    timeline_stats: Dict[str, float],
    job_stability_value: str,
    job_stability_weight_value: float,
    scenario_note: str = "",
) -> str:
    def money(value: float) -> str:
        return f"${value:,.0f}"

    scenario_block = ""
    if scenario_note.strip():
        scenario_block = f"\nUser Scenario Request:\n- {scenario_note.strip()}\n"

    monthly_addons_total = (
        scenario.get("extra_monthly_expenses", 0.0)
        + scenario.get("debt_payment_monthly", 0.0)
        + scenario.get("healthcare_monthly", 0.0)
        + scenario.get("dependent_care_monthly", 0.0)
        + scenario.get("job_search_monthly", 0.0)
    )
    one_time_total = scenario.get("one_time_expense", 0.0) + scenario.get("relocation_cost", 0.0)

    return f"""
You are RiseArc, a financial assistant powered by Nemotron-3-Nano.
Generate a concise, practical summary based on the user's profile and scenario.
Do NOT provide investment advice, stock picks, buy/sell/hold guidance, or promises of returns.
Avoid language that sounds like a recommendation to invest. Focus on cash flow, runway, and risk reduction.
If asked about investing, redirect to budgeting, debt, and emergency savings fundamentals.

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

Avoid template placeholders like $debt, $savings, {brackets}, or variables. Use real numbers only.
If you estimate a range, write it clearly (e.g., "$3,500 to $4,000").
Do not write equations inline (e.g., "~$3,500 6 = $21,000"). Spell out the result instead.

User Profile:
- Monthly income: {money(profile['income_monthly'])}
- Monthly expenses: {money(profile['expenses_monthly'])}
- Savings: {money(profile['savings'])}
- Total debt: {money(profile['debt'])}
- Industry: {profile['industry']}
- Job stability: {job_stability_value}
- Dependents: {profile['dependents']}

Scenario:
- Months unemployed: {scenario['months_unemployed']}
- Expense cut: {scenario['expense_cut_pct']:.0f}%
- Severance: {money(scenario['severance'])}
- Unemployment benefit (monthly): {money(scenario.get('unemployment_benefit_monthly', 0.0))}
- Other income (monthly): {money(scenario.get('other_income_monthly', 0.0))}
- Debt payments (monthly): {money(scenario.get('debt_payment_monthly', 0.0))}
- Healthcare / insurance (monthly): {money(scenario.get('healthcare_monthly', 0.0))}
- Dependent care (monthly): {money(scenario.get('dependent_care_monthly', 0.0))}
- Job search / reskilling (monthly): {money(scenario.get('job_search_monthly', 0.0))}
- Other monthly expenses: {money(scenario.get('extra_monthly_expenses', 0.0))}
- Total monthly add-ons: {money(monthly_addons_total)}
- One-time expense: {money(scenario.get('one_time_expense', 0.0))}
- Relocation / legal (one-time): {money(scenario.get('relocation_cost', 0.0))}
- Total one-time costs: {money(one_time_total)}

Computed Metrics:
- Runway (months): {metrics['runway_months']:.1f}
- Risk score (0-100): {metrics['risk_score']:.0f}
- Adjusted risk score (0-100): {metrics['adjusted_risk_score']:.0f}
- Debt ratio: {metrics['debt_ratio']:.2f}
- Monthly expenses after cut: {money(metrics['monthly_expenses_cut'])}
- Monthly support: {money(metrics.get('monthly_support', 0.0))}
- Net monthly burn: {money(metrics.get('monthly_net_burn', 0.0))}
- One-time expense: {money(metrics.get('one_time_expense', 0.0))}
- Estimated savings leaks (monthly): {money(savings_total)}
- Timeline signals: months_until_zero={timeline_stats['months_until_zero']:.0f}, max_drawdown={money(timeline_stats['max_drawdown'])}, trend_slope={money(timeline_stats['trend_slope'])}

Alert Context:
{alert}
{scenario_block}
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
    monthly_support = scenario.get("unemployment_benefit_monthly", 0.0) + scenario.get(
        "other_income_monthly", 0.0
    )
    monthly_addons = (
        scenario.get("extra_monthly_expenses", 0.0)
        + scenario.get("debt_payment_monthly", 0.0)
        + scenario.get("healthcare_monthly", 0.0)
        + scenario.get("dependent_care_monthly", 0.0)
        + scenario.get("job_search_monthly", 0.0)
    )
    monthly_net_burn = monthly_expenses_cut + monthly_addons - monthly_support
    one_time_total = scenario.get("one_time_expense", 0.0) + scenario.get("relocation_cost", 0.0)
    starting_balance = profile["savings"] + scenario.get("severance", 0.0) - one_time_total
    if monthly_net_burn <= 0:
        runway_months = 60.0
    else:
        runway_months = compute_runway(max(starting_balance, 0.0), monthly_net_burn, 0.0)
    debt_ratio = compute_debt_ratio(profile["debt"], profile["income_monthly"])
    base_risk = compute_risk_score(
        runway_months, debt_ratio, profile["job_stability"], profile["industry"]
    )
    if adjust_risk_for_scenario:
        risk_score = adjust_risk_for_scenario(base_risk, runway_months, scenario["months_unemployed"])
    else:
        risk_score = base_risk

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
        starting_balance, max(monthly_net_burn, 0.0), max(scenario["months_unemployed"], 1), 0.0
    )
    timeline_stats = compute_timeline_stats(timeline)
    savings_total = total_savings_leaks([s["monthly_cost"] for s in payload["subscriptions"]])

    metrics = {
        "monthly_expenses_cut": monthly_expenses_cut,
        "monthly_support": monthly_support,
        "monthly_net_burn": monthly_net_burn,
        "one_time_expense": one_time_total,
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
        payload.get("scenario_note", ""),
    )
    try:
        summary = sanitize_llm_output(extract_text(query_nemotron(prompt)))
    except Exception as exc:
        summary = format_nemotron_error(str(exc), "scenario analysis")

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
    st.session_state.baseline_summary = None
    st.session_state.baseline_profile_sig = None
    if scenario:
        st.session_state["months_unemployed"] = scenario.get("months_unemployed", 6)
        st.session_state["expense_cut"] = scenario.get("expense_cut_pct", 15)
        st.session_state["severance"] = scenario.get("severance", 3000.0)
    if SAMPLE_REQUEST.get("news_event"):
        st.session_state["news_event"] = "Tech layoff wave"
    for item in SAMPLE_REQUEST.get("subscriptions", []):
        key = f"sub_{item['name']}"
        st.session_state[key] = True


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown('<div class="sidebar-brand">RiseArc</div>', unsafe_allow_html=True)
        st.caption("Financial intelligence console")

        options = ["Landing", "Scenario Builder", "Survival Timeline", "Chat"]
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
        profile_ready = st.session_state.profile is not None
        profile_class = "ready" if profile_ready else ""
        profile_label = "Profile: Ready" if profile_ready else "Profile: Incomplete"
        nemotron_online = get_nemotron_status()
        nemotron_class = "ready" if nemotron_online else ""
        nemotron_label = "Nemotron: Online" if nemotron_online else "Nemotron: Offline"
        st.markdown(
            f"""
            <div class="status-stack">
              <div class="status-pill {profile_class}">{profile_label}</div>
              <div class="status-pill {nemotron_class}">{nemotron_label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def init_state() -> None:
    if "profile" not in st.session_state:
        st.session_state.profile = None
    if "show_profile_dialog" not in st.session_state:
        st.session_state.show_profile_dialog = True
    if "active_view" not in st.session_state:
        st.session_state.active_view = "Landing"
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "result" not in st.session_state:
        st.session_state.result = None
    if "baseline_summary" not in st.session_state:
        st.session_state.baseline_summary = None
    if "baseline_profile_sig" not in st.session_state:
        st.session_state.baseline_profile_sig = None
    if "months_unemployed" not in st.session_state:
        st.session_state.months_unemployed = 6
    if "expense_cut" not in st.session_state:
        st.session_state.expense_cut = 15.0
    if "severance" not in st.session_state:
        st.session_state.severance = 3000.0
    if "unemployment_benefit_monthly" not in st.session_state:
        st.session_state.unemployment_benefit_monthly = 0.0
    if "other_income_monthly" not in st.session_state:
        st.session_state.other_income_monthly = 0.0
    if "extra_monthly_expenses" not in st.session_state:
        st.session_state.extra_monthly_expenses = 0.0
    if "debt_payment_monthly" not in st.session_state:
        st.session_state.debt_payment_monthly = 0.0
    if "healthcare_monthly" not in st.session_state:
        st.session_state.healthcare_monthly = 0.0
    if "dependent_care_monthly" not in st.session_state:
        st.session_state.dependent_care_monthly = 0.0
    if "job_search_monthly" not in st.session_state:
        st.session_state.job_search_monthly = 0.0
    if "one_time_expense" not in st.session_state:
        st.session_state.one_time_expense = 0.0
    if "relocation_cost" not in st.session_state:
        st.session_state.relocation_cost = 0.0


def parse_float_input(raw: str, fallback: float, label: str) -> float:
    if raw is None or raw.strip() == "":
        return fallback
    try:
        return float(raw.replace(",", ""))
    except ValueError:
        st.error(f"Please enter a valid number for {label}.")
        raise


def parse_int_input(raw: str, fallback: int, label: str) -> int:
    if raw is None or raw.strip() == "":
        return fallback
    try:
        return int(float(raw.replace(",", "")))
    except ValueError:
        st.error(f"Please enter a valid whole number for {label}.")
        raise


@st.dialog("Welcome to RiseArc")
def profile_dialog() -> None:
    st.markdown("Fill in your financial profile once. You can update it anytime.")
    profile = st.session_state.profile or {}
    has_profile = bool(profile)

    with st.form("profile_form"):
        income_raw = st.text_input(
            "Monthly income",
            value="",
            placeholder="e.g. 5200",
        )
        expenses_raw = st.text_input(
            "Monthly expenses",
            value="",
            placeholder="e.g. 3400",
        )
        savings_raw = st.text_input(
            "Savings",
            value="",
            placeholder="e.g. 12000",
        )
        debt_raw = st.text_input(
            "Total debt",
            value="",
            placeholder="e.g. 15000",
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
        dependents_raw = st.text_input(
            "Dependents",
            value="",
            placeholder="e.g. 0",
        )
        submitted = st.form_submit_button("Save profile")

    if submitted:
        try:
            income = parse_float_input(income_raw, float(profile.get("income_monthly", 0.0)), "Monthly income")
            expenses = parse_float_input(expenses_raw, float(profile.get("expenses_monthly", 0.0)), "Monthly expenses")
            savings = parse_float_input(savings_raw, float(profile.get("savings", 0.0)), "Savings")
            debt = parse_float_input(debt_raw, float(profile.get("debt", 0.0)), "Total debt")
            dependents = parse_int_input(dependents_raw, int(profile.get("dependents", 0)), "Dependents")
        except ValueError:
            return

        if not has_profile:
            if income <= 0 or expenses <= 0:
                st.error("Monthly income and expenses are required.")
                return
        st.session_state.profile = {
            "income_monthly": income,
            "expenses_monthly": expenses,
            "savings": savings,
            "debt": debt,
            "industry": industry,
            "job_stability": job_stability,
            "dependents": int(dependents),
        }
        st.session_state.baseline_summary = None
        st.session_state.baseline_profile_sig = None
        monthly_net = income - expenses
        if monthly_net >= 0:
            runway_months = 60.0
        else:
            runway_months = compute_runway(savings, abs(monthly_net), 0.0) if compute_runway else 0.0
        ensure_baseline_summary(st.session_state.profile, monthly_net, runway_months, show_spinner=True)
        st.session_state.show_profile_dialog = False
        st.success("Profile saved.")
        st.rerun()


def normalize_numeric_text(raw: str) -> str:
    return (
        raw.replace(",", "")
        .replace("$", "")
        .replace("%", "")
        .strip()
    )


def parse_optional_float(raw: str, fallback: float, label: str) -> float | None:
    if raw is None or raw.strip() == "":
        return fallback
    try:
        value = float(normalize_numeric_text(raw))
    except ValueError:
        st.error(f"Please enter a valid number for {label}.")
        return None
    return max(value, 0.0)


def parse_optional_int(raw: str, fallback: int, label: str) -> int | None:
    if raw is None or raw.strip() == "":
        return fallback
    try:
        value = int(float(normalize_numeric_text(raw)))
    except ValueError:
        st.error(f"Please enter a valid whole number for {label}.")
        return None
    return max(value, 0)


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
        if st.button("Enter Scenario Builder", type="primary"):
            st.session_state.active_view = "Scenario Builder"
            st.rerun()


def build_payload_from_state(
    profile: Dict[str, Any],
    months_unemployed: int,
    expense_cut_pct: float,
    severance: float,
    unemployment_benefit_monthly: float,
    other_income_monthly: float,
    extra_monthly_expenses: float,
    debt_payment_monthly: float,
    healthcare_monthly: float,
    dependent_care_monthly: float,
    job_search_monthly: float,
    one_time_expense: float,
    relocation_cost: float,
    subscriptions: Dict[str, float],
    news_event: Dict[str, Any],
    scenario_note: str = "",
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "profile": profile,
        "scenario": {
            "months_unemployed": months_unemployed,
            "expense_cut_pct": expense_cut_pct,
            "severance": severance,
            "unemployment_benefit_monthly": unemployment_benefit_monthly,
            "other_income_monthly": other_income_monthly,
            "extra_monthly_expenses": extra_monthly_expenses,
            "debt_payment_monthly": debt_payment_monthly,
            "healthcare_monthly": healthcare_monthly,
            "dependent_care_monthly": dependent_care_monthly,
            "job_search_monthly": job_search_monthly,
            "one_time_expense": one_time_expense,
            "relocation_cost": relocation_cost,
        },
        "subscriptions": [
            {"name": name, "monthly_cost": cost}
            for name, cost in subscriptions.items()
            if cost > 0
        ],
        "news_event": news_event,
        "scenario_note": scenario_note.strip(),
    }
    return payload


def render_scenario_builder() -> None:
    if not st.session_state.profile:
        st.info("Please complete your profile to unlock the full experience.")
        if st.button("Complete profile"):
            st.session_state.show_profile_dialog = True
        return

    st.markdown('<div class="card-text">Build a sandbox scenario and run a survival scan.</div>', unsafe_allow_html=True)
    st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Scenario prompt</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Describe the scenario you want to simulate.</div>', unsafe_allow_html=True)

    scenario_note = st.text_area(
        "",
        value=st.session_state.get("scenario_note", ""),
        placeholder="Example: I might lose my job for 5 months, can cut expenses by 20%, and have $3k severance.",
        height=90,
        label_visibility="collapsed",
    )
    st.session_state.scenario_note = scenario_note
    if scenario_note.strip():
        parsed_preview = extract_scenario_from_text(scenario_note, use_model=False)
        applied_preview = apply_scenario_update(parsed_preview)
        if applied_preview:
            summary_bits = []
            if "months_unemployed" in applied_preview:
                summary_bits.append(f"{int(applied_preview['months_unemployed'])} months unemployed")
            if "expense_cut_pct" in applied_preview:
                summary_bits.append(f"{applied_preview['expense_cut_pct']:.0f}% expense cut")
            if "severance" in applied_preview:
                summary_bits.append(f"severance {format_currency(applied_preview['severance'])}")
            if "unemployment_benefit_monthly" in applied_preview:
                summary_bits.append(
                    f"benefits {format_currency(applied_preview['unemployment_benefit_monthly'])}/mo"
                )
            if "other_income_monthly" in applied_preview:
                summary_bits.append(f"other income {format_currency(applied_preview['other_income_monthly'])}/mo")
            if "extra_monthly_expenses" in applied_preview:
                summary_bits.append(f"extra expenses {format_currency(applied_preview['extra_monthly_expenses'])}/mo")
            if "one_time_expense" in applied_preview:
                summary_bits.append(f"one-time {format_currency(applied_preview['one_time_expense'])}")
            st.caption("Interpreted: " + ", ".join(summary_bits))

    st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Scenario parameters <span class="muted">(optional)</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="card-text">Enter desired scenario factors.</div>', unsafe_allow_html=True)
    st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        st.markdown('<div class="field-label">Months unemployed</div>', unsafe_allow_html=True)
        months_unemployed_raw = st.text_input(
            "",
            key="months_unemployed_raw",
            placeholder="e.g. 6",
            label_visibility="collapsed",
        )
        st.markdown('<div class="field-label">Expense cut (%)</div>', unsafe_allow_html=True)
        expense_cut_raw = st.text_input(
            "",
            key="expense_cut_raw",
            placeholder="e.g. 15",
            label_visibility="collapsed",
        )
        st.markdown('<div class="field-label">Severance / payout</div>', unsafe_allow_html=True)
        severance_raw = st.text_input(
            "",
            key="severance_raw",
            placeholder="e.g. 3000",
            label_visibility="collapsed",
        )
        st.markdown('<div class="field-label">Unemployment benefits (monthly)</div>', unsafe_allow_html=True)
        unemployment_raw = st.text_input(
            "",
            key="unemployment_benefit_raw",
            placeholder="e.g. 600",
            label_visibility="collapsed",
        )
        st.markdown('<div class="field-label">Other income (monthly)</div>', unsafe_allow_html=True)
        other_income_raw = st.text_input(
            "",
            key="other_income_raw",
            placeholder="e.g. 200",
            label_visibility="collapsed",
        )
    with right:
        st.markdown('<div class="field-label">Debt payments (monthly)</div>', unsafe_allow_html=True)
        debt_payment_raw = st.text_input(
            "",
            key="debt_payment_raw",
            placeholder="e.g. 250",
            label_visibility="collapsed",
        )
        st.markdown('<div class="field-label">Healthcare / insurance (monthly)</div>', unsafe_allow_html=True)
        healthcare_raw = st.text_input(
            "",
            key="healthcare_raw",
            placeholder="e.g. 150",
            label_visibility="collapsed",
        )
        st.markdown('<div class="field-label">Dependent care (monthly)</div>', unsafe_allow_html=True)
        dependent_care_raw = st.text_input(
            "",
            key="dependent_care_raw",
            placeholder="e.g. 0",
            label_visibility="collapsed",
        )
        st.markdown('<div class="field-label">Job search / reskilling (monthly)</div>', unsafe_allow_html=True)
        job_search_raw = st.text_input(
            "",
            key="job_search_raw",
            placeholder="e.g. 100",
            label_visibility="collapsed",
        )
        st.markdown('<div class="field-label">Other monthly expenses (misc)</div>', unsafe_allow_html=True)
        extra_expenses_raw = st.text_input(
            "",
            key="extra_monthly_raw",
            placeholder="e.g. 75",
            label_visibility="collapsed",
        )

    st.markdown('<div class="field-label">One-time expense</div>', unsafe_allow_html=True)
    one_time_raw = st.text_input(
        "",
        key="one_time_raw",
        placeholder="e.g. 1200",
        label_visibility="collapsed",
    )
    st.markdown('<div class="field-label">Relocation / legal (one-time)</div>', unsafe_allow_html=True)
    relocation_raw = st.text_input(
        "",
        key="relocation_raw",
        placeholder="e.g. 2500",
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    months_unemployed = parse_optional_int(
        months_unemployed_raw, st.session_state.get("months_unemployed", 0), "Months unemployed"
    )
    expense_cut_pct = parse_optional_float(
        expense_cut_raw, st.session_state.get("expense_cut", 0.0), "Expense cut (%)"
    )
    severance = parse_optional_float(
        severance_raw, st.session_state.get("severance", 0.0), "Severance / payout"
    )
    unemployment_benefit_monthly = parse_optional_float(
        unemployment_raw, st.session_state.get("unemployment_benefit_monthly", 0.0), "Unemployment benefits"
    )
    other_income_monthly = parse_optional_float(
        other_income_raw, st.session_state.get("other_income_monthly", 0.0), "Other income"
    )
    debt_payment_monthly = parse_optional_float(
        debt_payment_raw, st.session_state.get("debt_payment_monthly", 0.0), "Debt payments"
    )
    healthcare_monthly = parse_optional_float(
        healthcare_raw, st.session_state.get("healthcare_monthly", 0.0), "Healthcare"
    )
    dependent_care_monthly = parse_optional_float(
        dependent_care_raw, st.session_state.get("dependent_care_monthly", 0.0), "Dependent care"
    )
    job_search_monthly = parse_optional_float(
        job_search_raw, st.session_state.get("job_search_monthly", 0.0), "Job search"
    )
    extra_monthly_expenses = parse_optional_float(
        extra_expenses_raw, st.session_state.get("extra_monthly_expenses", 0.0), "Other monthly expenses"
    )
    one_time_expense = parse_optional_float(
        one_time_raw, st.session_state.get("one_time_expense", 0.0), "One-time expense"
    )
    relocation_cost = parse_optional_float(
        relocation_raw, st.session_state.get("relocation_cost", 0.0), "Relocation / legal"
    )

    if None in [
        months_unemployed,
        expense_cut_pct,
        severance,
        unemployment_benefit_monthly,
        other_income_monthly,
        debt_payment_monthly,
        healthcare_monthly,
        dependent_care_monthly,
        job_search_monthly,
        extra_monthly_expenses,
        one_time_expense,
        relocation_cost,
    ]:
        return

    st.session_state.months_unemployed = months_unemployed
    st.session_state.expense_cut = expense_cut_pct
    st.session_state.severance = severance
    st.session_state.unemployment_benefit_monthly = unemployment_benefit_monthly
    st.session_state.other_income_monthly = other_income_monthly
    st.session_state.debt_payment_monthly = debt_payment_monthly
    st.session_state.healthcare_monthly = healthcare_monthly
    st.session_state.dependent_care_monthly = dependent_care_monthly
    st.session_state.job_search_monthly = job_search_monthly
    st.session_state.extra_monthly_expenses = extra_monthly_expenses
    st.session_state.one_time_expense = one_time_expense
    st.session_state.relocation_cost = relocation_cost

    monthly_support = unemployment_benefit_monthly + other_income_monthly
    monthly_addons = (
        debt_payment_monthly
        + healthcare_monthly
        + dependent_care_monthly
        + job_search_monthly
        + extra_monthly_expenses
    )
    one_time_total = one_time_expense + relocation_cost
    monthly_expenses_cut = st.session_state.profile["expenses_monthly"] * (1 - expense_cut_pct / 100.0)
    monthly_net_burn = monthly_expenses_cut + monthly_addons - monthly_support

    st.markdown("\n")
    if st.button("Run Analysis", type="primary"):
        with st.spinner("Analyzing scenario..."):
            parsed = extract_scenario_from_text(scenario_note, use_model=True)
            apply_scenario_update(parsed)
        payload = build_payload_from_state(
            profile=st.session_state.profile,
            months_unemployed=int(months_unemployed),
            expense_cut_pct=float(expense_cut_pct),
            severance=severance,
            unemployment_benefit_monthly=unemployment_benefit_monthly,
            other_income_monthly=other_income_monthly,
            extra_monthly_expenses=extra_monthly_expenses,
            debt_payment_monthly=debt_payment_monthly,
            healthcare_monthly=healthcare_monthly,
            dependent_care_monthly=dependent_care_monthly,
            job_search_monthly=job_search_monthly,
            one_time_expense=one_time_expense,
            relocation_cost=relocation_cost,
            subscriptions={},
            news_event=None,
            scenario_note=scenario_note,
        )
        with st.spinner("Running analysis..."):
            try:
                result = local_analysis(payload)
                st.session_state.result = result
                st.success("Analysis complete.")
            except Exception as local_exc:
                st.error(f"Local analysis failed: {local_exc}")

    result = st.session_state.result
    if result:
        st.subheader("Scenario Results")
        metrics = result.get("metrics", {})
        m1, m2, m3 = st.columns(3)
        m1.metric("Runway (months)", f"{metrics.get('runway_months', 0):.1f}")
        m2.metric("Risk score", f"{metrics.get('risk_score', 0):.0f}/100")
        m3.metric("Adjusted risk", f"{metrics.get('adjusted_risk_score', 0):.0f}/100")
        st.progress(min(int(metrics.get("risk_score", 0)), 100))

        timeline = result.get("timeline", [])
        if timeline:
            st.line_chart(timeline, height=240)

        st.subheader("Nemotron Summary")
        summary_text = sanitize_llm_output(result.get("summary", ""))
        st.text(summary_text)


def render_survival_timeline() -> None:
    st.subheader("Survival Timeline")

    if not st.session_state.profile:
        st.info("Please complete your profile to unlock the full experience.")
        if st.button("Complete profile"):
            st.session_state.show_profile_dialog = True
        return

    profile = st.session_state.profile
    income = float(profile.get("income_monthly", 0.0))
    expenses = float(profile.get("expenses_monthly", 0.0))
    savings = float(profile.get("savings", 0.0))
    debt = float(profile.get("debt", 0.0))

    monthly_net = income - expenses
    debt_ratio = compute_debt_ratio(debt, income) if compute_debt_ratio else 0.0
    runway_months = 60.0 if monthly_net >= 0 else compute_runway(savings, abs(monthly_net), 0.0)
    risk_score = (
        compute_risk_score(runway_months, debt_ratio, profile.get("job_stability", "stable"), profile.get("industry", "Other"))
        if compute_risk_score
        else 0.0
    )

    m1, m2, m3 = st.columns(3)
    if monthly_net >= 0:
        m1.metric("Cash flow", "Positive")
        m2.metric("Monthly surplus", format_currency(monthly_net))
        m3.metric("Risk score", f"{risk_score:.0f}/100")
        st.progress(min(int(risk_score), 100))
    else:
        m1.metric("Runway (months)", f"{runway_months:.1f}")
        m2.metric("Monthly deficit", format_currency(abs(monthly_net)))
        m3.metric("Risk score", f"{risk_score:.0f}/100")
        st.progress(min(int(risk_score), 100))

    horizon_months = 36
    if monthly_net >= 0:
        timeline = [round(savings + monthly_net * month, 2) for month in range(horizon_months + 1)]
        st.line_chart(timeline, height=260)
    else:
        timeline = build_timeline(savings, abs(monthly_net), horizon_months, 0.0) if build_timeline else []
        if timeline:
            st.line_chart(timeline, height=260)

    timeline_stats = get_timeline_stats(timeline)
    metrics = {
        "runway_months": runway_months,
        "risk_score": risk_score,
        "adjusted_risk_score": risk_score,
        "debt_ratio": debt_ratio,
    }
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

    st.subheader("Current Snapshot")
    if monthly_net >= 0:
        st.success("Positive cash flow: you are growing your savings each month.")
        st.caption(f"Projected savings in 12 months: {format_currency(savings + monthly_net * 12)}")
    else:
        st.warning("Negative cash flow: expenses exceed income.")
        st.caption(f"Estimated runway at current burn: {runway_months:.1f} months")

    st.subheader("Nemotron Summary")
    summary_text = ensure_baseline_summary(profile, monthly_net, runway_months)
    st.markdown(
        f"""
        <div class="summary-block">
          <div class="summary-title">Baseline Summary</div>
          <div class="summary-text">{html.escape(summary_text)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
        st.warning("Nemotron is unavailable right now. Please start the server to enable chat.")
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

    prompt_text = st.chat_input("Ask RiseArc about your finances")
    if quick_input:
        prompt_text = quick_input

    if prompt_text:
        st.session_state.chat_history.append({"role": "user", "content": prompt_text})
        with st.chat_message("user", avatar="👤"):
            st.text(prompt_text)

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
            "Never provide investment advice or asset recommendations. Avoid buy/sell/hold language.",
            "Always reply to the user in the same font.",
            "Always be helpful, polite, and professional",
            "Always reply to the user in plain human language with no formulas, LaTeX, or code formatting.",
            "Keep answers short unless the user asks for details.",
            "Use a friendly, reassuring tone as a financial guardian.",
            "Explain for non-experts: avoid jargon or define it in plain words.",
            "Sound human and supportive, not robotic or overly formal.",
            "When expressing ranges, use words like '3 to 6' instead of dashes.",
            "Structure every response with clear signposting:",
            "Summary: (1-2 short sentences)",
            "What this means: (2-3 short bullets)",
            "Next steps: (2-3 short bullets)",
            "End with one short, relevant follow-up question that offers clarification or the next best step.",
            (
                "Profile: income "
                f"{llm_profile['income_monthly']}, expenses {llm_profile['expenses_monthly']}, "
                f"savings {llm_profile['savings']}, debt {llm_profile['debt']}, "
                f"industry {llm_profile['industry']}, stability {stability_label}, "
                f"dependents {llm_profile['dependents']}"
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
                response = format_nemotron_error(str(exc), "chat response")
            typing_placeholder.text(format_readable_text(response))

        st.session_state.chat_history.append({"role": "assistant", "content": format_readable_text(response)})


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
    elif st.session_state.active_view == "Scenario Builder":
        render_scenario_builder()
    elif st.session_state.active_view == "Survival Timeline":
        render_survival_timeline()
    else:
        render_chat()


if __name__ == "__main__":
    main()
