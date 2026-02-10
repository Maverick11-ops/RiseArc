import html
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st
import streamlit.components.v1 as components
try:
    import altair as alt
except Exception:
    alt = None

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))



try:
    from app.core.sample_payloads import SAMPLE_REQUEST
except Exception:
    SAMPLE_REQUEST = None

try:
    from app.core.tools import (
        clamp,
        compute_debt_ratio,
        compute_risk_score,
        compute_runway,
        compute_timeline_stats,
        adjust_risk_for_scenario,
        total_savings_leaks,
    )
    from app.ai.nemotron_client import check_nemotron_online, extract_text, query_nemotron
except Exception:
    clamp = None
    compute_debt_ratio = None
    compute_risk_score = None
    compute_runway = None
    compute_timeline_stats = None
    adjust_risk_for_scenario = None
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
BASELINE_SUMMARY_VERSION = "v4-currency-locked"
CHAT_HISTORY_CURRENCY_VERSION = "v9-markdown-strip-fix"
TIMELINE_HORIZON_MONTHS = 60
INVESTMENT_TERMS_PATTERN = re.compile(
    r"\b("
    r"invest|investing|investment|invested|"
    r"stock|stocks|etf|etfs|index fund|index funds|mutual fund|mutual funds|"
    r"portfolio|crypto|cryptocurrency|bitcoin|equity|equities|bond|bonds"
    r")\b",
    flags=re.IGNORECASE,
)
NON_INVESTMENT_FALLBACK = (
    "Focus on cash flow stability, debt reduction, and emergency savings first."
)

FOLLOWUP_QUESTIONS = [
    "Would you like me to unpack any part of this in more detail?",
    "Want a simple step-by-step plan based on your priorities?",
    "Should I focus on savings, debt, or cash flow first?",
    "Do you want me to stress-test a specific scenario next?",
    "Would you like a quick checklist tailored to your situation?",
]
_FOLLOWUP_INDEX = 0
_LAST_FOLLOWUP = ""


def next_followup() -> str:
    global _FOLLOWUP_INDEX
    if not FOLLOWUP_QUESTIONS:
        return "Would you like me to go deeper on any part of this?"
    text = FOLLOWUP_QUESTIONS[_FOLLOWUP_INDEX % len(FOLLOWUP_QUESTIONS)]
    _FOLLOWUP_INDEX += 1
    return text


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

/* Hide Streamlit dev toolbar/status widgets */
[data-testid="stToolbar"],
[data-testid="stStatusWidget"],
[data-testid="stToolbarActions"],
header {
  display: none !important;
  visibility: hidden !important;
  height: 0 !important;
}

.update-overlay {
  position: fixed;
  inset: 0;
  background: rgba(8, 12, 20, 0.6);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.update-card {
  background: var(--panel-strong);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 24px 28px;
  min-width: 320px;
  max-width: 520px;
  box-shadow: 0 20px 60px rgba(15, 23, 42, 0.5);
  text-align: left;
}

.update-title {
  font-size: 1.2rem;
  font-weight: 700;
  margin-bottom: 0.4rem;
}

.update-text {
  color: var(--muted);
  margin-bottom: 1rem;
}

.update-btn {
  background: transparent;
  border: 1px solid var(--line);
  color: var(--text);
  padding: 10px 18px;
  border-radius: 10px;
  font-weight: 600;
  font-family: inherit;
  font-size: 1rem;
  cursor: pointer;
  text-decoration: none;
  display: inline-block;
}

.update-btn:hover {
  background: rgba(148, 163, 184, 0.12);
}

html, body, [class*="st-"] {
  font-family: 'Sora', sans-serif;
  color: var(--text);
}

/* Prevent random font/size shifts in markdown/code blocks */
.stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span,
.stText, .stText pre, pre, code, kbd, samp, tt {
  font-family: 'Sora', sans-serif !important;
  font-size: 1rem !important;
  line-height: 1.6 !important;
  color: var(--text) !important;
}

pre, code {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  border-radius: 0 !important;
  white-space: pre-wrap !important;
}

.stApp {
  background: radial-gradient(circle at 10% 20%, rgba(79, 70, 229, 0.18), transparent 45%),
              radial-gradient(circle at 80% 10%, rgba(14, 165, 233, 0.15), transparent 35%),
              linear-gradient(160deg, var(--bg-1), var(--bg-2));
}

/* Hide stale UI elements during reruns so previous tab content never shows */
[data-stale="true"],
[data-testid="stAppViewContainer"] [data-stale="true"] {
  display: none !important;
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

.landing-card {
  min-height: 138px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
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
  padding-bottom: 20px;
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

.summary-bottom {
  font-weight: 600;
  margin-bottom: 0.6rem;
}

.summary-section {
  margin-bottom: 0.8rem;
}

.summary-section-title {
  font-weight: 600;
  margin-bottom: 0.3rem;
}

.summary-list {
  list-style: none;
  padding-left: 0;
  margin: 0;
}

.summary-list li {
  margin-bottom: 0.35rem;
  position: relative;
  padding-left: 0.9rem;
}

.summary-list li::before {
  content: "–";
  position: absolute;
  left: 0;
  color: var(--muted);
}

.stApp .block-container {
  padding-bottom: 140px;
}

div[data-testid="stChatInput"] {
  position: fixed;
  bottom: 24px;
  z-index: 1000;
  max-width: none;
}

div[data-testid="stChatInput"] > div {
  width: 100%;
  max-width: none;
}

div[data-testid="stChatInput"] textarea {
  width: 100%;
}

div[data-testid="stChatInput"] form,
div[data-testid="stChatInput"] form > div,
div[data-testid="stChatInput"] form > div > div,
div[data-testid="stChatInput"] [data-baseweb="textarea"] {
  width: 100% !important;
  max-width: none !important;
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

.chat-plain-text {
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'Sora', sans-serif;
  font-size: 1rem;
  line-height: 1.6;
  color: var(--text);
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


def inject_chat_input_positioner() -> None:
    st.components.v1.html(
        """
        <script>
        (function() {
          const root = window.parent ? window.parent.document : document;
          const positionChatInput = () => {
            const chat = root.querySelector('div[data-testid="stChatInput"]');
            if (!chat) return;
            const padding = 16;
            const container = root.querySelector('.block-container');
            if (container) {
              const rect = container.getBoundingClientRect();
              chat.style.left = `${rect.left + padding}px`;
              chat.style.right = 'auto';
              chat.style.width = `${Math.max(rect.width - padding * 2, 320)}px`;
              chat.style.marginLeft = '0px';
              return;
            }
            const sidebar = root.querySelector('section[data-testid="stSidebar"]');
            const sidebarWidth = sidebar ? sidebar.getBoundingClientRect().width : 0;
            chat.style.left = `calc(${sidebarWidth}px + 24px + ${padding}px)`;
            chat.style.right = `${24 + padding}px`;
            chat.style.width = `calc(100vw - ${sidebarWidth}px - ${48 + padding * 2}px)`;
            chat.style.marginLeft = '0px';
          };
          positionChatInput();
          window.parent.addEventListener('resize', positionChatInput);
          const observer = new MutationObserver(positionChatInput);
          observer.observe(root.body, { childList: true, subtree: true });
        })();
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
    cleaned = re.sub(r"\x1B\[[0-?]*[ -/]*[@-~]", "", cleaned)
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
        "lowpayment": "low payment",
        "creatinga": "creating a",
        "leavinga": "leaving a",
        "makinga": "making a",
        "turninga": "turning a",
        "causinga": "causing a",
    }
    for raw, replacement in compound_map.items():
        cleaned = re.sub(rf"\\b{raw}\\b", replacement, cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"(\d)\s+%", r"\1%", cleaned)
    cleaned = re.sub(r"\b(\d+)\s*%\b", r"\1%", cleaned)
    cleaned = re.sub(r"\$(\d[\d,]*)\s*%", r"$\1", cleaned)
    cleaned = re.sub(r"\b([A-Za-z]+)\s*%\b", r"\\1", cleaned)
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
    cleaned = re.sub(
        r"\$(cash flow|cashflow|savings|debt|income|expenses|cash|balance|runway|reserve|buffer)\b",
        r"\1",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\$([A-Za-z_]+)\b", r"\1", cleaned)
    cleaned = re.sub(r"\$(?!\d)([A-Za-z]+(?:\s+[A-Za-z]+)*)", r"\1", cleaned)
    cleaned = re.sub(r"\bcash flow month\b", "cash flow per month", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b~\s*\$(\d[\d,]*)\s*(\d+)\s*=\s*\$?(\d[\d,]*)\b", r"$\1 x \2 = $\3", cleaned)
    cleaned = re.sub(r"\$(\d[\d,]*)\s*-\s*\$(\d[\d,]*)", r"$\1 to $\2", cleaned)
    cleaned = re.sub(r"\$(\d[\d,]*)\s+(\d{1,3})\s+\$(\d[\d,]*)", r"$\1 x \2 = $\3", cleaned)
    cleaned = re.sub(r"\bmonths?_?until_?zero\s*=?\s*\d+(?:\.\d+)?\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("–", "-").replace("—", "-").replace("−", "-")
    cleaned = re.sub(r"\bmonths?of\b", "months of", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bmonthsof\b", "months of", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\(about\s+(\d[\d,]*)\)", r"(about $\1)", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"([A-Za-z])(?=\d)", r"\1 ", cleaned)
    cleaned = re.sub(r"(\d)(?=[A-Za-z])", r"\1 ", cleaned)
    cleaned = re.sub(r"([0-9])\(", r"\1 (", cleaned)
    cleaned = re.sub(r"\)([A-Za-z0-9])", r") \1", cleaned)
    cleaned = re.sub(r"(income|expenses|savings|debt|cash flow|monthly net)\$", r"\1 $", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r":\s*\.", ".", cleaned)
    cleaned = re.sub(r"\s*:\s*$", "", cleaned)
    cleaned = re.sub(r"(?i)(^|\n)\s*-\s*risk score\b", r"\1- Risk score", cleaned)
    cleaned = re.sub(r"(?i)(^|\n)\s*-\s*debt ratio\b", r"\1- Debt ratio", cleaned)
    cleaned = re.sub(r"(?i)(^|\n)\s*-\s*debt-to-annual-income ratio\b", r"\1- Debt-to-annual-income ratio", cleaned)
    cleaned = re.sub(r"(?i)(^|\n)risk score\b", r"\1Risk score", cleaned)
    cleaned = re.sub(r"(?i)(^|\n)debt ratio\b", r"\1Debt ratio", cleaned)
    cleaned = re.sub(r"(?i)(^|\n)debt-to-annual-income ratio\b", r"\1Debt-to-annual-income ratio", cleaned)
    cleaned = re.sub(
        r"\b(?:based on|using) the runway metric\b",
        "based on your savings and current burn rate",
        cleaned,
        flags=re.IGNORECASE,
    )
    money_keywords = r"(cash flow|savings|debt|expenses|income|surplus|deficit|payment|payments|balance|budget|costs?|spend|spending|buffer|reserve)"
    def _format_money_value(value: str) -> str:
        raw = value.replace(",", "")
        try:
            num = float(raw)
        except ValueError:
            return value
        if abs(num) >= 1000 and abs(num - round(num)) < 1e-6:
            return f"{num:,.0f}"
        if abs(num) >= 1000:
            return f"{num:,.2f}".rstrip("0").rstrip(".")
        return value

    def _prefix_dollar(match: re.Match) -> str:
        prefix = match.group(1)
        amount = _format_money_value(match.group(2))
        if "ratio" in prefix.lower():
            return f"{prefix}{amount}"
        return f"{prefix}${amount}"
    cleaned = re.sub(
        rf"({money_keywords}[^\d$]{{0,40}})(\d{{1,3}}(?:,\d{{3}})+(?:\.\d+)?|\d+(?:\.\d+)?)(?!\s*%)(?!\s*(?:days?|months?|years?))\b",
        _prefix_dollar,
        cleaned,
        flags=re.IGNORECASE,
    )
    def _money_per_month(match: re.Match) -> str:
        if match.group(1):
            return match.group(0)
        return f"${_format_money_value(match.group(2))} per month"
    cleaned = re.sub(
        r"(\$)?(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(?:a|per|each|/)\s*(?:month|mo)\b",
        _money_per_month,
        cleaned,
        flags=re.IGNORECASE,
    )
    def _range_with_dollars(match: re.Match) -> str:
        left = _format_money_value(match.group(1))
        right = _format_money_value(match.group(2))
        return f"${left} to ${right}"

    def _amount_before_keyword(match: re.Match) -> str:
        amount = _format_money_value(match.group(1))
        keyword = match.group(2)
        return f"${amount} {keyword}"

    # Only separate truly concatenated dollar amounts (no commas), avoid splitting "$10,200"
    cleaned = re.sub(r"(\$\d{4,})(?=\$)", r"\1 - ", cleaned)
    cleaned = re.sub(r"(\$\d{4,})(\d{4,})", r"\1 - $\2", cleaned)
    cleaned = re.sub(r"\b(\d{1,2})-(\d{1,2})\s+months\b", r"\1 to \2 months", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bemergency fund (of|for) 36 months\b", r"emergency fund \1 3 to 6 months", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"\$(\d[\d,]*)(?:\.\d+)?\s+to\s+(\d[\d,]*)(?:\.\d+)?",
        _range_with_dollars,
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b(\d{1,3}(?:,\d{3})+|\d{4,})(?:\.\d+)?\s+to\s+(\d{1,3}(?:,\d{3})+|\d{4,})(?:\.\d+)?\b",
        _range_with_dollars,
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b(\d{1,3}(?:,\d{3})+|\d{4,})(?:\.\d+)?\s+(debt|income|expenses|savings|cash flow|budget)\b",
        _amount_before_keyword,
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\$\s*(\d[\d,]*)(?:\.\d+)?\b", lambda m: f"${_format_money_value(m.group(1))}", cleaned)
    cleaned = re.sub(r"\${2,}", "$", cleaned)
    cleaned = normalize_zero_amounts(cleaned)
    cleaned = cleaned.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[\t\r ]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = cleaned.strip()
    return cleaned


def normalize_zero_amounts(text: str) -> str:
    if not text:
        return ""
    zero_map = [
        ("monthly support", "monthly support"),
        ("support", "incoming support"),
        ("severance", "severance"),
        ("unemployment benefit", "unemployment benefits"),
        ("other income", "other income"),
        ("one-time income", "one-time income"),
        ("one time income", "one-time income"),
        ("one-time expense", "one-time expenses"),
        ("one time expense", "one-time expenses"),
        ("debt payment", "monthly debt payments"),
        ("healthcare", "healthcare costs"),
        ("dependent care", "dependent care costs"),
        ("job search", "job search costs"),
        ("extra monthly", "extra monthly expenses"),
        ("relocation", "relocation costs"),
        ("monthly expenses", "monthly expenses"),
        ("emergency buffer", "emergency buffer target"),
    ]
    lines = text.splitlines()
    normalized: List[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or "$0" not in stripped:
            normalized.append(line)
            continue
        lower = stripped.lower()
        handled = False
        for key, phrase in zero_map:
            if key in lower:
                prefix = "- " if stripped.startswith("-") else ""
                normalized.append(f"{prefix}You have no {phrase}.")
                handled = True
                break
        if handled:
            continue
        normalized.append(re.sub(r"\$0(?:\.0+)?", "no", stripped))
    return "\n".join(normalized)






















































def is_small_talk(prompt_text: str) -> bool:
    if not prompt_text:
        return False
    normalized = normalize_chat_text(prompt_text)
    if len(normalized) > 40:
        return False
    if re.search(r"\d", normalized):
        return False
    finance_terms = [
        "budget", "debt", "savings", "income", "expenses", "runway", "risk", "loan", "credit",
        "job", "layoff", "laid off", "unemployment", "fired", "severance", "salary", "raise", "promotion",
        "rent", "mortgage", "insurance", "bills", "burn", "cash flow", "cashflow",
    ]
    if any(term in normalized for term in finance_terms):
        return False
    if "what if" in normalized:
        return False
    greetings = [
        "hi", "hello", "hey", "yo", "sup", "hola", "howdy",
        "good morning", "good afternoon", "good evening", "gm", "gn",
        "thanks", "thank you", "appreciate it",
        "how are you", "hows it going", "what's up", "whats up",
    ]
    return any(normalized == g or normalized.startswith(g + " ") for g in greetings)


def is_clarification_request(prompt_text: str) -> bool:
    if not prompt_text:
        return False
    return bool(
        re.search(
            r"\b(clarify|clarification|explain|explanation|unpack|elaborate|expand|break\s+that\s+down|what\s+do\s+you\s+mean|can\s+you\s+go\s+deeper|tell\s+me\s+more|why|how\s+so)\b",
            prompt_text,
            flags=re.IGNORECASE,
        )
    )


def is_short_affirmation(prompt_text: str) -> bool:
    normalized = normalize_chat_text(prompt_text)
    return normalized in {
        "yes",
        "yeah",
        "yep",
        "sure",
        "ok",
        "okay",
        "please",
        "yes please",
        "sure please",
    }


def is_analysis_intent(prompt_text: str) -> bool:
    if not prompt_text:
        return False
    lowered = normalize_chat_text(prompt_text)
    triggers = [
        "analyze",
        "analysis",
        "summary",
        "assess",
        "risk",
        "runway",
        "cash flow",
        "cashflow",
        "debt ratio",
        "financial position",
        "what if",
        "scenario",
        "job loss",
        "lose my job",
        "surplus",
        "deficit",
        "burn",
        "breakdown",
        "recommend",
        "what should i do",
        "next steps",
    ]
    return any(term in lowered for term in triggers)


def user_requested_simple_terms(prompt_text: str) -> bool:
    if not prompt_text:
        return False
    return bool(
        re.search(
            r"\b(simple|simply|simpler|plain\s+english|plain\s+language|easy\s+terms|easy\s+to\s+understand|break\s+it\s+down)\b",
            prompt_text,
            flags=re.IGNORECASE,
        )
    )




def is_job_loss_intent(prompt_text: str) -> bool:
    if not prompt_text:
        return False
    normalized = normalize_chat_text(prompt_text)
    triggers = [
        "lose my job",
        "job loss",
        "laid off",
        "layoff",
        "fired",
        "unemployment",
        "income stops",
        "no income",
    ]
    return any(term in normalized for term in triggers)


def was_followup_prompt(assistant_text: str) -> bool:
    if not assistant_text:
        return False
    return bool(
        re.search(
            r"(would you like|want me to|should i|do you want me to).+\?$",
            assistant_text.strip(),
            flags=re.IGNORECASE | re.DOTALL,
        )
    )


def should_use_structured_chat_response(prompt_text: str, chat_history: List[Dict[str, str]]) -> bool:
    if is_small_talk(prompt_text):
        return False
    if is_clarification_request(prompt_text):
        return False
    if is_short_affirmation(prompt_text):
        last_assistant = next((m for m in reversed(chat_history) if m.get("role") == "assistant"), None)
        if last_assistant and was_followup_prompt(last_assistant.get("content", "")):
            return False
    return is_analysis_intent(prompt_text)


def normalize_chat_text(text: str) -> str:
    lowered = text.strip().lower()
    cleaned = re.sub(r"[^a-z0-9\\s]", " ", lowered)
    cleaned = re.sub(r"\\s+", " ", cleaned).strip()
    return cleaned








def parse_summary_sections(text: str) -> Dict[str, Any]:
    if not text:
        return {"sections": {}}
    text = split_inline_structured_sections(text)
    headers = [
        "Summary",
        "Key Facts",
        "What this means",
        "What to do first",
        "Actions",
        "Warnings",
    ]
    header_pattern = r"^(summary|key facts|what this means|what to do first|actions|warnings)\s*:?\s*$"
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    sections: Dict[str, List[str]] = {header: [] for header in headers}
    current = ""

    def normalize_header(raw: str) -> str:
        lookup = {
            "summary": "Summary",
            "key facts": "Key Facts",
            "what this means": "What this means",
            "what to do first": "What to do first",
            "actions": "Actions",
            "warnings": "Warnings",
        }
        return lookup.get(raw.lower(), raw)

    for line in lines:
        header_match = re.match(header_pattern, line, flags=re.IGNORECASE)
        if header_match:
            current = normalize_header(header_match.group(1))
            continue
        bullet_match = re.match(r"^[-•*]\s*(.*)", line)
        if bullet_match and current:
            bullet_text = bullet_match.group(1).strip()
            if bullet_text:
                sections[current].append(bullet_text)
            continue
        if current:
            sections[current].append(line)

    def _clean_bullet(text_line: str, section_name: str) -> str:
        cleaned = clean_text_block(text_line)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if cleaned in {".", ":", "-"}:
            return ""
        cleaned = re.sub(r"[.:]+\s*$", "", cleaned).strip()
        if cleaned in {"", ".", ":", "-"}:
            return ""
        cleaned = re.sub(r"(\d)\s+%", r"\1%", cleaned)
        if cleaned and cleaned[0].isalpha():
            cleaned = cleaned[0].upper() + cleaned[1:]
        if section_name == "Key Facts":
            cleaned = re.sub(r"[.!?]+\s*$", "", cleaned).strip()
            return cleaned
        if cleaned and cleaned[-1] not in ".!?":
            cleaned += "."
        return cleaned

    for key in list(sections.keys()):
        sections[key] = [_clean_bullet(item, key) for item in sections[key] if item.strip()]
        sections[key] = [item for item in sections[key] if item]

    return {"sections": sections}


def split_inline_structured_sections(text: str) -> str:
    if not text:
        return ""
    header_map = {
        "summary": "Summary",
        "key facts": "Key Facts",
        "what this means": "What this means",
        "what to do first": "What to do first",
        "actions": "Actions",
        "warnings": "Warnings",
    }
    header_re = re.compile(
        r"(?i)\b(summary|key facts|what this means|what to do first|actions|warnings)\s*:"
    )
    matches = list(header_re.finditer(text))
    # Only normalize when this clearly looks like a structured response.
    if len(matches) < 2:
        return text.strip()

    def _repl(match: re.Match) -> str:
        canonical = header_map.get(match.group(1).lower(), match.group(1))
        return f"\n{canonical}:\n"

    fixed = header_re.sub(_repl, text)
    fixed = re.sub(r"(?m)^\s*[-*•]\s*[.:]\s*$", "", fixed)
    fixed = re.sub(r"(?m)^\s*[.:]\s*$", "", fixed)
    fixed = re.sub(r"\n{3,}", "\n\n", fixed)
    return fixed.strip()


def enforce_currency_consistency(text: str) -> str:
    if not text:
        return ""
    header_pattern = re.compile(
        r"^(Summary|Key Facts|What this means|What to do first|Actions|Warnings):$",
        flags=re.IGNORECASE,
    )
    lines = text.splitlines()
    normalized: List[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or header_pattern.match(stripped):
            normalized.append(line)
            continue
        if stripped.startswith("- "):
            content = stripped[2:].strip()
            normalized.append(f"- {clean_text_block(content)}")
            continue
        normalized.append(clean_text_block(stripped))
    normalized_text = "\n".join(normalized).strip()

    money_terms = (
        r"income|expenses?|spending|costs?|savings?|debt|surplus|deficit|cash\s*flow|burn|"
        r"balance|payment|payments|salary|wage|budget|outflow|inflow|support|severance|benefits?"
    )
    number_token = r"(?:\d{1,3}(?:,\d{3})+|\d{1,4})(?:\.\d+)?(?:[kKmMbB])?"

    def _prefix_context_money(match: re.Match) -> str:
        prefix = match.group(1)
        sign = match.group(2) or ""
        amount = match.group(3)
        if re.search(r"(?i)(risk score|debt ratio|ratio|/100)", prefix):
            return f"{prefix}{sign}{amount}"
        return f"{prefix}{sign}${amount}"

    def _prefix_number_before_money(match: re.Match) -> str:
        sign = match.group(1) or ""
        amount = match.group(2)
        return f"{sign}${amount}"

    # Term appears before the amount, e.g. "monthly expenses: 3,720"
    normalized_text = re.sub(
        rf"(?i)\b((?:{money_terms})[^\n$]{{0,30}}?)([+-]?)(?<![\d,$.])({number_token})(?!,\d)(?!\.\d)\b(?!\s*%)(?!\s*/\s*100\b)(?!\s*(?:months?|years?)\b)",
        _prefix_context_money,
        normalized_text,
    )

    # Amount appears before the term, e.g. "5,200 monthly income", "12,000 in savings"
    normalized_text = re.sub(
        rf"(?i)(?<![\d,$.])([+-]?)({number_token})(?!,\d)(?!\.\d)\b(?=\s*(?:in\s+|of\s+)?(?:monthly|annual|yearly)?\s*(?:{money_terms})\b)",
        _prefix_number_before_money,
        normalized_text,
    )
    # Never treat numbered list markers like "1.", "2.", "3." as money.
    # Handles markers after sentence boundaries and markdown wrappers.
    normalized_text = re.sub(
        r"(?m)(^|[\n:.!?]\s+)\$(\d{1,2})\.(?=\s*(?:\*\*|[*_-]|[A-Za-z(]|$))",
        r"\1\2.",
        normalized_text,
    )
    normalized_text = re.sub(
        r"(?m)(^|\s)\$(\d{1,2})\.(?=\s*(?:\*\*|[*_-]|[A-Za-z(]|$))",
        r"\1\2.",
        normalized_text,
    )
    normalized_text = re.sub(r"\${2,}", "$", normalized_text)
    return normalized_text


def render_summary_html(summary_text: str) -> str:
    summary_text = enforce_readability_guardrail(summary_text, fallback=NON_INVESTMENT_FALLBACK)
    parsed = parse_summary_sections(summary_text)
    sections: Dict[str, List[str]] = parsed["sections"]
    order = ["Summary", "Key Facts", "What this means", "What to do first", "Actions", "Warnings"]

    parts: List[str] = []
    for header in order:
        bullets = sections.get(header, [])
        if not bullets:
            continue
        items = "".join([f"<li>{html.escape(b)}</li>" for b in bullets])
        parts.append(
            f"<div class='summary-section'>"
            f"<div class='summary-section-title'>{header}</div>"
            f"<ul class='summary-list'>{items}</ul>"
            f"</div>"
        )
    if not parts:
        return f"<div class='summary-text'>{html.escape(summary_text)}</div>"
    return "".join(parts)












def build_scenario_fallback_summary(
    profile: Dict[str, Any],
    scenario: Dict[str, Any],
    metrics: Dict[str, float],
) -> str:
    def money(value: float) -> str:
        return f"${value:,.0f}"

    living_expenses = float(profile.get("expenses_monthly", 0.0))
    baseline_debt_payment = profile_monthly_debt_payment(profile)
    base_required_expenses = living_expenses + baseline_debt_payment
    monthly_expenses_cut = float(metrics.get("monthly_expenses_cut", base_required_expenses))
    if monthly_expenses_cut <= 0 and base_required_expenses > 0:
        monthly_expenses_cut = base_required_expenses
    monthly_support = float(metrics.get("monthly_support", 0.0))
    monthly_net_burn = float(metrics.get("monthly_net_burn", 0.0))
    runway_months = float(metrics.get("runway_months", 0.0))
    debt_ratio = float(metrics.get("debt_ratio", 0.0))
    risk_score = float(metrics.get("risk_score", 0.0))
    income_start_month = int(float(scenario.get("income_start_month", 0) or 0))
    income_start_amount = float(scenario.get("income_start_amount", 0.0) or 0.0)
    months_unemployed = int(float(scenario.get("months_unemployed", 0) or 0))

    savings = float(profile.get("savings", 0.0))
    severance = float(scenario.get("severance", 0.0))
    one_time_income = float(scenario.get("one_time_income", 0.0))
    one_time_total = float(scenario.get("one_time_expense", 0.0)) + float(scenario.get("relocation_cost", 0.0))
    starting_cash = savings + severance + one_time_income - one_time_total

    emergency_low = monthly_expenses_cut * 3
    emergency_high = monthly_expenses_cut * 6

    income_change_monthly = float(scenario.get("income_change_monthly", 0.0))
    monthly_addons = (
        float(scenario.get("extra_monthly_expenses", 0.0))
        + float(scenario.get("debt_payment_monthly", 0.0))
        + float(scenario.get("healthcare_monthly", 0.0))
        + float(scenario.get("dependent_care_monthly", 0.0))
        + float(scenario.get("job_search_monthly", 0.0))
    )
    if income_change_monthly < 0:
        monthly_addons += abs(income_change_monthly)
    computed_net_burn = monthly_net_burn
    if monthly_support <= 0:
        support_phrase = "with no incoming cash"
    else:
        support_phrase = f"with {money(monthly_support)} in monthly support"

    if monthly_net_burn > 0:
        if runway_months >= float(TIMELINE_HORIZON_MONTHS):
            verdict = (
                "Verdict: Cash flow is negative during the stress phase, "
                "but savings do not deplete within the modeled horizon."
            )
        elif months_unemployed > 0:
            verdict = (
                f"Verdict: During the unemployment phase, your buffer lasts about {runway_months:.1f} months "
                "before cash runs out."
            )
        else:
            verdict = (
                f"Verdict: At the current burn rate, your buffer lasts about {runway_months:.1f} months "
                "before the cash runs out."
            )
    else:
        verdict = "Verdict: Your cash flow is positive under this scenario, so the near-term outlook is stable."

    if abs(computed_net_burn) < 0.01:
        burn_line = (
            f"- Monthly expenses after cuts are {money(monthly_expenses_cut)} and monthly support matches them, "
            "so cash flow is break-even."
        )
    elif monthly_addons > 0:
        burn_line = (
            f"- Required monthly expenses after cuts are {money(monthly_expenses_cut)} plus "
            f"{money(monthly_addons)} in add-ons {support_phrase}, leaving a net burn of "
            f"{money(computed_net_burn)}/mo."
            if computed_net_burn > 0
            else f"- Required monthly expenses after cuts are {money(monthly_expenses_cut)} with add-ons of "
            f"{money(monthly_addons)} {support_phrase}, leaving a surplus of {money(abs(computed_net_burn))}/mo."
        )
    else:
        burn_line = (
            f"- Monthly expenses after cuts are {money(monthly_expenses_cut)} "
            f"{support_phrase}, leaving a net burn of {money(computed_net_burn)}/mo."
            if computed_net_burn > 0
            else f"- Monthly support covers expenses, leaving a surplus of {money(abs(computed_net_burn))}/mo."
        )
    if income_start_month > 0 and income_start_amount > 0:
        net_after = computed_net_burn - income_start_amount
        burn_line += f" Additional income of {money(income_start_amount)}/mo starts month {income_start_month}, reducing net burn to about {money(net_after)}/mo."

    summary_lines = [
        verdict,
        "Summary:",
        burn_line,
    ]
    if baseline_debt_payment > 0:
        summary_lines.append(
            f"- Baseline debt payments of {money(baseline_debt_payment)}/mo are included in required expenses."
        )
    if computed_net_burn > 0:
        summary_lines.append(
            f"- Starting cash is about {money(starting_cash)}, giving a runway of roughly {runway_months:.1f} months."
        )
    else:
        summary_lines.append("- Cash flow is positive under this scenario; runway is not a near-term constraint.")
    summary_lines.append(
        f"- Debt ratio is {debt_ratio:.2f} ({debt_ratio*100:.0f}% of annual income) and risk score is {risk_score:.0f}/100."
    )

    action_lines = [
        "Actions:",
        f"- Target an emergency buffer of {money(emergency_low)} to {money(emergency_high)} at the reduced expense level.",
        "- Lower the net burn by trimming discretionary costs and pausing non-essential subscriptions.",
        "- If debt carries interest, prioritize reducing high-interest balances while maintaining cash reserves.",
    ]

    warning_lines = [
        "Warnings:",
        (
            f"- At the current burn, cash could run out in about {runway_months:.1f} months without new income."
            if monthly_net_burn > 0
            else "- If support drops or expenses rise, the surplus can disappear quickly."
        ),
        "- Rising costs or delayed income can shorten the buffer faster than expected.",
        f"- Debt ratio near {debt_ratio*100:.0f}% limits flexibility if the scenario persists.",
    ]

    return "\n".join(summary_lines + action_lines + warning_lines)


def build_baseline_fallback_summary(
    profile: Dict[str, Any],
    monthly_net: float,
    runway_months: float,
    metrics: Dict[str, float],
) -> str:
    def money(value: float) -> str:
        return f"${value:,.0f}"

    living_expenses = float(profile.get("expenses_monthly", 0.0))
    baseline_debt_payment = profile_monthly_debt_payment(profile)
    expenses = living_expenses + baseline_debt_payment
    savings = float(profile.get("savings", 0.0))
    debt = float(profile.get("debt", 0.0))
    debt_ratio = float(metrics.get("debt_ratio", 0.0))
    risk_score = float(metrics.get("risk_score", 0.0))

    if monthly_net >= 0:
        verdict = "Verdict: You have positive cash flow today, so stability hinges on keeping expenses controlled."
        cash_line = f"- Monthly surplus is {money(monthly_net)} after {money(expenses)} in expenses."
        runway_line = "- Cash flow is positive, so runway is not a near-term constraint."
    else:
        verdict = (
            f"Verdict: At the current burn, savings could run out in about {runway_months:.1f} months."
        )
        cash_line = f"- Monthly deficit is {money(abs(monthly_net))} after {money(expenses)} in expenses."
        runway_line = f"- Savings of {money(savings)} imply a runway near {runway_months:.1f} months."

    summary_lines = [
        verdict,
        "Summary:",
        cash_line,
        (
            f"- This includes baseline debt payments of {money(baseline_debt_payment)}/mo."
            if baseline_debt_payment > 0
            else "- No baseline monthly debt payment is configured."
        ),
        f"- Savings are {money(savings)} versus debt of {money(debt)} (debt ratio {debt_ratio:.2f}, {debt_ratio*100:.0f}% of annual income).",
        runway_line,
    ]

    emergency_low = expenses * 3
    emergency_high = expenses * 6
    action_lines = [
        "Actions:",
        f"- Build an emergency buffer of {money(emergency_low)} to {money(emergency_high)}.",
        "- Keep expenses stable and track any drift month to month.",
        "- Reduce high-interest debt to improve flexibility.",
    ]

    warning_lines = [
        "Warnings:",
        "- Rising expenses can quickly erode the surplus or shorten runway.",
        f"- A risk score near {risk_score:.0f}/100 means shocks can still hurt without a buffer.",
        "- Avoid adding new debt while building cash reserves.",
    ]

    return "\n".join(summary_lines + action_lines + warning_lines)


def format_nemotron_error(message: str, context: str) -> str:
    base = "Nemotron is unavailable right now."
    if os.getenv("NIM_DEBUG", "").lower() in {"1", "true", "yes"} and message:
        return f"{base} Debug: {message}"
    if not message:
        return base
    lowered = message.lower()
    if "missing nvidia_api_key" in lowered or "api key" in lowered or "unauthorized" in lowered or "401" in lowered:
        return f"{base} Missing or invalid NVIDIA_API_KEY."
    if "openai client is unavailable" in lowered:
        return f"{base} OpenAI client missing; install the openai package."
    if "timeout" in lowered:
        return f"{base} The request timed out."
    if "connection" in lowered or "refused" in lowered or "name or service not known" in lowered:
        return f"{base} Could not reach the NIM endpoint."
    if "unavailable" in lowered:
        return base
    return base


def format_currency(value: float) -> str:
    return f"${value:,.0f}"


def format_pct(value: float) -> str:
    return f"{value:.0f}%"


def format_ratio(value: float) -> str:
    return f"{value:.2f}"


def format_months(value: float) -> str:
    return f"{value:.1f} months"


def format_money_signed(value: float) -> str:
    if value < 0:
        return f"-${abs(value):,.0f}"
    return f"${value:,.0f}"


def profile_monthly_debt_payment(profile: Dict[str, Any]) -> float:
    try:
        return max(float(profile.get("debt_payment_monthly", 0.0)), 0.0)
    except (TypeError, ValueError, AttributeError):
        return 0.0


def profile_total_monthly_expenses(profile: Dict[str, Any]) -> float:
    try:
        living_expenses = max(float(profile.get("expenses_monthly", 0.0)), 0.0)
    except (TypeError, ValueError, AttributeError):
        living_expenses = 0.0
    return living_expenses + profile_monthly_debt_payment(profile)


def clean_text_block(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text).strip()
    cleaned = re.sub(r"(\d)\s+%", r"\1%", cleaned)
    cleaned = re.sub(r"(?i)\b(\d+(?:\.\d+)?)\s+([kmb])\b", r"\1\2", cleaned)
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"(?<=\d)(?=(?![kKmMbB]\b)[A-Za-z])", " ", cleaned)
    cleaned = cleaned.replace("$$", "$")
    cleaned = re.sub(r"\bthe user's\b", "your", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bthe user\b", "you", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\buser's\b", "your", cleaned, flags=re.IGNORECASE)
    money_candidate_pattern = re.compile(
        r"(?<!\$)\b(\d{1,3}(?:,\d{3})+|\d{4,})\b(?!\s*(?:months?\b|years?\b|%|/100\b|/mo\b|/month\b|/year\b|/week\b))"
    )
    source_text = cleaned

    def _prefix_money(match: re.Match) -> str:
        number = match.group(1)
        start, end = match.span(1)
        prev_char = source_text[start - 1] if start > 0 else ""
        next_char = source_text[end] if end < len(source_text) else ""
        if (prev_char and prev_char in "/-") or (next_char and next_char in "/-"):
            return number

        plain = number.replace(",", "")
        prev_window = source_text[max(0, start - 24):start].lower()
        next_window = source_text[end:end + 32].lower()

        if plain.isdigit() and len(plain) == 4:
            year_value = int(plain)
            if 1900 <= year_value <= 2100:
                if re.search(
                    r"(?:^|\b)(?:in|on|by|from|since|until|through|during|to|before|after|around|year)\s*$",
                    prev_window,
                ):
                    return number
                if re.search(r"(?:\d{1,2}[/-])\s*$", prev_window):
                    return number

        if plain in {"1099", "1040"} and re.match(r"\s*(?:income\b|form\b)", next_window):
            return number
        if plain in {"401", "403", "457"} and re.match(r"\s*k\b", next_window):
            return number
        return f"${number}"

    cleaned = money_candidate_pattern.sub(_prefix_money, source_text)
    cleaned = re.sub(
        r"(?<!\$)(?<![\d,])\b(\d+(?:,\d{3})*(?:\.\d+)?)\b(?=\s*(?:monthly|yearly|annually|per\s+month|per\s+year|each\s+month|each\s+year|/mo|/month|/yr|/year)\b)",
        r"$\1",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"(?i)\b((?:monthly\s+surplus|monthly\s+deficit|surplus|deficit|savings?|debt|income|expenses?|payments?|salary|budget|cash\s*flow|burn|buffer)\s*(?:of|is|are|was|were|:)?\s*)(?<!\$)(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\b(?!\s*%)(?!\s*/\s*100\b)",
        lambda m: f"{m.group(1)}${m.group(2)}",
        cleaned,
    )

    contextual_amount_pattern = re.compile(r"(?<![\d,$])\b(\d{3,}(?:,\d{3})*(?:\.\d+)?)\b")
    context_words = re.compile(
        r"(income|earnings|salary|expenses?|spend(?:ing)?|costs?|surplus|deficit|savings?|debt|payment|cash\s*flow|burn|shortfall|budget|buffer|support|fund|payout|severance|benefit)",
        flags=re.IGNORECASE,
    )

    def _prefix_contextual_amount(match: re.Match) -> str:
        amount = match.group(1)
        start, end = match.span(1)
        prev = cleaned[max(0, start - 48):start].lower()
        nxt = cleaned[end:end + 32].lower()
        nearby = f"{prev} {nxt}"

        if re.match(r"\s*(?:months?\b|years?\b|%|/100\b|/mo\b|/month\b|/yr\b|/year\b)", nxt):
            return amount
        if re.search(r"(risk score|score|/100|percent|%)", nearby):
            return amount
        if re.search(r"\bmonth\s+\d+\s*$", prev):
            return amount
        if context_words.search(nearby):
            return f"${amount}"
        return amount

    cleaned = contextual_amount_pattern.sub(_prefix_contextual_amount, cleaned)
    cleaned = re.sub(
        r"(?i)\b(?<!\$)([+-]?\d+(?:\.\d+)?[kmb])\b(?=\s*(?:down-?payment|payment|income|expenses?|costs?|savings?|debt|mortgage|rent|loan|budget|surplus|deficit|cash\s*flow|burn|balance|reserve|buffer))",
        r"$\1",
        cleaned,
    )
    cleaned = re.sub(
        r"(?i)\b((?:income|savings?|debt|payment|payments|budget|costs?|expenses?|cash\s*flow|burn|down-?payment)\s*(?:of|is|are|was|were|:)?\s*)(?<!\$)([+-]?\d+(?:\.\d+)?[kmb])\b",
        r"\1$\2",
        cleaned,
    )

    def _rewrite_job_stability(match: re.Match) -> str:
        industry = re.sub(r"^\s*the\s+", "", match.group(1).strip(), flags=re.IGNORECASE)
        if industry.lower().endswith("industry"):
            return f"job in the {industry}"
        return f"job in the {industry} industry"

    cleaned = re.sub(
        r"\bjob stability in\s+([A-Za-z][A-Za-z &/\-]*)(?=[,.;!?]|$)",
        _rewrite_job_stability,
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip()


def contains_investment_terms(text: str) -> bool:
    return bool(INVESTMENT_TERMS_PATTERN.search(text or ""))


def enforce_non_investment_policy(text: str) -> str:
    if not text:
        return ""

    structured_header = re.compile(
        r"^(Summary|Key Facts|What this means|What to do first|Actions|Warnings):$",
        flags=re.IGNORECASE | re.MULTILINE,
    )
    has_structured_sections = bool(structured_header.search(text))

    if not has_structured_sections:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
        kept = [s for s in sentences if not contains_investment_terms(s)]
        if kept:
            return " ".join(kept).strip()
        return NON_INVESTMENT_FALLBACK

    lines = text.splitlines()
    cleaned_lines: List[str] = []
    current_section = ""
    inserted_action_fallback = False

    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped:
            cleaned_lines.append(raw_line)
            continue

        header_match = structured_header.match(stripped)
        if header_match:
            current_section = header_match.group(1).lower()
            cleaned_lines.append(raw_line)
            inserted_action_fallback = False
            continue

        if not contains_investment_terms(stripped):
            cleaned_lines.append(raw_line)
            continue

        if current_section in {"what to do first", "actions"}:
            if not inserted_action_fallback:
                cleaned_lines.append(
                    "- Keep extra cash focused on debt reduction and emergency savings until your buffer is strong."
                )
                inserted_action_fallback = True
            continue

        if current_section == "summary":
            cleaned_lines.append(
                "You are strongest when you keep cash flow steady, reduce debt pressure, and build your emergency buffer."
            )
            continue
        if current_section == "what this means":
            cleaned_lines.append(
                "The most reliable next step is to protect monthly cash flow, lower debt stress, and keep building reserves."
            )
            continue
        if current_section == "warnings":
            cleaned_lines.append("Keep your plan focused on near-term cash stability and debt resilience.")
            continue

    result = "\n".join(cleaned_lines)
    result = re.sub(r"\n{3,}", "\n\n", result).strip()
    return result or NON_INVESTMENT_FALLBACK


def capitalize_first(text: str) -> str:
    if not text:
        return ""
    return text[0].upper() + text[1:]


def has_placeholder_artifacts(text: str) -> bool:
    if not text:
        return False
    patterns = [
        r"\$[A-Za-z]+",
        r"\{\{.*?\}\}",
        r"\bdebt ratio\s+is\s+debt\b",
        r"\bdebt ratio\s+near\s+debt\b",
        r"\brisk score\s+is\s+\$\d",
        r"\bmonths?\s+\$\d",
        r"\$\d{1,3}(?:,\d{3})+\s*-\s*\$?\d",
        r"\d+/\d+/\d+",
    ]
    return any(re.search(p, text) for p in patterns)


def has_corrupted_spacing(text: str) -> bool:
    if not text:
        return False
    normalized = re.sub(r"\s+", " ", str(text)).strip()
    if not normalized:
        return False

    long_tokens = re.findall(r"\b[A-Za-z]{14,}\b", normalized)
    if len(long_tokens) >= 2:
        return True
    if any(len(token) >= 22 for token in long_tokens):
        return True
    if re.search(r"\b[A-Za-z]{3,}\d{2,}[A-Za-z]{3,}\b", normalized):
        return True
    if re.search(r"\b\d{1,3}(?:,\d{3})+[A-Za-z]{4,}\b", normalized):
        return True
    if re.search(r"\b[A-Za-z]{4,}\d{1,3}(?:,\d{3})+\b", normalized):
        return True

    glued_patterns = [
        r"[A-Za-z]{3,}incomeand[A-Za-z]{2,}",
        r"[A-Za-z]{3,}expensesand[A-Za-z]{2,}",
        r"[A-Za-z]{3,}cashflow[A-Za-z]{2,}",
        r"[A-Za-z]{3,}burningthrough[A-Za-z]{2,}",
        r"[A-Za-z]{3,}ifyou[A-Za-z]{2,}",
        r"[A-Za-z]{3,}yourcashflow[A-Za-z]{2,}",
        r"[A-Za-z]{3,}monthlyincome[A-Za-z]{2,}",
        r"[A-Za-z]{3,}monthlysurplus[A-Za-z]{2,}",
        r"[A-Za-z]{3,}monthlydeficit[A-Za-z]{2,}",
    ]
    if any(re.search(pattern, normalized, flags=re.IGNORECASE) for pattern in glued_patterns):
        return True

    suspicious_tokens = [
        "monthlybaseline",
        "thenallocate",
        "allocateany",
        "anysurplus",
        "flowtoward",
        "towardthe",
    ]
    if any(re.search(rf"(?i)\b{token}\b", normalized) for token in suspicious_tokens):
        return True

    repeated_chunk = re.search(r"(?i)\b([a-z][a-z\s,-]{16,}?)\1\b", normalized)
    if repeated_chunk:
        return True

    finance_roots = r"(income|expense|expenses|savings|debt|cashflow|cash|flow|surplus|deficit|runway|risk|month|monthly)"
    if re.search(rf"(?i)\b[a-z]*{finance_roots}[a-z]*{finance_roots}[a-z]*\b", normalized):
        return True

    return False


def has_garbled_sequences(text: str) -> bool:
    if not text:
        return False
    normalized = re.sub(r"\s+", " ", str(text)).strip()
    if not normalized:
        return False
    patterns = [
        r"(?i)\b(?:\$?\d{1,3}(?:,\d{3})*(?:\s*-\s*\$?\d{1,3}(?:,\d{3})*){2,})\b",
        r"(?i)\b\d{1,3}(?:,\d{3})+[A-Za-z]{4,}",
        r"(?i)\b[A-Za-z]{4,}\d{1,3}(?:,\d{3})+[A-Za-z]{2,}",
        r"(?i)\bto reduce the \$?\d{1,3}\s+finally\b",
        r"(?i)\bdebttoreducethe\b",
        r"(?i)\bsetuparecurringtransferthatmovesatleast\b",
        r"(?i)(finally,\s*set up a recurring transfer that moves at least.{0,120})\1",
    ]
    return any(re.search(pattern, normalized) for pattern in patterns)


def collapse_repeated_token_runs(text: str) -> str:
    if not text:
        return ""
    tokens = text.split()
    if len(tokens) < 12:
        return text
    out: List[str] = []
    i = 0
    while i < len(tokens):
        collapsed = False
        max_n = min(18, (len(tokens) - i) // 2)
        for n in range(max_n, 4, -1):
            left = tokens[i : i + n]
            right = tokens[i + n : i + 2 * n]
            if left == right:
                out.extend(left)
                i += 2 * n
                collapsed = True
                break
        if not collapsed:
            out.append(tokens[i])
            i += 1
    return " ".join(out)


def repair_spacing_artifacts(text: str) -> str:
    if not text:
        return ""
    repaired = str(text)
    repaired = repaired.replace("−", "-")
    repaired = re.sub(r"([.!?])(?=[A-Za-z$])", r"\1 ", repaired)
    repaired = re.sub(r"([,;:])(?=[A-Za-z$])", r"\1 ", repaired)
    repaired = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", repaired)
    repaired = re.sub(r"(?<=\d)(?=[A-Za-z])", " ", repaired)
    repaired = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", repaired)

    word_joins = {
        "ifyou": "if you",
        "yourcashflow": "your cash flow",
        "cashflow": "cash flow",
        "monthlyincome": "monthly income",
        "monthlyexpenses": "monthly expenses",
        "monthlysurplus": "monthly surplus",
        "monthlydeficit": "monthly deficit",
        "monthlybaseline": "monthly baseline",
        "burningthrough": "burning through",
        "runwaybefore": "runway before",
        "surplusand": "surplus and",
        "deficitand": "deficit and",
        "thenallocate": "then allocate",
        "allocateany": "allocate any",
        "anysurplus": "any surplus",
        "flowtoward": "flow toward",
        "towardthe": "toward the",
        "debttoreducethe": "debt to reduce the",
        "setuparecurringtransferthatmovesatleast": "set up a recurring transfer that moves at least",
    }
    for bad, good in word_joins.items():
        repaired = re.sub(rf"(?i){bad}", good, repaired)

    repaired = re.sub(r"(?i)(surplus)(cash)", r"\1 \2", repaired)
    repaired = re.sub(r"(?i)(cash)(flow)", r"\1 \2", repaired)
    repaired = re.sub(r"(?i)(monthly)(baseline)", r"\1 \2", repaired)
    repaired = re.sub(r"(?i)(then)(allocate)", r"\1 \2", repaired)
    repaired = re.sub(r"(?i)(allocate)(any)", r"\1 \2", repaired)
    repaired = re.sub(r"(?i)(toward)(the)", r"\1 \2", repaired)
    repaired = re.sub(r"(?i)(expenses)(about)", r"\1 about", repaired)
    repaired = re.sub(r"(?i)(baseline)(then)", r"\1. \2", repaired)
    repaired = re.sub(r"([A-Za-z])\$(\d)", r"\1 $\2", repaired)
    repaired = re.sub(r"\$(\d[\d,]*)\s*-\s*(\d[\d,]*)", r"$\1-$\2", repaired)
    repaired = re.sub(r"\$(\d[\d,]*)\s+to\s+(\d[\d,]*)", r"$\1 to $\2", repaired, flags=re.IGNORECASE)
    repaired = re.sub(r"\b(\d{1,3}(?:,\d{3})*)\s*-\s*\1\s*-\s*(\d{1,3}(?:,\d{3})*)\b", r"\1-\2", repaired)
    repaired = re.sub(r"\b(\d{1,3}(?:,\d{3})*)\s+to\s+\1\s+to\s+(\d{1,3}(?:,\d{3})*)\b", r"\1 to \2", repaired, flags=re.IGNORECASE)
    repaired = re.sub(r"\b(\d+)\s*-\s*\1\s*-\s*(\d+)\b", r"\1-\2", repaired)
    repaired = re.sub(r"\b(\d+)\s+to\s+\1\s+to\s+(\d+)\b", r"\1 to \2", repaired, flags=re.IGNORECASE)
    repaired = re.sub(r"(?i)\bdebt to reduce the \d+\s+finally,\s*", "debt. Finally, ", repaired)
    repaired = re.sub(
        r"(?i)finally,\s*set up a recurring transfer that moves at least\s+\d{1,3}(?:,\d{3})*\s+debt\.\s*finally,\s*set up a recurring transfer that moves at least",
        "Finally, set up a recurring transfer that moves at least",
        repaired,
    )
    repaired = re.sub(r"(?<=\.\s)(then|and|but|so|or)\b", lambda m: m.group(1).capitalize(), repaired, flags=re.IGNORECASE)

    repaired = collapse_repeated_token_runs(repaired)
    repaired = re.sub(r"\s{2,}", " ", repaired)
    repaired = re.sub(r"\n{3,}", "\n\n", repaired)
    return repaired.strip()


def normalize_money_spacing(text: str) -> str:
    if not text:
        return ""
    cleaned = str(text)
    cleaned = re.sub(r"([A-Za-z])\$(\d)", r"\1 $\2", cleaned)
    cleaned = re.sub(r"\$(\d[\d,]*)\s*-\s*(\d[\d,]*)", r"$\1-$\2", cleaned)
    cleaned = re.sub(r"\$(\d[\d,]*)\s+to\s+(\d[\d,]*)", r"$\1 to $\2", cleaned, flags=re.IGNORECASE)
    return cleaned


def strip_markdown_artifacts(text: str) -> str:
    if not text:
        return ""
    cleaned = str(text)
    cleaned = cleaned.replace("\r\n", "\n")
    cleaned = re.sub(r"(?m)^\s*\*\s+", "- ", cleaned)
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"__(.*?)__", r"\1", cleaned)
    cleaned = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", cleaned)
    cleaned = re.sub(r"(?<!_)_([^_\n]+)_(?!_)", r"\1", cleaned)
    cleaned = cleaned.replace("`", "")
    # Preserve section/newline structure for chat rendering.
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = "\n".join(line.rstrip() for line in cleaned.splitlines())
    return cleaned.strip()


def enforce_readability_guardrail(text: str, fallback: str = "") -> str:
    prepped = html.unescape(str(text or ""))
    prepped = unicodedata.normalize("NFKC", prepped)
    prepped = re.sub(r"[\u200B-\u200D\uFEFF]", "", prepped)
    prepped = prepped.replace("−", "-").replace("—", "-").replace("–", "-")
    prepped = strip_markdown_artifacts(prepped)
    prepped = split_inline_structured_sections(prepped)
    candidate = enforce_currency_consistency(enforce_non_investment_policy(prepped))
    candidate = normalize_money_spacing(candidate)
    candidate = strip_markdown_artifacts(candidate)
    candidate = split_inline_structured_sections(candidate)
    if candidate and not has_corrupted_spacing(candidate) and not has_garbled_sequences(candidate):
        return candidate

    repaired_seed = repair_spacing_artifacts(prepped)
    repaired_seed = repair_spacing_artifacts(repaired_seed)
    repaired = enforce_currency_consistency(enforce_non_investment_policy(repaired_seed))
    repaired = normalize_money_spacing(repaired)
    repaired = strip_markdown_artifacts(repaired)
    repaired = split_inline_structured_sections(repaired)
    if repaired and not has_corrupted_spacing(repaired) and not has_garbled_sequences(repaired):
        return repaired

    if fallback:
        fallback_clean = enforce_currency_consistency(enforce_non_investment_policy(fallback))
        fallback_clean = normalize_money_spacing(fallback_clean)
        fallback_clean = strip_markdown_artifacts(fallback_clean)
        fallback_clean = split_inline_structured_sections(fallback_clean)
        if fallback_clean and not has_corrupted_spacing(fallback_clean) and not has_garbled_sequences(fallback_clean):
            return fallback_clean

    return "I can restate that clearly. Do you want me to focus on cash flow, runway, or risk?"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def sanitize_metrics(metrics: Dict[str, float]) -> Dict[str, float]:
    cleaned = dict(metrics or {})
    cleaned["monthly_net"] = _safe_float(cleaned.get("monthly_net", 0.0))
    cleaned["monthly_expenses_cut"] = max(_safe_float(cleaned.get("monthly_expenses_cut", 0.0)), 0.0)
    cleaned["monthly_support"] = max(_safe_float(cleaned.get("monthly_support", 0.0)), 0.0)
    cleaned["monthly_net_burn"] = _safe_float(cleaned.get("monthly_net_burn", 0.0))
    cleaned["one_time_expense"] = max(_safe_float(cleaned.get("one_time_expense", 0.0)), 0.0)
    cleaned["runway_months"] = max(_safe_float(cleaned.get("runway_months", 0.0)), 0.0)
    cleaned["debt_ratio"] = max(_safe_float(cleaned.get("debt_ratio", 0.0)), 0.0)
    risk_score = _safe_float(cleaned.get("risk_score", 0.0))
    if clamp:
        risk_score = clamp(risk_score, 0.0, 100.0)
    else:
        risk_score = max(min(risk_score, 100.0), 0.0)
    cleaned["risk_score"] = risk_score
    adjusted = _safe_float(cleaned.get("adjusted_risk_score", risk_score))
    if clamp:
        adjusted = clamp(adjusted, 0.0, 100.0)
    else:
        adjusted = max(min(adjusted, 100.0), 0.0)
    cleaned["adjusted_risk_score"] = adjusted
    return cleaned


def compute_financials(
    profile: Dict[str, Any],
    scenario: Dict[str, Any],
    *,
    baseline_mode: bool = False,
    horizon_months: int = 36,
) -> Dict[str, Any]:
    income = _safe_float(profile.get("income_monthly", 0.0))
    expenses = _safe_float(profile.get("expenses_monthly", 0.0))
    baseline_debt_payment = profile_monthly_debt_payment(profile)
    total_required_expenses = expenses + baseline_debt_payment
    savings = _safe_float(profile.get("savings", 0.0))
    debt = _safe_float(profile.get("debt", 0.0))

    expense_cut_pct = _safe_float(scenario.get("expense_cut_pct", 0.0))
    months_unemployed = int(_safe_float(scenario.get("months_unemployed", 0.0)))
    severance = _safe_float(scenario.get("severance", 0.0))
    unemployment_benefit_monthly = _safe_float(scenario.get("unemployment_benefit_monthly", 0.0))
    other_income_monthly = _safe_float(scenario.get("other_income_monthly", 0.0))
    income_change_monthly = _safe_float(scenario.get("income_change_monthly", 0.0))
    income_start_month = int(_safe_float(scenario.get("income_start_month", 0.0)))
    income_start_amount = _safe_float(scenario.get("income_start_amount", 0.0))
    extra_monthly_expenses = _safe_float(scenario.get("extra_monthly_expenses", 0.0))
    debt_payment_monthly = _safe_float(scenario.get("debt_payment_monthly", 0.0))
    healthcare_monthly = _safe_float(scenario.get("healthcare_monthly", 0.0))
    dependent_care_monthly = _safe_float(scenario.get("dependent_care_monthly", 0.0))
    job_search_monthly = _safe_float(scenario.get("job_search_monthly", 0.0))
    one_time_expense = _safe_float(scenario.get("one_time_expense", 0.0))
    one_time_income = _safe_float(scenario.get("one_time_income", 0.0))
    relocation_cost = _safe_float(scenario.get("relocation_cost", 0.0))

    monthly_expenses_cut = expenses * (1 - expense_cut_pct / 100.0) + baseline_debt_payment
    support_adjustment_base = unemployment_benefit_monthly + other_income_monthly + income_change_monthly
    support_shortfall = max(-support_adjustment_base, 0.0)
    support_adjustment_base = max(support_adjustment_base, 0.0)

    monthly_addons = (
        extra_monthly_expenses
        + debt_payment_monthly
        + healthcare_monthly
        + dependent_care_monthly
        + job_search_monthly
        + support_shortfall
    )
    one_time_total = one_time_expense + relocation_cost
    starting_balance = savings + severance + one_time_income - one_time_total

    def _employment_income_for_month(month: int) -> float:
        if baseline_mode:
            return income
        if months_unemployed > 0 and month <= months_unemployed:
            return 0.0
        return income

    def _support_for_month(month: int) -> float:
        employment_income = _employment_income_for_month(month)
        support = employment_income + support_adjustment_base
        if income_start_month > 0 and income_start_amount > 0 and month >= income_start_month:
            # During unemployment scenarios, treat this as replacement income.
            # Otherwise treat it as additional income on top of the existing salary.
            if not baseline_mode and months_unemployed > 0:
                support = support - employment_income + income_start_amount
            else:
                support += income_start_amount
        return support

    def _net_burn_for_month(month: int) -> float:
        return monthly_expenses_cut + monthly_addons - _support_for_month(month)

    monthly_support_first_month = _support_for_month(1)
    monthly_net_burn = _net_burn_for_month(1)

    max_months = TIMELINE_HORIZON_MONTHS
    if starting_balance <= 0:
        runway_months = 0.0
    else:
        runway_months = float(max_months)
        balance_probe = starting_balance
        for month in range(1, max_months + 1):
            burn = _net_burn_for_month(month)
            balance_after = balance_probe - burn
            if balance_after <= 0:
                if burn > 0:
                    runway_months = (month - 1) + (balance_probe / burn)
                else:
                    runway_months = float(month)
                break
            balance_probe = balance_after

    timeline: List[float] = []
    balance = starting_balance
    months_for_timeline = max(horizon_months, 1)
    for month in range(0, months_for_timeline + 1):
        if month == 0:
            timeline.append(round(balance, 2))
            continue
        balance -= _net_burn_for_month(month)
        timeline.append(round(balance, 2))

    timeline_stats = compute_timeline_stats(timeline) if compute_timeline_stats else {
        "months_until_zero": 0.0,
        "max_drawdown": 0.0,
        "trend_slope": 0.0,
    }

    debt_ratio = compute_debt_ratio(debt, income) if compute_debt_ratio else 0.0
    base_risk = compute_risk_score(
        runway_months,
        debt_ratio,
        profile.get("job_stability", "stable"),
        profile.get("industry", "Other"),
    ) if compute_risk_score else 0.0
    if adjust_risk_for_scenario and not baseline_mode:
        risk_score = adjust_risk_for_scenario(base_risk, runway_months, months_unemployed)
    else:
        risk_score = base_risk

    metrics = sanitize_metrics(
        {
            "monthly_expenses_cut": monthly_expenses_cut,
            "monthly_support": monthly_support_first_month,
            "monthly_net_burn": monthly_net_burn,
            "one_time_expense": one_time_total,
            "profile_debt_payment_monthly": baseline_debt_payment,
            "runway_months": runway_months,
            "debt_ratio": debt_ratio,
            "risk_score": risk_score,
            "adjusted_risk_score": risk_score,
        }
    )

    return {
        "metrics": metrics,
        "timeline": timeline,
        "timeline_stats": timeline_stats,
        "starting_balance": starting_balance,
        "monthly_net": income - total_required_expenses,
    }


def first_depletion_month(timeline: List[float]) -> int | None:
    for month, balance in enumerate(timeline):
        if float(balance) <= 0:
            return month
    return None


def render_timeline_chart(timeline: List[float], *, height: int = 260) -> int | None:
    if not timeline:
        st.info("No timeline data available yet.")
        return None

    points = [{"month": int(month), "balance": float(balance)} for month, balance in enumerate(timeline)]
    depletion_month = first_depletion_month(timeline)

    markers: List[Dict[str, Any]] = [
        {"month": 0, "balance": float(timeline[0]), "label": "Start", "kind": "start"}
    ]
    final_month = len(timeline) - 1
    if depletion_month is not None and depletion_month > 0:
        markers.append(
            {
                "month": int(depletion_month),
                "balance": float(timeline[depletion_month]),
                "label": "Zero cash",
                "kind": "depletion",
            }
        )
    if final_month > 0 and (depletion_month is None or final_month != depletion_month):
        markers.append(
            {
                "month": int(final_month),
                "balance": float(timeline[-1]),
                "label": "End",
                "kind": "end",
            }
        )

    st.caption("Blue line = projected cash balance by month. Orange dashed line = $0 cash threshold.")

    if alt is None:
        st.line_chart(timeline, height=height)
        return depletion_month

    base = alt.Chart(alt.Data(values=points)).encode(
        x=alt.X("month:Q", title="Month"),
        y=alt.Y("balance:Q", title="Cash balance", axis=alt.Axis(format="$,.0f")),
        tooltip=[
            alt.Tooltip("month:Q", title="Month"),
            alt.Tooltip("balance:Q", title="Cash balance", format="$,.0f"),
        ],
    )
    balance_line = base.mark_line(color="#38bdf8", strokeWidth=3)
    zero_line = alt.Chart(alt.Data(values=[{"zero": 0.0}])).mark_rule(
        color="#f97316",
        strokeDash=[8, 6],
        strokeWidth=2,
    ).encode(y="zero:Q")

    marker_layer = alt.Chart(alt.Data(values=markers)).mark_point(filled=True, size=90).encode(
        x=alt.X("month:Q", title="Month"),
        y=alt.Y("balance:Q", title="Cash balance", axis=alt.Axis(format="$,.0f")),
        color=alt.Color(
            "kind:N",
            scale=alt.Scale(
                domain=["start", "depletion", "end"],
                range=["#22c55e", "#ef4444", "#94a3b8"],
            ),
            legend=None,
        ),
        tooltip=[
            alt.Tooltip("label:N", title="Point"),
            alt.Tooltip("month:Q", title="Month"),
            alt.Tooltip("balance:Q", title="Cash balance", format="$,.0f"),
        ],
    )
    marker_labels = alt.Chart(alt.Data(values=markers)).mark_text(
        dx=8,
        dy=-8,
        color="#e2e8f0",
        fontSize=11,
    ).encode(
        x=alt.X("month:Q", title="Month"),
        y=alt.Y("balance:Q", title="Cash balance", axis=alt.Axis(format="$,.0f")),
        text="label:N",
    )

    chart = alt.layer(zero_line, balance_line, marker_layer, marker_labels).properties(height=height)
    st.altair_chart(chart, use_container_width=True)
    return depletion_month


def parse_json_response(raw: str) -> Dict[str, Any] | None:
    if not raw:
        return None
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    snippet = raw[start : end + 1]
    try:
        data = json.loads(snippet)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return data


def apply_structured_guardrails(
    data: Dict[str, Any],
    mode: str,
    profile: Dict[str, Any],
    metrics: Dict[str, float],
    scenario: Dict[str, Any] | None,
) -> Dict[str, Any]:
    guarded = dict(data or {})
    if mode != "scenario" or not scenario:
        return guarded

    scenario_values = sanitize_metrics(metrics)
    monthly_net_burn = float(scenario_values.get("monthly_net_burn", 0.0))
    net_cash_flow = -monthly_net_burn
    runway_months = float(scenario_values.get("runway_months", 0.0))
    severance = float(scenario.get("severance", 0.0))
    savings = float(profile.get("savings", 0.0))
    debt = float(profile.get("debt", 0.0))

    runway_text = f"{runway_months:.1f} months" if monthly_net_burn > 0 else "Not constrained (cash flow positive)"
    if monthly_net_burn > 0:
        guarded["summary"] = (
            f"Your scenario net cash flow is {format_money_signed(net_cash_flow)}/mo, "
            f"so current savings would last about {runway_months:.1f} months."
        )
    else:
        guarded["summary"] = (
            f"Your scenario net cash flow is {format_money_signed(net_cash_flow)}/mo, "
            "so savings are growing instead of being depleted."
        )
    guarded["key_facts"] = [
        f"Savings: {format_currency(savings)}",
        f"Debt: {format_currency(debt)}",
        f"Scenario runway: {runway_text}",
        f"Net cash flow: {format_money_signed(net_cash_flow)}/mo",
        f"Severance: {format_currency(severance)}",
    ]
    guarded["warnings"] = [
        f"Risk score is {float(scenario_values.get('risk_score', 0.0)):.0f}/100",
        (
            f"Scenario runway is about {runway_months:.1f} months at the current burn rate"
            if monthly_net_burn > 0
            else "Cash flow is positive now, but income/support changes can reverse that quickly"
        ),
    ]

    actions = [str(item).strip() for item in guarded.get("actions", []) if str(item).strip()]
    if net_cash_flow < 0:
        stripped_actions: List[str] = []
        for action in actions:
            lowered = action.lower()
            if "emergency" in lowered and "saving" in lowered and ("prioritize" in lowered or "build" in lowered):
                continue
            stripped_actions.append(action)

        baseline_actions = [
            "Cut non-essential spending immediately to reduce monthly outflow and extend runway",
            "Secure replacement income quickly through benefits, contract work, or temporary roles",
        ]
        merged_actions = baseline_actions + stripped_actions
        deduped: List[str] = []
        for action in merged_actions:
            if not action:
                continue
            normalized = re.sub(r"\s+", " ", action).strip().lower()
            if normalized not in {re.sub(r"\s+", " ", item).strip().lower() for item in deduped}:
                deduped.append(action)
        guarded["actions"] = deduped[:4]

    return guarded


def render_structured_response(
    data: Dict[str, Any],
    include_followup: bool = True,
    force_simple_terms: bool = False,
) -> str:
    def _normalize_action_wording(action_text: str) -> str:
        lowered = action_text.lower()
        if (
            "break even" in lowered
            and "cut" in lowered
            and ("expense" in lowered or "spending" in lowered)
        ):
            return "Reduce discretionary spending to lower the monthly burn as much as possible"
        if re.search(
            r"\bcut\s+\$?\d[\d,]*(?:\.\d+)?\s+(?:in\s+)?expenses?\b",
            lowered,
        ) and "break even" in lowered:
            return "Reduce discretionary spending to lower the monthly burn as much as possible"
        return action_text

    summary = clean_text_block(str(data.get("summary", "")).strip())
    key_facts = [clean_text_block(str(item)) for item in data.get("key_facts", []) if str(item).strip()]
    key_facts = [re.sub(r"[.!?]+\s*$", "", fact).strip() for fact in key_facts]
    meaning = clean_text_block(str(data.get("meaning", "")).strip())
    actions = [clean_text_block(str(item)) for item in data.get("actions", []) if str(item).strip()]
    actions = [_normalize_action_wording(item) for item in actions]
    warnings = [clean_text_block(str(item)) for item in data.get("warnings", []) if str(item).strip()]
    followup = clean_text_block(str(data.get("followup", "")).strip())

    if meaning:
        if force_simple_terms and not re.match(r"(?i)^in simple terms\s*:", meaning):
            meaning = f"In simple terms: {meaning}"
        if not force_simple_terms:
            meaning = re.sub(r"(?i)^in simple terms\s*:\s*", "", meaning).strip()

    has_concrete_action = any(re.search(r"\$?\d", item) for item in actions)
    if actions and not has_concrete_action:
        negative_cashflow = any(
            [
                re.search(r"net cash flow\s*:\s*-\$", text, flags=re.IGNORECASE) for text in [summary] + key_facts
            ]
        ) or any("deficit" in text.lower() for text in [summary] + key_facts)
        surplus_value = 0.0
        for text in [summary] + key_facts:
            match = re.search(
                r"(?:monthly\s+surplus|net cash flow)[^\d$+\-]{0,24}[+]?\$?(\d{1,3}(?:,\d{3})+|\d{3,})",
                text,
                flags=re.IGNORECASE,
            )
            if match:
                try:
                    surplus_value = float(match.group(1).replace(",", ""))
                except ValueError:
                    surplus_value = 0.0
                break

        if surplus_value > 0:
            low = max(100.0, round((surplus_value * 0.25) / 50.0) * 50.0)
            high = max(low + 100.0, round((surplus_value * 0.40) / 50.0) * 50.0)
            actions.insert(0, f"Put ${low:,.0f}-${high:,.0f} per month toward debt while maintaining a cash buffer")
        if (
            not negative_cashflow
            and not any(re.search(r"\b\d+\s*-\s*\d+\s*months\b|\b\d+\s+months\b", item, flags=re.IGNORECASE) for item in actions)
        ):
            actions.append("Build an emergency fund to cover 3-6 months of expenses")

    lines: List[str] = []
    if summary:
        lines.append("Summary:")
        lines.append(capitalize_first(summary))
        lines.append("")
    if key_facts:
        lines.append("Key Facts:")
        for fact in key_facts:
            lines.append(f"- {capitalize_first(fact)}")
        lines.append("")
    if meaning:
        lines.append("What this means:")
        lines.append(capitalize_first(meaning))
        lines.append("")
    if actions:
        lines.append("What to do first:")
        for action in actions:
            lines.append(f"- {capitalize_first(action)}")
        lines.append("")
    if warnings:
        lines.append("Warnings:")
        for warning in warnings:
            lines.append(f"- {capitalize_first(warning)}")
        lines.append("")
    if include_followup:
        global _LAST_FOLLOWUP
        cleaned_followup = clean_text_block(followup)
        if not cleaned_followup or cleaned_followup.lower() == _LAST_FOLLOWUP.lower():
            cleaned_followup = next_followup()
        _LAST_FOLLOWUP = cleaned_followup
        lines.append(capitalize_first(cleaned_followup))

    return enforce_currency_consistency("\n".join(lines).strip())


def format_structured_markdown(text: str) -> str:
    if not text:
        return ""
    text = re.sub(
        r"(?m)^(Summary|Key Facts|What this means|What to do first|Actions|Warnings):",
        r"**\1:**",
        text,
    )
    text = re.sub(
        r"(?m)\n(?=\*\*(Summary|Key Facts|What this means|What to do first|Actions|Warnings):\*\*)",
        "\n\n",
        text,
    )
    return text.strip()


def build_nemotron_prompt(mode: str, context: Dict[str, Any]) -> str:
    data_blob = json.dumps(context, indent=2)
    return f"""
You are RiseArc, a financial assistant powered by Nemotron.
Your job is to explain the user's finances clearly and helpfully based only on the provided data.
Do NOT calculate new numbers. Use the formatted numbers exactly as provided.
Do NOT invent missing values. If you need clarification, ask a follow-up question.
Do NOT provide investment advice or stock recommendations.
Do NOT mention investing, investments, stocks, ETFs, crypto, portfolios, mutual funds, or bonds.
Keep the tone supportive and practical, never alarmist or discouraging.

Return ONLY valid JSON with the following schema:
{{
  "summary": "1-2 sentences",
  "key_facts": ["short bullet", "..."],
  "meaning": "1-3 sentences interpreting the facts",
  "actions": ["prioritized action", "..."],
  "warnings": ["short warning", "..."],
  "followup": "one short clarifying question"
}}

Rules:
- Use only the values in DATA.
- If MODE is "scenario", base your Summary/Meaning on the scenario metrics and do not claim current cash flow is negative unless the scenario shows that.
- If MODE is "chat" and scenario metrics are present, clearly distinguish current vs scenario numbers.
- If cash flow is positive, do not claim a negative cash flow.
- If MODE is "scenario" or "overview", set "followup" to an empty string.
- Use "You" to address the reader. Do not say "the user".
- Prefix all money amounts with "$".
- When stating net cash flow, use a compact label like "Net cash flow: +$1,800/mo" or "-$3,400/mo".
- In scenario mode, use the exact net cash flow value from DATA and do not invent a different monthly burn/cash-flow number.
- Keep "meaning" conversational. Start with "In simple terms:" only if the user explicitly asked for simple wording.
- Avoid wording like "job stability in tech"; prefer "stable job in the tech industry".
- In "actions", include at least one concrete numeric target (dollars per month or months of expenses) when data allows.
- Keep recommendations focused on controllable steps in budgeting, debt management, income stability, and emergency reserves.
- When risk is high, pair each warning with a clear next step.
- If net cash flow is negative, prioritize actions in this order: cut expenses, secure income, then debt optimization.
- Do not suggest "prioritize emergency savings" as the first action when income is already gone and cash flow is negative.
- If runway is "Not constrained", say savings are growing.
- Avoid placeholders like $income, $debt, or 'debt ratio is Debt'.
- Do not repeat the same sentence in multiple sections.
- Use plain language.

MODE: {mode}
DATA:
{data_blob}
""".strip()


def build_nemotron_context(
    profile: Dict[str, Any],
    metrics: Dict[str, float],
    scenario: Dict[str, Any] | None = None,
    scenario_metrics: Dict[str, float] | None = None,
    timeline_stats: Dict[str, float] | None = None,
    question: str | None = None,
    mode: str = "chat",
) -> Dict[str, Any]:
    income = float(profile.get("income_monthly", 0.0))
    living_expenses = float(profile.get("expenses_monthly", 0.0))
    baseline_debt_payment = profile_monthly_debt_payment(profile)
    expenses = living_expenses + baseline_debt_payment
    savings = float(profile.get("savings", 0.0))
    debt = float(profile.get("debt", 0.0))
    monthly_net = income - expenses
    metrics = sanitize_metrics(metrics)
    debt_ratio = float(metrics.get("debt_ratio", 0.0))
    risk_score = float(metrics.get("risk_score", 0.0))
    current_runway = "Not constrained (cash flow positive)"
    if monthly_net < 0:
        current_runway = format_months(metrics.get("runway_months", 0.0))

    current_metrics = {
        "monthly_net": format_money_signed(monthly_net),
        "cash_flow_label": "surplus" if monthly_net >= 0 else "deficit",
        "debt_ratio": f"{format_ratio(debt_ratio)} ({debt_ratio * 100:.0f}% of annual income)",
        "risk_score": f"{risk_score:.0f}/100",
    }
    if monthly_net < 0:
        current_metrics["runway"] = current_runway

    context: Dict[str, Any] = {
        "mode": mode,
        "question": question or "",
        "profile": {
            "monthly_income": format_currency(income),
            "monthly_expenses": format_currency(expenses),
            "monthly_living_expenses": format_currency(living_expenses),
            "debt_payment_monthly": format_currency(baseline_debt_payment),
            "savings": format_currency(savings),
            "debt": format_currency(debt),
            "industry": profile.get("industry", "Other"),
            "job_stability": profile.get("job_stability", "medium"),
            "dependents": int(profile.get("dependents", 0)),
        },
    }
    if mode != "scenario":
        context["current_metrics"] = current_metrics

    if scenario is not None:
        scenario_values = sanitize_metrics(scenario_metrics or metrics)
        scenario_net_burn = float(scenario_values.get("monthly_net_burn", 0.0))
        scenario_net_cash_flow = -scenario_net_burn
        scenario_runway = "Not constrained (cash flow positive)"
        if scenario_net_burn > 0:
            scenario_runway = format_months(scenario_values.get("runway_months", 0.0))
        scenario_payload = {
            "monthly_support": format_currency(float(scenario_values.get("monthly_support", 0.0))),
            "monthly_expenses_after_cut": format_currency(float(scenario_values.get("monthly_expenses_cut", 0.0))),
            "net_monthly_burn": f"{format_currency(abs(scenario_net_burn))}/mo",
            "net_cash_flow": f"{format_money_signed(scenario_net_cash_flow)}/mo",
            "risk_score": f"{float(scenario_values.get('risk_score', 0.0)):.0f}/100",
            "debt_ratio": f"{format_ratio(float(scenario_values.get('debt_ratio', 0.0)))} ({float(scenario_values.get('debt_ratio', 0.0)) * 100:.0f}% of annual income)",
        }
        if mode != "chat":
            scenario_payload.update(
                {
                    "months_unemployed": int(scenario.get("months_unemployed", 0)),
                    "expense_cut_pct": format_pct(float(scenario.get("expense_cut_pct", 0.0))),
                    "severance": format_currency(float(scenario.get("severance", 0.0))),
                }
            )
        if scenario_net_burn > 0:
            scenario_payload["scenario_runway"] = scenario_runway
        context["scenario"] = scenario_payload

    if timeline_stats:
        context["timeline"] = {
            "months_until_zero": format_months(float(timeline_stats.get("months_until_zero", 0.0))),
            "max_drawdown": format_currency(float(timeline_stats.get("max_drawdown", 0.0))),
            "trend_slope": format_currency(float(timeline_stats.get("trend_slope", 0.0))),
        }

    return context


def format_chat_history_snippet(chat_history: List[Dict[str, str]], max_messages: int = 8) -> str:
    if not chat_history:
        return ""
    recent = chat_history[-max_messages:]
    lines: List[str] = []
    for msg in recent:
        role = "User" if msg.get("role") == "user" else "Assistant"
        content = str(msg.get("content", "")).strip()
        if not content:
            continue
        lines.append(f"{role}: {content}")
    return "\n".join(lines).strip()


def nemotron_generate_conversational(
    profile: Dict[str, Any],
    metrics: Dict[str, float],
    question: str,
    chat_history: List[Dict[str, str]],
    scenario: Dict[str, Any] | None = None,
    scenario_metrics: Dict[str, float] | None = None,
) -> str:
    if not query_nemotron or not extract_text:
        return "Nemotron is unavailable right now. Please start the server and try again."

    metrics = sanitize_metrics(metrics)
    if scenario_metrics:
        scenario_metrics = sanitize_metrics(scenario_metrics)

    context = build_nemotron_context(
        profile=profile,
        metrics=metrics,
        scenario=scenario,
        scenario_metrics=scenario_metrics,
        timeline_stats=None,
        question=question,
        mode="chat",
    )
    history_snippet = format_chat_history_snippet(chat_history)
    context_blob = json.dumps(context, indent=2)

    prompt = f"""
You are RiseArc, a financial assistant. Respond naturally in conversation.

Rules:
- Answer the user's exact question first. If they asked for clarification, clarify the specific prior point.
- Do not use fixed report sections like Summary/Key Facts unless the user explicitly asks for a structured report.
- Keep the response concise and human (about 2-6 sentences).
- If the user asks what to do next, give a prioritized 2-4 step plan with at least one concrete numeric target when data allows.
- Use only the values in CONTEXT when citing numbers.
- Prefix money amounts with "$".
- If the user says "yes" without details after your follow-up question, ask one short clarifying question.
- Keep tone supportive and solution-focused.
- Do not provide investment advice.
- Do not mention investing, investments, stocks, ETFs, crypto, portfolios, mutual funds, or bonds.

RECENT CONVERSATION:
{history_snippet or "(none)"}

CONTEXT:
{context_blob}

USER QUESTION:
{question}
""".strip()

    try:
        raw = extract_text(query_nemotron(prompt, max_tokens=420, temperature=0.35)).strip()
        record_nemotron_status(True)
    except Exception as exc:
        record_nemotron_status(False)
        return format_nemotron_error(str(exc), "chat response")

    if not raw:
        return "Can you clarify what you want me to explain first: cash flow, runway, or risk?"
    cleaned = enforce_readability_guardrail(
        clean_text_block(raw),
        fallback="I can clarify that more cleanly. Do you want me to focus on cash flow, runway, or risk first?",
    )
    if has_corrupted_spacing(cleaned):
        return "I can clarify that more cleanly. Do you want me to focus on cash flow, runway, or risk first?"
    return cleaned


def nemotron_generate_structured(
    mode: str,
    profile: Dict[str, Any],
    metrics: Dict[str, float],
    scenario: Dict[str, Any] | None = None,
    scenario_metrics: Dict[str, float] | None = None,
    timeline_stats: Dict[str, float] | None = None,
    question: str | None = None,
    include_followup: bool = True,
) -> str:
    def finalize_output(text: str, fallback: str = "") -> str:
        return enforce_readability_guardrail(text or "", fallback=fallback)

    simple_terms_requested = user_requested_simple_terms(question or "")

    if not query_nemotron or not extract_text:
        return finalize_output("Nemotron is unavailable right now. Please start the server and try again.")

    metrics = sanitize_metrics(metrics)
    if scenario_metrics:
        scenario_metrics = sanitize_metrics(scenario_metrics)

    def deterministic_fallback() -> str:
        if mode == "scenario" and scenario is not None:
            return build_scenario_fallback_summary(profile, scenario, scenario_metrics or metrics)
        if mode == "overview":
            monthly_net = float(profile.get("income_monthly", 0.0)) - profile_total_monthly_expenses(profile)
            runway_months = float(metrics.get("runway_months", 0.0))
            return build_baseline_fallback_summary(profile, monthly_net, runway_months, metrics)

        context = build_nemotron_context(
            profile=profile,
            metrics=metrics,
            scenario=scenario,
            scenario_metrics=scenario_metrics,
            timeline_stats=timeline_stats,
            question=question,
            mode=mode,
        )
        current = context.get("current_metrics", {})
        scenario_ctx = context.get("scenario", {})
        summary = ""
        if scenario_ctx:
            summary = (
                f"Under this scenario, net burn is {scenario_ctx.get('net_monthly_burn', '')} "
                f"and runway is {scenario_ctx.get('scenario_runway', '')}."
            )
        else:
            summary = (
                f"Your current cash flow is {current.get('monthly_net', '')} "
                f"with a debt ratio of {current.get('debt_ratio', '')}."
            )

        key_facts = [
            f"Monthly income: {context['profile']['monthly_income']}",
            f"Monthly expenses: {context['profile']['monthly_expenses']}",
            f"Savings: {context['profile']['savings']}",
            f"Debt: {context['profile']['debt']}",
            f"Risk score: {current.get('risk_score', '')}",
        ]
        meaning = (
            "This means you have a clear view of your cash flow and risk posture, "
            "so you can focus on stabilizing income and protecting savings."
        )
        actions = [
            "Stabilize income first by identifying short-term or backup sources.",
            "Reduce discretionary expenses to slow the monthly burn.",
            "Build or protect an emergency buffer to improve flexibility.",
        ]
        warnings = [
            "If income drops, your runway will shrink quickly at the current burn.",
            "High debt can become harder to manage if cash flow weakens.",
        ]
        return render_structured_response(
            {
                "summary": summary,
                "key_facts": key_facts,
                "meaning": meaning,
                "actions": actions,
                "warnings": warnings, 
                "followup": "Do you want me to adjust any assumptions?" if include_followup else "",
            },
            include_followup=include_followup,
            force_simple_terms=simple_terms_requested,
        )

    context = build_nemotron_context(
        profile=profile,
        metrics=metrics,
        scenario=scenario,
        scenario_metrics=scenario_metrics,
        timeline_stats=timeline_stats,
        question=question,
        mode=mode,
    )
    prompt = build_nemotron_prompt(mode, context)
    try:
        raw = extract_text(query_nemotron(prompt))
        record_nemotron_status(True)
    except Exception as exc:
        record_nemotron_status(False)
        fallback = deterministic_fallback()
        if fallback:
            return finalize_output(fallback, fallback=fallback)
        return finalize_output(format_nemotron_error(str(exc), mode))

    parsed = parse_json_response(raw)
    if not parsed or not any(
        [
            parsed.get("summary"),
            parsed.get("key_facts"),
            parsed.get("meaning"),
            parsed.get("actions"),
            parsed.get("warnings"),
        ]
    ):
        fallback = deterministic_fallback()
        return finalize_output(fallback, fallback=fallback)

    parsed = apply_structured_guardrails(parsed, mode, profile, scenario_metrics or metrics, scenario)
    text = render_structured_response(
        parsed,
        include_followup=include_followup,
        force_simple_terms=simple_terms_requested,
    )
    if not text or has_placeholder_artifacts(text) or has_corrupted_spacing(text):
        fallback = deterministic_fallback()
        return finalize_output(fallback, fallback=fallback)
    fallback = deterministic_fallback()
    return finalize_output(text, fallback=fallback)


def format_readable_text(text: str) -> str:
    if not text:
        return ""
    if "\n" in text:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    if len(sentences) <= 2:
        return text
    return "\n".join(sentences)


def render_plain_chat_text(text: str) -> str:
    safe = html.escape(str(text or ""))
    safe = safe.replace("\n", "<br>")
    return f"<div class='chat-plain-text'>{safe}</div>"


def get_nemotron_status() -> bool:
    last_ok = st.session_state.get("nemotron_last_ok")
    last_checked = st.session_state.get("nemotron_last_checked", 0.0)
    if last_ok is not None and time.time() - last_checked < 60:
        return bool(last_ok)
    if not check_nemotron_online:
        return False
    try:
        status = bool(check_nemotron_online())
        st.session_state.nemotron_last_ok = status
        st.session_state.nemotron_last_checked = time.time()
        return status
    except Exception:
        return False


def record_nemotron_status(is_online: bool) -> None:
    st.session_state.nemotron_last_ok = bool(is_online)
    st.session_state.nemotron_last_checked = time.time()


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

    def _amount_to_float(value: str) -> float:
        return float(value.replace(",", ""))

    def _linked_amount(keyword_pattern: str) -> float | None:
        # Keep extraction tightly bound to the keyword to avoid cross-sentence leaks
        # like "no severance ... savings are $12,000" being read as severance.
        match = re.search(
            rf"\b(?:{keyword_pattern})\b(?:\s*(?:is|are|was|were|=|:|of|about|around|at|for|totals?|equals?)\s*){{0,2}}\s*\$?([\d,]+(?:\.\d+)?)\b",
            lowered,
        )
        if not match:
            return None
        return _amount_to_float(match.group(1))

    def _linked_monthly_amount(keyword_pattern: str) -> float | None:
        match = re.search(
            rf"\b(?:{keyword_pattern})\b(?:\s*(?:is|are|was|were|=|:|of|about|around|at|for|totals?|equals?)\s*){{0,3}}"
            rf"\s*\$?([\d,]+(?:\.\d+)?)\s*(?:/|per)?\s*(?:month|mo)\b",
            lowered,
        )
        if not match:
            match = re.search(
                rf"\$?([\d,]+(?:\.\d+)?)\s*(?:/|per)?\s*(?:month|mo)\b[^\n]{{0,24}}?\b(?:{keyword_pattern})\b",
                lowered,
            )
        if not match:
            return None
        return _amount_to_float(match.group(1))

    job_loss_context = r"(?:unemployed|jobless|without\s+(?:a\s+)?job|lose\s+(?:my\s+)?job|laid\s+off|layoff|out\s+of\s+work)"
    months_match = re.search(
        rf"{job_loss_context}[^\n]{{0,50}}?(\d+(?:\.\d+)?)\s*(?:months?|mos|mo)\b",
        lowered,
    )
    if not months_match:
        months_match = re.search(
            rf"(\d+(?:\.\d+)?)\s*(?:months?|mos|mo)\b[^\n]{{0,50}}?{job_loss_context}",
            lowered,
        )
    if months_match:
        data["months_unemployed"] = int(float(months_match.group(1)))

    percent_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:%|percent\b).*(expense|cut|reduce|lower)", lowered)
    if not percent_match:
        percent_match = re.search(
            r"(?:cut|reduce|lower)\s+(?:my\s+)?(?:expenses?|spending|costs?)\s*(?:by\s*)?(\d+(?:\.\d+)?)\s*(?:%|percent\b)",
            lowered,
        )
    if percent_match:
        data["expense_cut_pct"] = float(percent_match.group(1))

    expense_increase_match = re.search(
        r"(?:expenses?|costs?|spend(?:ing)?)\s*(?:rise|increase|go up|went up|up)\s*(?:by\s*)?(\d+(?:\.\d+)?)\s*(?:%|percent\b)",
        lowered,
    )
    if expense_increase_match:
        data["expense_increase_pct"] = float(expense_increase_match.group(1))
    else:
        inflation_match = re.search(
            r"(\d+(?:\.\d+)?)\s*(?:%|percent\b)\s*(?:inflation|cost increase|expense increase|price increase)",
            lowered,
        )
        if inflation_match:
            data["expense_increase_pct"] = float(inflation_match.group(1))

    severance_amount = _linked_amount(r"severance|payout")
    if severance_amount is not None:
        data["severance"] = severance_amount
    elif re.search(r"\b(?:without|no)\s+severance\b", lowered):
        data["severance"] = 0.0

    benefit_amount = _linked_amount(r"unemployment(?:\s+benefits?)?|benefits?")
    if benefit_amount is not None:
        data["unemployment_benefit_monthly"] = benefit_amount
    elif re.search(r"\b(?:without|no)\s+(?:unemployment|benefits?)\b", lowered):
        data["unemployment_benefit_monthly"] = 0.0

    other_income_amount = _linked_amount(r"side income|freelance|other income")
    if other_income_amount is not None:
        data["other_income_monthly"] = other_income_amount

    debt_payment_amount = _linked_monthly_amount(
        r"debt payments?|loan payments?|credit card payments?|min(?:imum)? payments?|debt paydown"
    )
    if debt_payment_amount is not None:
        data["debt_payment_monthly"] = debt_payment_amount

    healthcare_amount = _linked_monthly_amount(r"healthcare|insurance|medical(?: costs?| bills?)?")
    if healthcare_amount is not None:
        data["healthcare_monthly"] = healthcare_amount

    dependent_care_amount = _linked_monthly_amount(r"dependent care|childcare|daycare")
    if dependent_care_amount is not None:
        data["dependent_care_monthly"] = dependent_care_amount

    job_search_amount = _linked_monthly_amount(r"job search|reskilling|training|course|certification")
    if job_search_amount is not None:
        data["job_search_monthly"] = job_search_amount

    extra_monthly_amount = _linked_monthly_amount(
        r"extra monthly(?: expenses?| costs?)?|other monthly(?: expenses?| costs?)?|additional monthly(?: expenses?| costs?)?|misc(?:ellaneous)?(?: monthly)?(?: expenses?| costs?)?"
    )
    if extra_monthly_amount is not None:
        data["extra_monthly_expenses"] = extra_monthly_amount

    windfall_amount = _linked_amount(r"lottery|windfall|bonus|inheritance|settlement|award|prize|jackpot")
    if windfall_amount is not None:
        data["one_time_income"] = windfall_amount

    explicit_one_time_expense = _linked_amount(r"one[-\s]?time expense|one[-\s]?time cost|unexpected expense")
    if explicit_one_time_expense is not None:
        data["one_time_expense"] = explicit_one_time_expense

    start_income_match = re.search(
        r"(?:starting|from|beginning|starts?)\s+(?:in\s+)?month\s+(\d+)(?:[^\n]{0,80}?)\$?([\d,]+)\s*(?:/|per)?\s*(?:month|mo)\b",
        lowered,
    )
    if not start_income_match:
        start_income_match = re.search(
            r"after\s+(\d+)\s+months?(?:[^\n]{0,80}?)\$?([\d,]+)\s*(?:/|per)?\s*(?:month|mo)\b",
            lowered,
        )
    if start_income_match:
        data["income_start_month"] = int(float(start_income_match.group(1)))
        data["income_start_amount"] = _amount_to_float(start_income_match.group(2))
    else:
        month_any_match = re.search(r"\bmonth\s+(\d+)\b", lowered)
        income_month_match = re.search(r"\$?([\d,]+)\s*(?:/|per)?\s*(?:month|mo)\b", lowered)
        if month_any_match and income_month_match and re.search(r"(contract|income|new job|new income|job|work|gig|freelance|side income)", lowered):
            data["income_start_month"] = int(float(month_any_match.group(1)))
            data["income_start_amount"] = _amount_to_float(income_month_match.group(1))

    raise_match = re.search(
        r"(raise|promotion|salary increase|pay increase|pay bump)[^\d]*\$?([\d,]+)(?:\s*(per|/)?\s*(year|yr|annual|month|mo))?",
        lowered,
    )
    if raise_match:
        amount = _amount_to_float(raise_match.group(2))
        period = (raise_match.group(4) or "").strip()
        if period in {"year", "yr", "annual"}:
            amount = amount / 12.0
        data["income_change_monthly"] = amount

    cut_match = re.search(
        r"(pay cut|salary cut|income cut|pay reduction|salary reduction)[^\d]*\$?([\d,]+)(?:\s*(per|/)?\s*(year|yr|annual|month|mo))?",
        lowered,
    )
    if cut_match:
        amount = _amount_to_float(cut_match.group(2))
        period = (cut_match.group(4) or "").strip()
        if period in {"year", "yr", "annual"}:
            amount = amount / 12.0
        data["income_change_monthly"] = -amount

    theft_amount = _linked_amount(r"robbed|stolen|theft|scammed|fraud")
    if theft_amount is not None:
        data["one_time_expense"] = theft_amount

    relocation_amount = _linked_amount(r"relocation(?: cost)?|moving(?: cost)?|legal(?: fees?| cost)")
    if relocation_amount is not None:
        data["relocation_cost"] = relocation_amount

    savings_amount = _linked_amount(r"savings|saved|cash on hand|cash")
    if savings_amount is not None:
        data["override_savings"] = savings_amount

    debt_amount = _linked_amount(r"debt|owe|loan|credit card|balance")
    if debt_amount is not None:
        data["override_debt"] = debt_amount

    income_match = re.search(
        r"\b(?:income|salary)\s*(?:is|=|:|of)?\s*\$?([\d,]+)\s*(?:/|per)?\s*(?:month|mo)\b",
        lowered,
    )
    if not income_match:
        income_match = re.search(r"\b(?:i\s+)?earn(?:ing)?\s*\$?([\d,]+)\s*(?:/|per)?\s*(?:month|mo)\b", lowered)
    if income_match:
        prefix = lowered[max(0, income_match.start() - 64):income_match.start()]
        nearby = lowered[max(0, income_match.start() - 48):min(len(lowered), income_match.end() + 48)]
        scenario_income_context = re.search(
            r"(side income|other income|additional income|extra income|contract income|freelance income|unemployment benefits?)",
            nearby,
        )
        if (
            not scenario_income_context
            and not re.search(
                r"(?:start(?:ing|s)?|begin(?:ning)?|after|month\s+\d+|cut|reduction|decrease|drop|raise|increase)",
                prefix,
            )
        ):
            data["override_income_monthly"] = _amount_to_float(income_match.group(1))

    expense_match = re.search(r"(expenses?|spend|spending|costs?)\s*[^\d]*\$?([\d,]+)\s*(?:/|per)?\s*(?:month|mo)", lowered)
    if expense_match:
        nearby = lowered[max(0, expense_match.start() - 48):min(len(lowered), expense_match.end() + 48)]
        scenario_expense_context = re.search(
            r"(extra monthly|other monthly|additional (?:monthly )?(?:expenses?|costs?)|expense increase|cost increase|inflation)",
            nearby,
        )
        if not scenario_expense_context:
            data["override_expenses_monthly"] = _amount_to_float(expense_match.group(2))

    return data


def extract_scenario_from_text(user_text: str, use_model: bool = False) -> Dict[str, Any]:
    if not user_text or not user_text.strip():
        return {}
    if not use_model or not query_nemotron or not extract_text:
        return regex_extract_scenario(user_text)

    schema = {
        "months_unemployed": "int (0-36)",
        "expense_cut_pct": "float (0-70)",
        "expense_increase_pct": "float (0-200)",
        "severance": "float",
        "unemployment_benefit_monthly": "float",
        "other_income_monthly": "float",
        "income_start_month": "int (0-60)",
        "income_start_amount": "float (monthly)",
        "income_change_monthly": "float (can be negative)",
        "extra_monthly_expenses": "float",
        "debt_payment_monthly": "float",
        "healthcare_monthly": "float",
        "dependent_care_monthly": "float",
        "job_search_monthly": "float",
        "one_time_expense": "float",
        "one_time_income": "float",
        "relocation_cost": "float",
        "override_savings": "float",
        "override_debt": "float",
        "override_income_monthly": "float",
        "override_expenses_monthly": "float",
    }

    prompt = f"""
You extract scenario details from user text for a financial simulator.
Return ONLY a JSON object. Do not include any extra text.
If a field is unknown, omit it.
Schema: {json.dumps(schema)}

User request: {user_text}
""".strip()

    try:
        raw = extract_text(query_nemotron(prompt, max_tokens=420, temperature=0.15))
        record_nemotron_status(True)
    except Exception:
        record_nemotron_status(False)
        return regex_extract_scenario(user_text)

    parsed = safe_json_from_text(raw)
    if not parsed:
        return regex_extract_scenario(user_text)
    fallback = regex_extract_scenario(user_text)
    for key, value in fallback.items():
        if key not in parsed:
            parsed[key] = value

    def _field_has_evidence(field: str, text: str) -> bool:
        lowered = text.lower()
        evidence_patterns = {
            "months_unemployed": r"(unemployed|jobless|lose\s+(?:my\s+)?job|laid\s+off|layoff|without\s+(?:a\s+)?job|out\s+of\s+work)",
            "expense_cut_pct": r"((cut|reduce|lower).*(expense|spend|cost)|(expense|spend|cost).*(cut|reduce|lower))",
            "expense_increase_pct": r"((expense|cost|spend).*(increase|rise|inflation|go\s+up)|inflation)",
            "severance": r"(severance|payout)",
            "unemployment_benefit_monthly": r"(unemployment|benefit)",
            "other_income_monthly": r"(side income|other income|freelance|gig|part[-\s]?time|contract income)",
            "income_start_month": r"((starting|starts?|from|beginning|after).*(month)|month\s+\d+.*(income|contract|job|work|gig|freelance))",
            "income_start_amount": r"((starting|starts?|from|beginning|after).*(month)|month\s+\d+.*(income|contract|job|work|gig|freelance))",
            "income_change_monthly": r"(raise|promotion|salary increase|pay increase|pay bump|pay cut|salary cut|income cut|reduction)",
            "extra_monthly_expenses": r"(extra monthly|other monthly|additional (?:monthly )?(?:expenses?|costs?)|misc(?:ellaneous)? (?:expenses?|costs?))",
            "debt_payment_monthly": r"(debt payment|loan payment|credit card payment|min(?:imum)? payment|pay(?:ing)? down debt)",
            "healthcare_monthly": r"(healthcare|insurance|medical)",
            "dependent_care_monthly": r"(dependent care|childcare|daycare)",
            "job_search_monthly": r"(job search|reskilling|training|course|certification)",
            "one_time_expense": r"(one[-\s]?time expense|one[-\s]?time cost|unexpected expense|robbed|stolen|theft|scammed|fraud)",
            "one_time_income": r"(one[-\s]?time income|windfall|bonus|inheritance|settlement|award|prize|jackpot)",
            "relocation_cost": r"(relocation|moving|legal)",
            "override_savings": r"(savings|saved|cash on hand|cash)",
            "override_debt": r"(debt|owe|loan|credit card|balance)",
            "override_income_monthly": r"(income|salary|earn)",
            "override_expenses_monthly": r"(expenses?|spend|spending|costs?)",
        }
        pattern = evidence_patterns.get(field)
        return bool(re.search(pattern, lowered)) if pattern else True

    # Keep regex-backed fields authoritative. For model-only fields, require evidence
    # in user text to avoid hallucinated monthly values (e.g., debt amount becoming debt payment).
    for key in list(parsed.keys()):
        if key in fallback:
            continue
        if not _field_has_evidence(key, user_text):
            parsed.pop(key, None)
    # If the user gave an inflation/expense-increase percent, prefer deriving the
    # monthly dollar add-on from profile expenses unless they explicitly stated a
    # separate extra-monthly-dollar amount.
    if (
        "expense_increase_pct" in parsed
        and "extra_monthly_expenses" in parsed
        and "extra_monthly_expenses" not in fallback
        and not re.search(
            r"(extra monthly|other monthly|additional (?:monthly )?(?:expenses?|costs?)|misc(?:ellaneous)? (?:expenses?|costs?))",
            user_text,
            flags=re.IGNORECASE,
        )
    ):
        parsed.pop("extra_monthly_expenses", None)
    # Guard against model "helpfully" inserting zero overrides that wipe the real profile
    # unless the user text explicitly included those numbers (regex fallback captures that).
    override_keys = {
        "override_savings",
        "override_debt",
        "override_income_monthly",
        "override_expenses_monthly",
    }
    for key in list(override_keys):
        if key in parsed and key not in fallback:
            try:
                value = float(parsed[key])
            except (TypeError, ValueError):
                continue
            if abs(value) < 1e-6:
                parsed.pop(key, None)
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
        "expense_increase_pct": (0.0, 200.0),
        "severance": (0.0, 200000.0),
        "unemployment_benefit_monthly": (0.0, 50000.0),
        "other_income_monthly": (0.0, 50000.0),
        "income_start_month": (0.0, 60.0),
        "income_start_amount": (0.0, 50000.0),
        "income_change_monthly": (-50000.0, 50000.0),
        "extra_monthly_expenses": (0.0, 50000.0),
        "debt_payment_monthly": (0.0, 50000.0),
        "healthcare_monthly": (0.0, 50000.0),
        "dependent_care_monthly": (0.0, 50000.0),
        "job_search_monthly": (0.0, 50000.0),
        "one_time_expense": (0.0, 500000.0),
        "one_time_income": (0.0, 500000.0),
        "relocation_cost": (0.0, 500000.0),
        "override_savings": (0.0, 2000000.0),
        "override_debt": (0.0, 2000000.0),
        "override_income_monthly": (0.0, 200000.0),
        "override_expenses_monthly": (0.0, 200000.0),
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
        "income_start_month": "income_start_month",
        "income_start_amount": "income_start_amount",
        "income_change_monthly": "income_change_monthly",
        "extra_monthly_expenses": "extra_monthly_expenses",
        "debt_payment_monthly": "debt_payment_monthly",
        "healthcare_monthly": "healthcare_monthly",
        "dependent_care_monthly": "dependent_care_monthly",
        "job_search_monthly": "job_search_monthly",
        "one_time_expense": "one_time_expense",
        "one_time_income": "one_time_income",
        "relocation_cost": "relocation_cost",
    }
    for key, state_key in state_map.items():
        if key in applied:
            st.session_state[state_key] = applied[key]

    if "expense_increase_pct" in applied and "extra_monthly_expenses" not in applied:
        profile = st.session_state.get("profile") or {}
        base_expenses = float(profile.get("expenses_monthly", 0.0))
        derived_extra = clamp_value(base_expenses * (float(applied["expense_increase_pct"]) / 100.0), 0.0, 50000.0)
        st.session_state["extra_monthly_expenses"] = derived_extra
        applied["extra_monthly_expenses"] = derived_extra

    overrides = {
        key: value
        for key, value in applied.items()
        if key in {
            "override_savings",
            "override_debt",
            "override_income_monthly",
            "override_expenses_monthly",
        }
    }
    if overrides:
        st.session_state.scenario_overrides = overrides
    else:
        st.session_state.scenario_overrides = {}

    return applied


def profile_signature(profile: Dict[str, Any]) -> str:
    try:
        return json.dumps({"profile": profile, "baseline_version": BASELINE_SUMMARY_VERSION}, sort_keys=True)
    except Exception:
        return str(profile)


def generate_baseline_summary(
    profile: Dict[str, Any],
    monthly_net: float,
    runway_months: float,
) -> str:
    if not query_nemotron or not extract_text:
        return "Nemotron is unavailable right now. Please start the server and try again."

    baseline_scenario = {
        "months_unemployed": 0,
        "expense_cut_pct": 0.0,
        "severance": 0.0,
        "unemployment_benefit_monthly": 0.0,
        "other_income_monthly": 0.0,
        "income_change_monthly": 0.0,
        "extra_monthly_expenses": 0.0,
        "debt_payment_monthly": 0.0,
        "healthcare_monthly": 0.0,
        "dependent_care_monthly": 0.0,
        "job_search_monthly": 0.0,
        "one_time_expense": 0.0,
        "one_time_income": 0.0,
        "relocation_cost": 0.0,
        "baseline_mode": True,
    }
    baseline_payload = {
        "profile": profile,
        "scenario": baseline_scenario,
        "subscriptions": [],
        "news_event": None,
        "scenario_note": "",
    }

    try:
        result = local_analysis(baseline_payload)
        summary = result.get("summary", "")
        record_nemotron_status(True)
        if not summary.strip():
            return "Nemotron returned an empty summary. Please try again."
        return enforce_readability_guardrail(summary)
    except Exception as exc:
        record_nemotron_status(False)
        return format_nemotron_error(str(exc), "financial overview")


def ensure_baseline_summary(
    profile: Dict[str, Any],
    monthly_net: float,
    runway_months: float,
    show_spinner: bool = False,
) -> str:
    debt_ratio = compute_debt_ratio(float(profile.get("debt", 0.0)), float(profile.get("income_monthly", 0.0))) if compute_debt_ratio else 0.0
    risk_score = (
        compute_risk_score(runway_months, debt_ratio, profile.get("job_stability", "stable"), profile.get("industry", "Other"))
        if compute_risk_score
        else 0.0
    )
    baseline_fallback = build_baseline_fallback_summary(
        profile,
        monthly_net,
        runway_months,
        {"debt_ratio": debt_ratio, "risk_score": risk_score},
    )

    sig = profile_signature(profile)
    cached = st.session_state.get("baseline_summary")
    cached_sig = st.session_state.get("baseline_profile_sig")
    if cached and cached_sig == sig:
        normalized_cached = enforce_readability_guardrail(cached, fallback=baseline_fallback)
        if normalized_cached != cached:
            st.session_state.baseline_summary = normalized_cached
        return normalized_cached

    if show_spinner:
        with st.spinner("Generating your financial overview..."):
            summary = generate_baseline_summary(profile, monthly_net, runway_months)
    else:
        summary = generate_baseline_summary(profile, monthly_net, runway_months)

    if summary.startswith("[nemotron error]"):
        return format_nemotron_error(summary, "financial overview")

    summary = enforce_readability_guardrail(summary, fallback=baseline_fallback)
    st.session_state.baseline_summary = summary
    st.session_state.baseline_profile_sig = sig
    return summary


def local_analysis(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not all(
        [
            clamp,
            compute_debt_ratio,
            compute_risk_score,
            compute_runway,
            compute_timeline_stats,
            total_savings_leaks,
            query_nemotron,
            extract_text,
        ]
    ):
        raise RuntimeError("Local analysis is unavailable (missing core tool imports).")

    profile = payload["profile"]
    scenario = payload["scenario"]

    horizon = max(
        int(scenario.get("months_unemployed", 0)),
        1,
        int(scenario.get("income_start_month", 0) or 0),
        TIMELINE_HORIZON_MONTHS,
    )
    computed = compute_financials(
        profile,
        scenario,
        baseline_mode=bool(scenario.get("baseline_mode")),
        horizon_months=horizon,
    )
    metrics = computed["metrics"]
    timeline = computed["timeline"]
    baseline_monthly_net = float(profile.get("income_monthly", 0.0)) - profile_total_monthly_expenses(profile)
    baseline_runway = 60.0 if baseline_monthly_net >= 0 else compute_runway(
        float(profile.get("savings", 0.0)), abs(baseline_monthly_net), 0.0
    )
    debt_ratio = compute_debt_ratio(profile["debt"], profile["income_monthly"]) if compute_debt_ratio else 0.0
    baseline_risk = compute_risk_score(
        baseline_runway, debt_ratio, profile["job_stability"], profile["industry"]
    ) if compute_risk_score else 0.0

    adjusted_risk = metrics.get("risk_score", 0.0)
    alert = "No alerts yet."
    news_event = payload.get("news_event")
    if news_event:
        delta = news_event["risk_delta"]
        if news_event.get("industry") and news_event["industry"] != profile["industry"]:
            delta *= 0.5
        adjusted_risk = clamp(float(metrics.get("risk_score", 0.0)) + delta, 0.0, 100.0) if clamp else float(metrics.get("risk_score", 0.0)) + delta
        metrics["adjusted_risk_score"] = adjusted_risk
        alert = f"Headline: {news_event['headline']} | Risk adjusted by {delta:+.0f} to {adjusted_risk:.0f}."

    metrics["baseline_risk_score"] = baseline_risk
    savings_total = total_savings_leaks([s["monthly_cost"] for s in payload["subscriptions"]]) if total_savings_leaks else 0.0

    mode = "overview" if scenario.get("baseline_mode") else "scenario"
    summary = nemotron_generate_structured(
        mode=mode,
        profile=profile,
        metrics=metrics,
        scenario=None if scenario.get("baseline_mode") else scenario,
        scenario_metrics=metrics,
        timeline_stats=None,
        question=payload.get("scenario_note", ""),
        include_followup=False,
    )
    if mode == "overview":
        baseline_fallback = build_baseline_fallback_summary(
            profile,
            baseline_monthly_net,
            baseline_runway,
            {
                "debt_ratio": debt_ratio,
                "risk_score": baseline_risk,
            },
        )
        summary = enforce_readability_guardrail(summary, fallback=baseline_fallback)
    else:
        scenario_fallback = build_scenario_fallback_summary(profile, scenario, metrics)
        summary = enforce_readability_guardrail(summary, fallback=scenario_fallback)

    return {
        "metrics": metrics,
        "timeline": timeline,
        "timeline_stats": computed.get("timeline_stats", {}),
        "starting_balance": computed.get("starting_balance", 0.0),
        "savings_total": savings_total,
        "alert": alert,
        "summary": summary,
        "scenario": dict(scenario),
        "profile": dict(profile),
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
    profile = dict(SAMPLE_REQUEST.get("profile", {}))
    profile.setdefault("debt_payment_monthly", 0.0)
    st.session_state.profile = profile
    st.session_state.show_profile_dialog = False
    st.session_state.baseline_summary = None
    st.session_state.baseline_profile_sig = None
    st.session_state.baseline_notice_pending = True
    if SAMPLE_REQUEST.get("news_event"):
        st.session_state["news_event"] = "Tech layoff wave"
    for item in SAMPLE_REQUEST.get("subscriptions", []):
        key = f"sub_{item['name']}"
        st.session_state[key] = True


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown('<div class="sidebar-brand">RiseArc</div>', unsafe_allow_html=True)
        st.caption("Financial intelligence console")

        options = ["Introduction", "Scenario Builder", "Survival Timeline", "Chat"]
        st.markdown("Navigation")
        for option in options:
            is_active = st.session_state.active_view == option
            button_type = "primary" if is_active else "secondary"
            if st.button(option, use_container_width=True, type=button_type):
                st.session_state.active_view = option
                st.rerun()

        st.markdown("---")
        if st.button("Edit profile", use_container_width=True):
            st.session_state.show_profile_dialog = True
            st.rerun()

        if SAMPLE_REQUEST and st.button("Load demo profile", use_container_width=True):
            st.session_state.show_demo_dialog = True
            st.session_state.show_profile_dialog = False
            st.rerun()

        st.markdown("---")
        profile_ready = st.session_state.profile is not None
        profile_class = "ready" if profile_ready else ""
        profile_label = "Profile: Ready" if profile_ready else "Profile: Incomplete"
        st.markdown(
            f"""
            <div class="status-stack">
              <div class="status-pill {profile_class}">{profile_label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def init_state() -> None:
    if "profile" not in st.session_state:
        st.session_state.profile = None
    elif st.session_state.profile and "debt_payment_monthly" not in st.session_state.profile:
        st.session_state.profile = dict(st.session_state.profile)
        st.session_state.profile["debt_payment_monthly"] = 0.0
    if "show_profile_dialog" not in st.session_state:
        st.session_state.show_profile_dialog = True
    if "show_demo_dialog" not in st.session_state:
        st.session_state.show_demo_dialog = False
    if "active_view" not in st.session_state:
        st.session_state.active_view = "Introduction"
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if st.session_state.get("chat_history_currency_version") != CHAT_HISTORY_CURRENCY_VERSION:
        migrated: List[Dict[str, str]] = []
        changed = False
        for item in st.session_state.chat_history:
            role = str(item.get("role", ""))
            content = str(item.get("content", ""))
            if role == "assistant":
                normalized = enforce_readability_guardrail(content)
                if normalized != content:
                    changed = True
                migrated.append({"role": role, "content": normalized})
            else:
                migrated.append({"role": role, "content": content})
        if changed:
            st.session_state.chat_history = migrated
        st.session_state.chat_history_currency_version = CHAT_HISTORY_CURRENCY_VERSION
    if "quick_prompt_used" not in st.session_state:
        st.session_state.quick_prompt_used = False
    if "quick_prompt_text" not in st.session_state:
        st.session_state.quick_prompt_text = ""
    if "pending_prompt" not in st.session_state:
        st.session_state.pending_prompt = ""
    if "result" not in st.session_state:
        st.session_state.result = None
    if "nemotron_last_ok" not in st.session_state:
        st.session_state.nemotron_last_ok = None
    if "nemotron_last_checked" not in st.session_state:
        st.session_state.nemotron_last_checked = 0.0
    if "baseline_summary" not in st.session_state:
        st.session_state.baseline_summary = None
    if "baseline_profile_sig" not in st.session_state:
        st.session_state.baseline_profile_sig = None
    if "baseline_notice_pending" not in st.session_state:
        st.session_state.baseline_notice_pending = False
    if "last_build_id" not in st.session_state:
        st.session_state.last_build_id = None
    if "show_update_dialog" not in st.session_state:
        st.session_state.show_update_dialog = False


def maybe_show_update_dialog() -> None:
    try:
        build_id = int(Path(__file__).stat().st_mtime)
    except Exception:
        return
    last_build = st.session_state.get("last_build_id")
    if last_build is None:
        st.session_state.last_build_id = build_id
        return
    if build_id != last_build:
        st.session_state.last_build_id = build_id
        st.session_state.show_update_dialog = True
    if st.session_state.get("show_update_dialog"):
        st.markdown(
            """
            <div class="update-overlay">
              <div class="update-card">
                <div class="update-title">Update Available</div>
                <div class="update-text">A new update is ready. Click Update to reload the app.</div>
                <form method="get" action="" style="margin: 0;">
                  <button class="update-btn" type="submit">Update</button>
                </form>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.stop()
    if "scenario_overrides" not in st.session_state:
        st.session_state.scenario_overrides = {}
    if "months_unemployed" not in st.session_state:
        st.session_state.months_unemployed = 0
    if "expense_cut" not in st.session_state:
        st.session_state.expense_cut = 0.0
    if "severance" not in st.session_state:
        st.session_state.severance = 0.0
    if "unemployment_benefit_monthly" not in st.session_state:
        st.session_state.unemployment_benefit_monthly = 0.0
    if "other_income_monthly" not in st.session_state:
        st.session_state.other_income_monthly = 0.0
    if "income_change_monthly" not in st.session_state:
        st.session_state.income_change_monthly = 0.0
    if "income_start_month" not in st.session_state:
        st.session_state.income_start_month = 0
    if "income_start_amount" not in st.session_state:
        st.session_state.income_start_amount = 0.0
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
    if "one_time_income" not in st.session_state:
        st.session_state.one_time_income = 0.0
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
            "Monthly living expenses (excl. debt payments)",
            value="",
            placeholder="e.g. 3400",
        )
        debt_payment_raw = st.text_input(
            "Debt payments / month",
            value="",
            placeholder="e.g. 320",
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
            expenses = parse_float_input(
                expenses_raw,
                float(profile.get("expenses_monthly", 0.0)),
                "Monthly living expenses (excl. debt payments)",
            )
            debt_payment_monthly = parse_float_input(
                debt_payment_raw,
                float(profile.get("debt_payment_monthly", 0.0)),
                "Debt payments / month",
            )
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
            "debt_payment_monthly": debt_payment_monthly,
            "savings": savings,
            "debt": debt,
            "industry": industry,
            "job_stability": job_stability,
            "dependents": int(dependents),
        }
        st.session_state.baseline_summary = None
        st.session_state.baseline_profile_sig = None
        monthly_net = income - (expenses + debt_payment_monthly)
        if monthly_net >= 0:
            runway_months = 60.0
        else:
            runway_months = compute_runway(savings, abs(monthly_net), 0.0) if compute_runway else 0.0
        ensure_baseline_summary(st.session_state.profile, monthly_net, runway_months, show_spinner=True)
        st.session_state.show_profile_dialog = False
        st.success("Profile saved.")


@st.dialog("Load the demo profile?")
def demo_profile_dialog() -> None:
    if not SAMPLE_REQUEST:
        st.info("Demo profile is unavailable.")
        st.session_state.show_demo_dialog = False
        return

    profile = SAMPLE_REQUEST.get("profile", {})
    def money(value: float) -> str:
        return f"${float(value):,.0f}"

    st.markdown(
        "Use a pre-filled demo profile to explore RiseArc with realistic sample numbers. "
        "This will replace any current profile."
    )
    st.markdown("**Demo profile snapshot**")
    st.markdown(
        "\n".join(
            [
                f"- Monthly income: {money(profile.get('income_monthly', 0))}",
                f"- Monthly living expenses (excl. debt): {money(profile.get('expenses_monthly', 0))}",
                f"- Debt payments / month: {money(profile.get('debt_payment_monthly', 0))}",
                f"- Total required outflow / month: {money(profile_total_monthly_expenses(profile))}",
                f"- Savings: {money(profile.get('savings', 0))}",
                f"- Debt: {money(profile.get('debt', 0))}",
                f"- Industry: {profile.get('industry', 'Other')}",
                f"- Job stability: {profile.get('job_stability', 'stable').title()}",
                f"- Dependents: {profile.get('dependents', 0)}",
            ]
        )
    )
    st.caption("Financial overview will generate when you open the Survival Timeline tab.")

    action_cols = st.columns([1, 1])
    with action_cols[0]:
        if st.button("Use demo profile", type="primary", use_container_width=True):
            apply_demo_profile()
            st.session_state.show_demo_dialog = False
            st.rerun()
    with action_cols[1]:
        if st.button("Cancel", use_container_width=True):
            st.session_state.show_demo_dialog = False
            st.session_state.show_profile_dialog = False
            st.rerun()


def normalize_numeric_text(raw: str) -> str:
    return (
        raw.replace(",", "")
        .replace("$", "")
        .replace("%", "")
        .strip()
    )


def parse_optional_float(
    raw: str,
    fallback: float,
    label: str,
    *,
    min_value: float = 0.0,
    max_value: float | None = None,
) -> float | None:
    if raw is None or raw.strip() == "":
        value = float(fallback)
    else:
        try:
            value = float(normalize_numeric_text(raw))
        except ValueError:
            st.error(f"Please enter a valid number for {label}.")
            return None
    value = max(value, min_value)
    if max_value is not None:
        value = min(value, max_value)
    return value


def parse_optional_float_signed(raw: str, fallback: float, label: str) -> float | None:
    if raw is None or raw.strip() == "":
        return fallback
    try:
        value = float(normalize_numeric_text(raw))
    except ValueError:
        st.error(f"Please enter a valid number for {label}.")
        return None
    return max(min(value, 50000.0), -50000.0)


def parse_optional_int(
    raw: str,
    fallback: int,
    label: str,
    *,
    min_value: int = 0,
    max_value: int | None = None,
) -> int | None:
    if raw is None or raw.strip() == "":
        value = int(fallback)
    else:
        try:
            value = int(float(normalize_numeric_text(raw)))
        except ValueError:
            st.error(f"Please enter a valid whole number for {label}.")
            return None
    value = max(value, min_value)
    if max_value is not None:
        value = min(value, max_value)
    return value


def render_landing() -> None:
    st.markdown(
        """
        <div class="hero fade-in">
          <span class="badge">Nemotron-3-Nano Powered</span>
          <div class="hero-title">RiseArc Financial Assistant</div>
          <div class="hero-subtitle">
            A financial analysis app that simulates real-world scenarios, summarizes risks, and delivers actionable plans.
            RiseArc helps you understand how resilient your finances are under different situations.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("\n")
    cols = st.columns(3)
    cards = [
        ("Survival Simulator", "Simulate your finances under job-loss and expense-shift scenarios."),
        ("Scenario Builder", "Describe a scenario and review a tailored analysis."),
        ("Survival Timeline", "See a month-by-month runway and financial overview."),
    ]
    for col, (title, text) in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div class="card landing-card fade-in">
                  <div class="card-title">{title}</div>
                  <div class="card-text">{text}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("\n")
    steps = st.columns(3)
    step_cards = [
        ("1. Profile", "Secure your financial overview with one-time onboarding."),
        ("2. Simulate", "Run scenario checks in seconds and view the timeline."),
        ("3. Act", "Receive clear steps and guardrails from RiseArc."),
    ]
    for col, (title, text) in zip(steps, step_cards):
        with col:
            st.markdown(
                f"""
                <div class="card landing-card fade-in">
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
    income_start_month: int,
    income_start_amount: float,
    income_change_monthly: float,
    extra_monthly_expenses: float,
    debt_payment_monthly: float,
    healthcare_monthly: float,
    dependent_care_monthly: float,
    job_search_monthly: float,
    one_time_expense: float,
    one_time_income: float,
    relocation_cost: float,
    overrides: Dict[str, float],
    subscriptions: Dict[str, float],
    news_event: Dict[str, Any],
    scenario_note: str = "",
) -> Dict[str, Any]:
    profile_payload = dict(profile)
    if overrides:
        if overrides.get("override_income_monthly") is not None:
            profile_payload["income_monthly"] = float(overrides["override_income_monthly"])
        if overrides.get("override_expenses_monthly") is not None:
            profile_payload["expenses_monthly"] = float(overrides["override_expenses_monthly"])
        if overrides.get("override_savings") is not None:
            profile_payload["savings"] = float(overrides["override_savings"])
        if overrides.get("override_debt") is not None:
            profile_payload["debt"] = float(overrides["override_debt"])

    payload: Dict[str, Any] = {
        "profile": profile_payload,
        "scenario": {
            "months_unemployed": months_unemployed,
            "expense_cut_pct": expense_cut_pct,
            "severance": severance,
            "unemployment_benefit_monthly": unemployment_benefit_monthly,
            "other_income_monthly": other_income_monthly,
            "income_start_month": income_start_month,
            "income_start_amount": income_start_amount,
            "income_change_monthly": income_change_monthly,
            "extra_monthly_expenses": extra_monthly_expenses,
            "debt_payment_monthly": debt_payment_monthly,
            "healthcare_monthly": healthcare_monthly,
            "dependent_care_monthly": dependent_care_monthly,
            "job_search_monthly": job_search_monthly,
            "one_time_expense": one_time_expense,
            "one_time_income": one_time_income,
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
            st.rerun()
        return

    def scenario_text_field(label: str, key: str, placeholder: str) -> str:
        st.markdown(f'<div class="field-label">{label}</div>', unsafe_allow_html=True)
        return st.text_input(
            "",
            key=key,
            placeholder=placeholder,
            label_visibility="collapsed",
        )

    st.markdown('<div class="card-text">Build a sandbox scenario and run a survival scan.</div>', unsafe_allow_html=True)
    st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

    with st.form("scenario_form"):
        st.markdown('<div class="section-title">Scenario prompt</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-subtitle">Describe the scenario you want to simulate.</div>', unsafe_allow_html=True)

        scenario_note = st.text_area(
            "",
            value=st.session_state.get("scenario_note_raw", ""),
            placeholder="Example: I might lose my job for 5 months, can cut expenses by 20%, and have $3k severance.",
            height=90,
            label_visibility="collapsed",
            key="scenario_note_raw",
        )

        st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Scenario parameters <span class="muted">(optional)</span></div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-text">Enter desired scenario factors. Baseline debt payments from your profile are already included.</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)
        row1_left, row1_right = st.columns(2)
        with row1_left:
            months_unemployed_raw = scenario_text_field("Months unemployed", "months_unemployed_raw", "e.g. 6")
        with row1_right:
            expense_cut_raw = scenario_text_field("Expense cut (%)", "expense_cut_raw", "e.g. 15")

        row2_left, row2_right = st.columns(2)
        with row2_left:
            severance_raw = scenario_text_field("Severance / payout", "severance_raw", "e.g. 3000")
        with row2_right:
            one_time_income_raw = scenario_text_field("One-time income (windfall)", "one_time_income_raw", "e.g. 100000")

        row3_left, row3_right = st.columns(2)
        with row3_left:
            unemployment_raw = scenario_text_field("Unemployment benefits / month", "unemployment_benefit_raw", "e.g. 600")
        with row3_right:
            other_income_raw = scenario_text_field("Other income / month", "other_income_raw", "e.g. 200")

        row4_left, row4_right = st.columns(2)
        with row4_left:
            income_change_raw = scenario_text_field("Income change / month", "income_change_raw", "e.g. 500 or -500")
        with row4_right:
            debt_payment_raw = scenario_text_field("Additional debt payments / month", "debt_payment_raw", "e.g. 250")

        row5_left, row5_right = st.columns(2)
        with row5_left:
            healthcare_raw = scenario_text_field("Healthcare / insurance / month", "healthcare_raw", "e.g. 150")
        with row5_right:
            dependent_care_raw = scenario_text_field("Dependent care / month", "dependent_care_raw", "e.g. 0")

        row6_left, row6_right = st.columns(2)
        with row6_left:
            job_search_raw = scenario_text_field("Job search / reskilling / month", "job_search_raw", "e.g. 100")
        with row6_right:
            extra_expenses_raw = scenario_text_field("Other monthly expenses", "extra_monthly_raw", "e.g. 75")

        row7_left, row7_right = st.columns(2)
        with row7_left:
            one_time_raw = scenario_text_field("One-time expense", "one_time_raw", "e.g. 1200")
        with row7_right:
            relocation_raw = scenario_text_field("Relocation / legal (one-time)", "relocation_raw", "e.g. 2500")

        st.markdown('</div>', unsafe_allow_html=True)

        run_submitted = st.form_submit_button("Run Analysis")

    if run_submitted:
        st.session_state.scenario_note = scenario_note
        months_unemployed = parse_optional_int(
            months_unemployed_raw,
            0,
            "Months unemployed",
            min_value=0,
            max_value=36,
        )
        expense_cut_pct = parse_optional_float(
            expense_cut_raw,
            0.0,
            "Expense cut (%)",
            min_value=0.0,
            max_value=70.0,
        )
        severance = parse_optional_float(
            severance_raw, 0.0, "Severance / payout"
        )
        one_time_income = parse_optional_float(
            one_time_income_raw, 0.0, "One-time income"
        )
        unemployment_benefit_monthly = parse_optional_float(
            unemployment_raw, 0.0, "Unemployment benefits"
        )
        other_income_monthly = parse_optional_float(
            other_income_raw, 0.0, "Other income"
        )
        income_start_month = 0
        income_start_amount = 0.0
        income_change_monthly = parse_optional_float_signed(
            income_change_raw, 0.0, "Income change"
        )
        debt_payment_monthly = parse_optional_float(
            debt_payment_raw, 0.0, "Additional debt payments"
        )
        healthcare_monthly = parse_optional_float(
            healthcare_raw, 0.0, "Healthcare"
        )
        dependent_care_monthly = parse_optional_float(
            dependent_care_raw, 0.0, "Dependent care"
        )
        job_search_monthly = parse_optional_float(
            job_search_raw, 0.0, "Job search"
        )
        extra_monthly_expenses = parse_optional_float(
            extra_expenses_raw, 0.0, "Other monthly expenses"
        )
        one_time_expense = parse_optional_float(
            one_time_raw, 0.0, "One-time expense"
        )
        relocation_cost = parse_optional_float(
            relocation_raw, 0.0, "Relocation / legal"
        )

        if None in [
            months_unemployed,
            expense_cut_pct,
            severance,
            one_time_income,
            unemployment_benefit_monthly,
            other_income_monthly,
            income_start_month,
            income_start_amount,
            income_change_monthly,
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
        st.session_state.one_time_income = one_time_income
        st.session_state.unemployment_benefit_monthly = unemployment_benefit_monthly
        st.session_state.other_income_monthly = other_income_monthly
        st.session_state.income_change_monthly = income_change_monthly
        st.session_state.debt_payment_monthly = debt_payment_monthly
        st.session_state.healthcare_monthly = healthcare_monthly
        st.session_state.dependent_care_monthly = dependent_care_monthly
        st.session_state.job_search_monthly = job_search_monthly
        st.session_state.extra_monthly_expenses = extra_monthly_expenses
        st.session_state.one_time_expense = one_time_expense
        st.session_state.relocation_cost = relocation_cost

        applied: Dict[str, float] = {}
        with st.spinner("Analyzing scenario..."):
            parsed = extract_scenario_from_text(scenario_note, use_model=True)
            applied = apply_scenario_update(parsed)
            if "income_start_month" not in parsed:
                st.session_state.income_start_month = 0
                applied.pop("income_start_month", None)
            if "income_start_amount" not in parsed:
                st.session_state.income_start_amount = 0.0
                applied.pop("income_start_amount", None)

        merged_values: Dict[str, float] = {
            "months_unemployed": float(months_unemployed),
            "expense_cut_pct": float(expense_cut_pct),
            "severance": float(severance),
            "one_time_income": float(one_time_income),
            "unemployment_benefit_monthly": float(unemployment_benefit_monthly),
            "other_income_monthly": float(other_income_monthly),
            "income_start_month": float(income_start_month),
            "income_start_amount": float(income_start_amount),
            "income_change_monthly": float(income_change_monthly),
            "debt_payment_monthly": float(debt_payment_monthly),
            "healthcare_monthly": float(healthcare_monthly),
            "dependent_care_monthly": float(dependent_care_monthly),
            "job_search_monthly": float(job_search_monthly),
            "extra_monthly_expenses": float(extra_monthly_expenses),
            "one_time_expense": float(one_time_expense),
            "relocation_cost": float(relocation_cost),
        }
        for key in list(merged_values.keys()):
            if key in applied:
                merged_values[key] = float(applied[key])

        months_unemployed = int(merged_values["months_unemployed"])
        expense_cut_pct = float(merged_values["expense_cut_pct"])
        severance = float(merged_values["severance"])
        one_time_income = float(merged_values["one_time_income"])
        unemployment_benefit_monthly = float(merged_values["unemployment_benefit_monthly"])
        other_income_monthly = float(merged_values["other_income_monthly"])
        income_start_month = int(merged_values["income_start_month"])
        income_start_amount = float(merged_values["income_start_amount"])
        income_change_monthly = float(merged_values["income_change_monthly"])
        debt_payment_monthly = float(merged_values["debt_payment_monthly"])
        healthcare_monthly = float(merged_values["healthcare_monthly"])
        dependent_care_monthly = float(merged_values["dependent_care_monthly"])
        job_search_monthly = float(merged_values["job_search_monthly"])
        extra_monthly_expenses = float(merged_values["extra_monthly_expenses"])
        one_time_expense = float(merged_values["one_time_expense"])
        relocation_cost = float(merged_values["relocation_cost"])
        overrides = st.session_state.get("scenario_overrides", {})
        payload = build_payload_from_state(
            profile=st.session_state.profile,
            months_unemployed=int(months_unemployed),
            expense_cut_pct=float(expense_cut_pct),
            severance=severance,
            one_time_income=one_time_income,
            unemployment_benefit_monthly=unemployment_benefit_monthly,
            other_income_monthly=other_income_monthly,
            income_start_month=int(income_start_month),
            income_start_amount=float(income_start_amount),
            income_change_monthly=income_change_monthly,
            extra_monthly_expenses=extra_monthly_expenses,
            debt_payment_monthly=debt_payment_monthly,
            healthcare_monthly=healthcare_monthly,
            dependent_care_monthly=dependent_care_monthly,
            job_search_monthly=job_search_monthly,
            one_time_expense=one_time_expense,
            relocation_cost=relocation_cost,
            overrides=overrides,
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
        metrics = sanitize_metrics(result.get("metrics", {}))
        timeline = result.get("timeline", [])
        m1, m2, m3 = st.columns(3)
        monthly_net_burn = float(metrics.get("monthly_net_burn", 0.0))
        runway_value = float(metrics.get("runway_months", 0.0))
        if monthly_net_burn <= 0:
            m1.metric("Cash Flow", "Positive")
        else:
            runway_label = f"{runway_value:.1f}"
            m1.metric("Runway (months)", runway_label)
        m2.metric("Risk score", f"{metrics.get('risk_score', 0):.0f}/100")
        m3.metric("Adjusted risk", f"{metrics.get('adjusted_risk_score', 0):.0f}/100")
        st.progress(min(int(metrics.get("risk_score", 0)), 100))

        if timeline:
            depletion_month = render_timeline_chart(timeline, height=260)
            if depletion_month is None:
                st.caption(
                    f"Balance stays above $0 throughout the {len(timeline) - 1}-month chart horizon."
                )
            else:
                st.caption(f"Balance crosses below $0 around month {depletion_month}.")

        st.subheader("Financial Analysis")
        summary_text = result.get("summary", "")
        if not summary_text.strip():
            st.info("Nemotron returned an empty summary. Please try again.")
        else:
            fallback_scenario = result.get("scenario", {})
            fallback_profile = result.get("profile", st.session_state.profile or {})
            fallback_text = build_scenario_fallback_summary(
                fallback_profile,
                fallback_scenario if isinstance(fallback_scenario, dict) else {},
                metrics,
            )
            summary_text = enforce_readability_guardrail(summary_text, fallback=fallback_text)
            st.markdown(format_structured_markdown(summary_text))


def render_survival_timeline() -> None:
    if not st.session_state.profile:
        st.info("Please complete your profile to unlock the full experience.")
        if st.button("Complete profile"):
            st.session_state.show_profile_dialog = True
            st.rerun()
        return

    profile = st.session_state.profile
    baseline_scenario = {
        "months_unemployed": 0,
        "expense_cut_pct": 0.0,
        "severance": 0.0,
        "unemployment_benefit_monthly": 0.0,
        "other_income_monthly": 0.0,
        "income_change_monthly": 0.0,
        "extra_monthly_expenses": 0.0,
        "debt_payment_monthly": 0.0,
        "healthcare_monthly": 0.0,
        "dependent_care_monthly": 0.0,
        "job_search_monthly": 0.0,
        "one_time_expense": 0.0,
        "one_time_income": 0.0,
        "relocation_cost": 0.0,
        "baseline_mode": True,
    }
    computed = compute_financials(
        profile,
        baseline_scenario,
        baseline_mode=True,
        horizon_months=TIMELINE_HORIZON_MONTHS,
    )
    metrics = sanitize_metrics(computed["metrics"])
    monthly_net = computed["monthly_net"]
    runway_months = metrics.get("runway_months", 0.0)
    risk_score = metrics.get("risk_score", 0.0)
    savings = float(profile.get("savings", 0.0))

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

    timeline = computed["timeline"]
    timeline_stats = computed["timeline_stats"]
    depletion_month = render_timeline_chart(timeline, height=280) if timeline else None
    timeline_horizon = max(len(timeline) - 1, 0)
    if timeline:
        if depletion_month is None:
            st.caption(f"Balance stays above $0 for the full {timeline_horizon}-month horizon.")
        else:
            st.caption(f"Balance crosses below $0 around month {depletion_month}.")

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
        depletion_text = (
            f"{int(depletion_month)} months"
            if depletion_month is not None
            else f"Not within {timeline_horizon} months"
        )
        max_drawdown = float(timeline_stats.get("max_drawdown", 0.0))
        trend_slope = float(timeline_stats.get("trend_slope", 0.0))
        st.markdown(
            f"""
            <div class="card">
              <div class="card-title">Timeline Insights</div>
              <div class="card-text">Cash depletion point: {depletion_text}</div>
              <div class="card-text">Max drawdown: {format_currency(max_drawdown)}</div>
              <div class="card-text">Trend slope: {format_money_signed(trend_slope)} / month</div>
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

    st.subheader("Financial Analysis")
    nemotron_online = get_nemotron_status()
    show_spinner = st.session_state.baseline_summary is None and nemotron_online
    if show_spinner and st.session_state.get("baseline_notice_pending"):
        if hasattr(st, "toast"):
            st.toast("Generating financial overview...")
        else:
            st.info("Generating financial overview...")
        st.session_state.baseline_notice_pending = False

    if not nemotron_online:
        st.info("Nemotron is offline. Start the server to generate the financial overview.")
        return
    summary_text = ensure_baseline_summary(profile, monthly_net, runway_months, show_spinner=show_spinner)
    if not summary_text.strip():
        st.info("Financial overview is empty right now. Please try again.")
        return
    summary_html = render_summary_html(summary_text)
    st.markdown(
        f"<div class='summary-block'>"
        f"<div class='summary-title'>Financial Overview</div>"
        f"{summary_html}"
        f"</div>",
        unsafe_allow_html=True,
    )


def build_chat_metrics(profile: Dict[str, Any]) -> Dict[str, float]:
    baseline_scenario = {
        "months_unemployed": 0,
        "expense_cut_pct": 0.0,
        "severance": 0.0,
        "unemployment_benefit_monthly": 0.0,
        "other_income_monthly": 0.0,
        "income_change_monthly": 0.0,
        "extra_monthly_expenses": 0.0,
        "debt_payment_monthly": 0.0,
        "healthcare_monthly": 0.0,
        "dependent_care_monthly": 0.0,
        "job_search_monthly": 0.0,
        "one_time_expense": 0.0,
        "one_time_income": 0.0,
        "relocation_cost": 0.0,
        "baseline_mode": True,
    }
    computed = compute_financials(profile, baseline_scenario, baseline_mode=True, horizon_months=1)
    metrics = computed["metrics"]
    metrics["monthly_net"] = computed["monthly_net"]
    return metrics


def build_job_loss_metrics(profile: Dict[str, Any]) -> Dict[str, float]:
    scenario = {
        "months_unemployed": 6,
        "expense_cut_pct": 0.0,
        "severance": 0.0,
        "unemployment_benefit_monthly": 0.0,
        "other_income_monthly": 0.0,
        "income_change_monthly": 0.0,
        "extra_monthly_expenses": 0.0,
        "debt_payment_monthly": 0.0,
        "healthcare_monthly": 0.0,
        "dependent_care_monthly": 0.0,
        "job_search_monthly": 0.0,
        "one_time_expense": 0.0,
        "one_time_income": 0.0,
        "relocation_cost": 0.0,
    }
    computed = compute_financials(profile, scenario, baseline_mode=False, horizon_months=12)
    metrics = computed["metrics"]
    metrics["monthly_net"] = -profile_total_monthly_expenses(profile)
    return metrics


def render_chat() -> None:
    header_cols = st.columns([4, 1])
    with header_cols[0]:
        st.markdown("<div class='page-title'>RiseArc Assistant</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='page-subtitle'>Nemotron-powered financial intelligence</div>",
            unsafe_allow_html=True,
        )
    with header_cols[1]:
        if st.button("Clear chat"):
            st.session_state.chat_history = []

    if not st.session_state.profile:
        st.info("Complete your profile to unlock the assistant.")
        return

    if not query_nemotron:
        st.warning("Nemotron is unavailable right now. Please start the server to enable chat.")
        return

    prompt_text = st.chat_input("Ask RiseArc about your finances")
    pending_prompt = st.session_state.pending_prompt
    if prompt_text:
        pending_prompt = prompt_text
        st.session_state.pending_prompt = ""
        st.session_state.quick_prompt_used = True

    for idx, message in enumerate(st.session_state.chat_history):
        avatar = "🤖" if message["role"] == "assistant" else "👤"
        with st.chat_message(message["role"], avatar=avatar):
            if message["role"] == "assistant":
                safe_content = enforce_readability_guardrail(
                    str(message.get("content", "")),
                    fallback="I can restate that clearly. Ask me again and I will answer cleanly.",
                )
                if has_corrupted_spacing(safe_content) or has_garbled_sequences(safe_content):
                    safe_content = "I can restate that clearly. Ask me again and I will answer cleanly."
                if safe_content != message.get("content", ""):
                    st.session_state.chat_history[idx]["content"] = safe_content
                st.markdown(render_plain_chat_text(safe_content), unsafe_allow_html=True)
            else:
                st.text(message["content"])

    prompt_container = st.empty()
    clicked_quick_prompt = None
    if not st.session_state.chat_history and not st.session_state.quick_prompt_used and not pending_prompt:
        with prompt_container.container():
            st.caption("Try a quick prompt:")
            suggestion_cols = st.columns(3)
            suggestions = [
                "What if I lose my job tomorrow?",
                "What actions should I take right now?",
                "What's my biggest risk?",
            ]
            for col, text in zip(suggestion_cols, suggestions):
                with col:
                    if st.button(text, use_container_width=True):
                        clicked_quick_prompt = text
        if clicked_quick_prompt:
            st.session_state.quick_prompt_used = True
            st.session_state.pending_prompt = clicked_quick_prompt
            pending_prompt = clicked_quick_prompt
            prompt_container.empty()

    if pending_prompt:
        profile = st.session_state.profile
        metrics = build_chat_metrics(profile)
        is_small = is_small_talk(pending_prompt)
        use_structured = should_use_structured_chat_response(pending_prompt, st.session_state.chat_history)
        use_job_loss = is_job_loss_intent(pending_prompt)
        scenario_payload = None
        scenario_metrics = None
        if use_job_loss:
            scenario_payload = {
                "months_unemployed": 6,
                "expense_cut_pct": 0.0,
                "severance": 0.0,
            }
            scenario_metrics = build_job_loss_metrics(profile)

        with st.chat_message("user", avatar="👤"):
            st.text(pending_prompt)
        with st.chat_message("assistant", avatar="🤖"):
            typing_placeholder = st.empty()
            typing_placeholder.markdown(
                '<div class="typing">RiseArc is thinking <span class="dots"><span></span><span></span><span></span></span></div>',
                unsafe_allow_html=True,
            )
            try:
                if is_small:
                    smalltalk_prompt = (
                        "You are RiseArc, a friendly financial assistant. Respond briefly and naturally "
                        "to the user's message in 1-2 sentences. Do not use headings or bullets. "
                        "Do not use a fixed template or repeated sentence; vary your wording. "
                        "If the user greets you, greet them back. If they ask how you are, answer politely "
                        "and then ask what they would like help with. Do not mention finances unless the "
                        "user does. Never mention investing, stocks, ETFs, crypto, or portfolios."
                        f"\nUser: {pending_prompt}\nAssistant:"
                    )
                    response = extract_text(query_nemotron(smalltalk_prompt)).strip()
                    record_nemotron_status(True)
                    response = clean_text_block(response)
                elif use_structured:
                    response = nemotron_generate_structured(
                        mode="chat",
                        profile=profile,
                        metrics=metrics,
                        scenario=scenario_payload,
                        scenario_metrics=scenario_metrics,
                        timeline_stats=None,
                        question=pending_prompt,
                        include_followup=True,
                    )
                else:
                    response = nemotron_generate_conversational(
                        profile=profile,
                        metrics=metrics,
                        scenario=scenario_payload,
                        scenario_metrics=scenario_metrics,
                        question=pending_prompt,
                        chat_history=st.session_state.chat_history,
                    )
            except Exception as exc:
                record_nemotron_status(False)
                response = format_nemotron_error(str(exc), "chat response")
            response = enforce_readability_guardrail(
                response,
                fallback="I can restate that clearly. Do you want me to focus on cash flow, runway, or risk?",
            )
            if has_corrupted_spacing(response) or has_garbled_sequences(response):
                response = "I can restate that clearly. Do you want me to focus on cash flow, runway, or risk?"
            display_response = format_readable_text(response)
            typing_placeholder.markdown(render_plain_chat_text(display_response), unsafe_allow_html=True)

        st.session_state.chat_history.append({"role": "user", "content": pending_prompt})
        formatted_response = enforce_readability_guardrail(
            format_readable_text(response),
            fallback="I can restate that clearly. Do you want me to focus on cash flow, runway, or risk?",
        )
        if has_corrupted_spacing(formatted_response) or has_garbled_sequences(formatted_response):
            formatted_response = "I can restate that clearly. Do you want me to focus on cash flow, runway, or risk?"
        st.session_state.chat_history.append({"role": "assistant", "content": formatted_response})
        st.session_state.pending_prompt = ""


def main() -> None: 
    st.set_page_config(page_title="RiseArc", layout="wide")
    inject_css()
    inject_tooltip_killer()
    inject_chat_input_positioner()
    init_state()
    maybe_show_update_dialog()
    render_sidebar()

    if st.session_state.show_demo_dialog:
        demo_profile_dialog()
    elif st.session_state.show_profile_dialog:
        profile_dialog()

    if st.session_state.active_view != "Chat":
        st.markdown(f"<div class='page-title'>{st.session_state.active_view}</div>", unsafe_allow_html=True)
        st.markdown("<div class='page-subtitle'>Nemotron-powered financial intelligence</div>", unsafe_allow_html=True)

    if st.session_state.active_view == "Introduction":
        render_landing()
    elif st.session_state.active_view == "Scenario Builder":
        render_scenario_builder()
    elif st.session_state.active_view == "Survival Timeline":
        render_survival_timeline()
    else:
        render_chat()


if __name__ == "__main__":
    main()
