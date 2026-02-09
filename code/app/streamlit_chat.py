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
BASELINE_SUMMARY_VERSION = "v3-nemotron-json"


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
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  border: none;
  color: white;
  padding: 10px 18px;
  border-radius: 10px;
  font-weight: 600;
  cursor: pointer;
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


def normalize_chat_formatting(text: str) -> str:
    if not text:
        return ""
    lines = text.splitlines()
    normalized: List[str] = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            normalized.append("")
            continue
        if stripped.startswith("#"):
            heading = re.sub(r"^#+\s*", "", stripped).strip()
            if heading and not heading.endswith(":"):
                heading = f"{heading}:"
            if heading:
                normalized.append(heading)
            continue
        if re.match(r"^\$[\d,]+(?:\.\d+)?\.?$", stripped):
            continue
        if re.match(r"^\$[\d,]+(?:\.\d+)?\.\s+", stripped):
            stripped = re.sub(r"^\$[\d,]+(?:\.\d+)?\.\s+", "- ", stripped)
        if re.match(r"^\$[A-Za-z_]+\.?\s+", stripped):
            stripped = re.sub(r"^\$[A-Za-z_]+\.?\s+", "- ", stripped)
        if re.match(r"^\d+[\.)]\s+", stripped):
            stripped = re.sub(r"^\d+[\.)]\s+", "- ", stripped)
        if stripped.startswith("- "):
            next_line = ""
            for follow in lines[index + 1:]:
                follow = follow.strip()
                if follow:
                    next_line = follow
                    break
            content = stripped[2:].strip()
            if next_line.startswith("- ") and ":" not in content and " - " not in content and not content.endswith("."):
                stripped = f"{content}:"
        normalized.append(stripped)
    cleaned = "\n".join(normalized)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def force_section_breaks(text: str) -> str:
    if not text:
        return ""
    pattern = r"([^\n])\s*(Summary|Key Facts|What this means|What to do first|Warnings)\s*:"

    def _insert_break(match: re.Match) -> str:
        prefix = match.group(1)
        heading = match.group(2)
        return f"{prefix}\n{heading}:"

    return re.sub(pattern, _insert_break, text, flags=re.IGNORECASE).strip()


def bold_chat_headings(text: str) -> str:
    if not text:
        return ""
    canonical = {
        "summary": "Summary",
        "key facts": "Key Facts",
        "what this means": "What this means",
        "what to do first": "What to do first",
        "warnings": "Warnings",
    }
    lines = text.splitlines()
    output: List[str] = []
    for line in lines:
        stripped = line.strip()
        match = re.match(
            r"^(summary|key facts|what this means|what to do first|warnings)\s*:?\s*(.*)$",
            stripped,
            flags=re.IGNORECASE,
        )
        if match:
            label = canonical.get(match.group(1).lower(), match.group(1).title())
            rest = match.group(2).strip()
            if rest:
                output.append(f"**{label}:**")
                output.append(rest)
            else:
                output.append(f"**{label}:**")
        else:
            output.append(line)
    return "\n".join(output).strip()


def remove_actively_prefix(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"(?m)^(-\s*)Actively\s+", r"\1", text)
    cleaned = re.sub(r"(?m)^(\\*\\*?[A-Za-z ]+\\*\\*?:\\s*)Actively\\s+", r"\\1", cleaned)
    cleaned = re.sub(r"([.!?])\\s+Actively\\s+", r"\\1 ", cleaned)
    return cleaned


def add_risk_score_explanation(text: str, risk_score: float) -> str:
    if not text:
        return ""
    if risk_score <= 0:
        return text
    if risk_score >= 80:
        meaning = "high financial vulnerability if income drops"
    elif risk_score >= 60:
        meaning = "elevated vulnerability if income weakens"
    elif risk_score >= 40:
        meaning = "moderate vulnerability if income slows"
    else:
        meaning = "lower vulnerability if income stays stable"

    lines = text.splitlines()
    output: List[str] = []
    current_section = ""
    for line in lines:
        stripped = line.strip()
        header_match = re.match(
            r"^(summary|key facts|what this means|what to do first|warnings)\s*:?",
            stripped,
            flags=re.IGNORECASE,
        )
        if header_match:
            current_section = header_match.group(1).lower()
            output.append(line)
            continue
        if "risk score" in stripped.lower() and current_section != "key facts":
            if not re.search(r"(vulnerab|risk level|low|moderate|elevated|high)", stripped.lower()):
                line = line.rstrip()
                if line.endswith("."):
                    line = line[:-1]
                line = f"{line} — {meaning}."
        output.append(line)
    return "\n".join(output)


def ensure_risk_score_line(text: str, risk_score: float) -> str:
    if not text:
        return ""
    if risk_score <= 0 or re.search(r"risk score", text, flags=re.IGNORECASE):
        return text
    if risk_score >= 80:
        meaning = "high financial vulnerability if income drops"
    elif risk_score >= 60:
        meaning = "elevated vulnerability if income weakens"
    elif risk_score >= 40:
        meaning = "moderate vulnerability if income slows"
    else:
        meaning = "lower vulnerability if income stays stable"
    insert_line = f"- Risk score: {risk_score:.0f}/100 ({meaning})."
    lines = text.splitlines()
    output: List[str] = []
    inserted = False
    for line in lines:
        output.append(line)
        if not inserted and re.match(r"^Summary\\s*:?$", line.strip(), flags=re.IGNORECASE):
            output.append(insert_line)
            inserted = True
    if not inserted:
        output.append(insert_line)
    return "\n".join(output)


def normalize_runway_mentions(text: str, runway_months: float) -> str:
    if not text or runway_months <= 0:
        return text
    target = f"{runway_months:.1f} months"
    patterns = [
        r"(runway[^.]*?)(\\d+(?:\\.\\d+)?)\\s+months",
        r"(savings[^.]*?last[^.]*?)(\\d+(?:\\.\\d+)?)\\s+months",
        r"(cash[^.]*?last[^.]*?)(\\d+(?:\\.\\d+)?)\\s+months",
        r"(run out in|exhausted in|last about|last roughly|last around)\\s+(\\d+(?:\\.\\d+)?)\\s+months",
    ]
    cleaned = text
    for pattern in patterns:
        cleaned = re.sub(
            pattern,
            lambda m: f"{m.group(1)} {target}",
            cleaned,
            flags=re.IGNORECASE,
        )
    cleaned = re.sub(
        r"\\b(under|less than)\\s+a\\s+year\\b",
        f"about {target}",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned


def replace_runway_when_surplus(text: str, monthly_net_burn: float) -> str:
    if not text or monthly_net_burn > 0:
        return text
    lines = text.splitlines()
    output: List[str] = []
    inserted = False
    for line in lines:
        if "runway" in line.lower():
            continue
        output.append(line)
        if not inserted and re.match(r"^Summary\\s*:?$", line.strip(), flags=re.IGNORECASE):
            output.append("- Cash flow is positive; runway is not a near-term constraint.")
            inserted = True
    if not inserted:
        output.append("- Cash flow is positive; runway is not a near-term constraint.")
    return "\n".join(output).strip()


def add_runway_detail_if_missing(
    text: str,
    profile: Dict[str, Any],
    scenario: Dict[str, Any],
    metrics: Dict[str, float],
) -> str:
    if not text:
        return ""
    if re.search(r"runway", text, flags=re.IGNORECASE):
        return text
    monthly_net_burn = float(metrics.get("monthly_net_burn", 0.0))
    if monthly_net_burn <= 0:
        return text
    savings = float(profile.get("savings", 0.0))
    severance = float(scenario.get("severance", 0.0))
    one_time_income = float(scenario.get("one_time_income", 0.0))
    one_time_total = float(scenario.get("one_time_expense", 0.0)) + float(scenario.get("relocation_cost", 0.0))
    starting_cash = savings + severance + one_time_income - one_time_total
    runway_months = float(metrics.get("runway_months", 0.0))
    def money(value: float) -> str:
        return f"${value:,.0f}"
    runway_line = (
        f"- Starting cash of {money(starting_cash)} at a burn of {money(monthly_net_burn)}/mo "
        f"gives a runway of about {runway_months:.1f} months."
    )
    lines = text.splitlines()
    output: List[str] = []
    inserted = False
    for line in lines:
        output.append(line)
        if not inserted and re.match(r"^Summary\\s*:?$", line.strip(), flags=re.IGNORECASE):
            output.append(runway_line)
            inserted = True
    if not inserted:
        output.append(runway_line)
    return "\n".join(output).strip()


def remove_net_burn_from_actions(text: str) -> str:
    if not text:
        return ""
    lines = text.splitlines()
    output: List[str] = []
    in_actions = False
    for line in lines:
        stripped = line.strip()
        if re.match(r"^Actions\\s*:?$", stripped, flags=re.IGNORECASE):
            in_actions = True
            output.append(line)
            continue
        if re.match(r"^(Summary|Key Facts|What this means|What to do first|Warnings)\\s*:?$", stripped, flags=re.IGNORECASE):
            in_actions = False
        if in_actions and re.search(r"monthly expenses|net burn|burn rate|monthly outlay", stripped, flags=re.IGNORECASE):
            continue
        output.append(line)
    return "\n".join(output).strip()


def annotate_risk_change(text: str, baseline_risk: float, current_risk: float) -> str:
    if not text or baseline_risk <= 0 or current_risk <= 0:
        return text
    def _add_context(match: re.Match) -> str:
        return f"{match.group(0)} (current: {current_risk:.0f}/100, baseline: {baseline_risk:.0f}/100)"
    cleaned = re.sub(r"risk score will rise above\\s+\\d+", _add_context, text, flags=re.IGNORECASE)
    cleaned = re.sub(r"risk score rises above\\s+\\d+", _add_context, cleaned, flags=re.IGNORECASE)
    return cleaned


def format_structured_response(text: str, monthly_net: float) -> str:
    if not text:
        return ""
    text = force_section_breaks(text)
    text = ensure_section_spacing(text)
    has_structure = bool(
        re.search(
            r"(Summary|Key Facts|What this means|What to do first|Warnings)\s*:",
            text,
            flags=re.IGNORECASE,
        )
    )
    if not has_structure:
        return text

    text = remove_runway_mentions_if_positive(text, monthly_net)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    canonical = {
        "summary": "Summary",
        "key facts": "Key Facts",
        "what this means": "What this means",
        "what to do first": "What to do first",
        "warnings": "Warnings",
    }
    sections: Dict[str, List[str]] = {label: [] for label in canonical.values()}
    current = ""
    for line in lines:
        match = re.match(
            r"^(Summary|Key Facts|What this means|What to do first|Warnings)\s*:\s*(.*)$",
            line,
            flags=re.IGNORECASE,
        )
        if match:
            key = canonical.get(match.group(1).lower().strip(), match.group(1).title())
            current = key
            rest = match.group(2).strip()
            if rest:
                sections.setdefault(current, []).append(rest)
            continue
        if current:
            sections.setdefault(current, []).append(line)

    def _clean_sentence(value: str) -> str:
        cleaned = re.sub(r"\s+", " ", value).strip()
        cleaned = re.sub(r"(\d)\s+%", r"\1%", cleaned)
        cleaned = re.sub(r":\s*$", "", cleaned)
        cleaned = re.sub(r":\s*\.", ".", cleaned)
        if cleaned and cleaned[0].isalpha():
            cleaned = cleaned[0].upper() + cleaned[1:]
        if cleaned and cleaned[-1] not in ".!?":
            cleaned += "."
        return cleaned

    def _split_items(entry: str) -> List[str]:
        if not entry:
            return []
        if entry.count(":") >= 2:
            chunks = [c.strip() for c in re.split(r"\s*:\s*(?=[A-Za-z])", entry) if c.strip()]
        else:
            chunks = [entry]
        items: List[str] = []
        for chunk in chunks:
            parts = [p.strip() for p in re.split(r"\s*[-•]\s+|\s*;\s*", chunk) if p.strip()]
            items.extend(parts if parts else [chunk])
        return [i for i in items if i and i != "-"]

    output: List[str] = []
    if sections.get("Summary"):
        summary_text = _clean_sentence(" ".join(sections["Summary"]))
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", summary_text) if s.strip()]
        if len(sentences) > 2:
            summary_text = " ".join(sentences[:2])
        output.append("Summary:")
        output.append(summary_text)

    if sections.get("Key Facts"):
        if output:
            output.append("")
        output.append("Key Facts:")
        key_items: List[str] = []
        for entry in sections["Key Facts"]:
            if entry.startswith("- "):
                key_items.append(entry[2:].strip())
            else:
                key_items.extend(_split_items(entry))
        for item in key_items:
            output.append(f"- {_clean_sentence(item)}")

    if sections.get("What this means"):
        if output:
            output.append("")
        output.append("What this means:")
        meaning_items: List[str] = []
        for entry in sections["What this means"]:
            if entry.startswith("- "):
                meaning_items.append(entry[2:].strip())
            else:
                meaning_items.extend(_split_items(entry))
        meaning_items = [i for i in meaning_items if i]
        if len(meaning_items) > 1:
            for item in meaning_items:
                output.append(f"- {_clean_sentence(item)}")
        elif meaning_items:
            output.append(_clean_sentence(meaning_items[0]))

    if sections.get("What to do first"):
        if output:
            output.append("")
        output.append("What to do first:")
        action_items: List[str] = []
        for entry in sections["What to do first"]:
            if entry.startswith("- "):
                action_items.append(entry[2:].strip())
            else:
                action_items.extend(_split_items(entry))
        for item in action_items:
            output.append(f"- {_clean_sentence(item)}")

    if sections.get("Warnings"):
        if output:
            output.append("")
        output.append("Warnings:")
        warning_items: List[str] = []
        for entry in sections["Warnings"]:
            if entry.startswith("- "):
                warning_items.append(entry[2:].strip())
            else:
                warning_items.extend(_split_items(entry))
        for item in warning_items:
            output.append(f"- {_clean_sentence(item)}")

    return "\n".join(output).strip()


def normalize_key_fact_labels(text: str) -> str:
    if not text:
        return ""
    label_map = {
        "monthly income": "Monthly Income",
        "monthly expenses": "Monthly Expenses",
        "monthly cash flow": "Monthly cash flow",
        "income": "Income",
        "expenses": "Expenses",
        "total savings": "Total Savings",
        "total debt": "Total Debt",
        "savings": "Savings",
        "debt": "Debt",
        "debt-to-annual-income ratio": "Debt-to-annual-income ratio",
        "debt ratio": "Debt ratio",
        "risk score": "Risk score",
    }
    pattern = r"\b(monthly income|monthly expenses|monthly cash flow|total savings|total debt|income|expenses|savings|debt|debt-to-annual-income ratio|debt ratio|risk score)\s*:"
    def _fix_label(match: re.Match) -> str:
        label = match.group(1).lower()
        return f"{label_map.get(label, match.group(1).title())}:"
    return re.sub(pattern, _fix_label, text, flags=re.IGNORECASE)


def ensure_section_spacing(text: str) -> str:
    if not text:
        return ""
    pattern = r"(Summary|Key Facts|What this means|What to do first|Warnings)\s*:"
    parts = re.split(pattern, text, flags=re.IGNORECASE)
    if len(parts) == 1:
        return text.strip()

    output: List[str] = []
    for index, part in enumerate(parts):
        if index == 0:
            prefix = part.strip()
            if prefix:
                output.append(prefix)
            continue
        if index % 2 == 1:
            heading = part.strip().title()
            if output:
                output.append("")
            output.append(f"{heading}:")
        else:
            content = part.strip()
            if content:
                output.append(content)
    return "\n".join(output).strip()


def fix_key_fact_placeholders(
    text: str,
    profile: Dict[str, Any],
    metrics: Dict[str, float],
) -> str:
    if not text:
        return ""
    def money(value: float) -> str:
        return f"${value:,.0f}"
    income = money(float(profile.get("income_monthly", 0.0)))
    expenses = money(float(profile.get("expenses_monthly", 0.0)))
    savings = money(float(profile.get("savings", 0.0)))
    debt = money(float(profile.get("debt", 0.0)))
    debt_ratio = f"{float(metrics.get('debt_ratio', 0.0)):.2f}"
    risk_score = f"{float(metrics.get('risk_score', 0.0)):.0f}/100"
    monthly_net = float(metrics.get("monthly_net", 0.0))
    monthly_cash_flow = f"{money(monthly_net)}" if monthly_net >= 0 else f"-{money(abs(monthly_net))}"
    cleaned = normalize_key_fact_labels(text)
    replacements = {
        "Monthly Income": income,
        "Monthly Expenses": expenses,
        "Monthly cash flow": monthly_cash_flow,
        "Total Savings": savings,
        "Total Debt": debt,
        "Income": income,
        "Expenses": expenses,
        "Savings": savings,
        "Debt": debt,
        "Debt-to-annual-income ratio": debt_ratio,
        "Debt ratio": debt_ratio,
        "Risk score": risk_score,
    }
    for label, value in replacements.items():
        cleaned = re.sub(
            rf"(?i)\b{re.escape(label)}\s*:\s*(income|expenses|savings|debt|buffer|cash|risk|ratio)\b",
            f"{label}: {value}",
            cleaned,
        )
    cleaned = re.sub(
        r"(?i)\bDebt-to-annual-income ratio\s*:\s*debt\b",
        f"Debt-to-annual-income ratio: {debt_ratio}",
        cleaned,
    )
    cleaned = re.sub(
        r"(?i)\bMonthly cash flow[^:]*:\s*\$?0(?:\.0+)?\b",
        f"Monthly cash flow (income - expenses): {monthly_cash_flow}",
        cleaned,
    )
    cleaned = re.sub(
        r"(?i)\bRisk score\s*:\s*\$?[\d,]+(?:\.\d+)?(?:\s*/\s*100|\s+out of 100)?\b",
        f"Risk score: {risk_score}",
        cleaned,
    )
    return cleaned.strip()


def override_key_facts_section(
    text: str,
    profile: Dict[str, Any],
    metrics: Dict[str, float],
) -> str:
    if not text:
        return text

    def money(value: float) -> str:
        return f"${value:,.0f}"

    income = float(profile.get("income_monthly", 0.0))
    expenses = float(profile.get("expenses_monthly", 0.0))
    savings = float(profile.get("savings", 0.0))
    debt = float(profile.get("debt", 0.0))
    monthly_net = float(metrics.get("monthly_net", income - expenses))
    debt_ratio = float(metrics.get("debt_ratio", 0.0))
    risk_score = float(metrics.get("risk_score", 0.0))

    facts = [
        f"- Income: {money(income)}",
        f"- Expenses: {money(expenses)}",
        f"- Savings: {money(savings)}",
        f"- Debt: {money(debt)}",
        f"- Debt ratio: {debt_ratio:.2f} ({debt_ratio*100:.0f}% of annual income)",
        f"- Risk score: {risk_score:.0f}/100",
    ]
    if monthly_net != 0:
        facts.insert(2, f"- Monthly net (income - expenses): {money(monthly_net)}")

    block = "\n".join(["Key Facts:"] + facts)

    pattern = re.compile(
        r"(^|\\n)(\\*\\*\\s*)?Key Facts\\s*\\*\\*?\\s*:?\\s*(.*?)(?=\\n(?:Summary|Key Facts|What this means|What to do first|Warnings)\\s*:|\\Z)",
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not pattern.search(text):
        return text
    return pattern.sub(lambda m: f"{m.group(1)}{block}\n", text).strip()


def append_followup_if_structured(text: str) -> str:
    if not text:
        return ""
    has_structure = bool(
        re.search(
            r"^\s*(Summary|Key Facts|What this means|What to do first|Warnings)\s*:",
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    )
    if not has_structure:
        return text
    trimmed = text.strip()
    if re.search(r"\?\s*$", trimmed):
        return trimmed
    followup = "Do you want me to clarify any part or go deeper on one of these points?"
    return f"{trimmed}\n\n{followup}"


def ensure_no_placeholders(
    text: str,
    profile: Dict[str, Any],
    metrics: Dict[str, float],
) -> str:
    if not text:
        return ""
    cleaned = repair_summary_placeholders(text, profile, {}, metrics)
    cleaned = scrub_placeholder_leaks(cleaned, profile, metrics)
    if not has_placeholder_tokens(cleaned):
        return cleaned.strip()

    debt_ratio_value = float(metrics.get("debt_ratio", 0.0))
    risk_value = float(metrics.get("risk_score", 0.0))
    runway_value = (
        f"{float(metrics.get('runway_months', 0.0)):.1f} months" if metrics.get("runway_months") is not None else ""
    )
    cleaned = re.sub(r"\$[A-Za-z_]+\b", "", cleaned)
    cleaned = re.sub(r"\bdebt ratio near\s+debt\b", f"debt ratio near {debt_ratio_value:.2f}", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bdebt ratio is\s+debt\b", f"debt ratio is {debt_ratio_value:.2f}", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bdebt ratio\s*:\s*debt\b", f"debt ratio: {debt_ratio_value:.2f}", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bdebt ratio\s+debt\b", f"debt ratio {debt_ratio_value:.2f}", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"\bdebt ratio\s+of\s+income\s+of\s+annual\s+income\b",
        f"debt ratio of {debt_ratio_value:.2f} ({debt_ratio_value*100:.0f}% of annual income)",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\brisk score of\s+-?\$?[\d,]+(?:\.\d+)?\b", f"risk score of {risk_value:.0f}/100", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\brisk score is\s+-?\$?[\d,]+(?:\.\d+)?/100\b", f"risk score is {risk_value:.0f}/100", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\brisk score is\s+-?\$?[\d,]+(?:\.\d+)?\s+out of 100\b", f"risk score is {risk_value:.0f}/100", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"\brisk score(?:\s+\w+)?\s+(?:at|around|near|remains at)\s+-?\$?[\d,]+(?:\.\d+)?(?:/100|\s+out of 100)?\b",
        f"risk score is {risk_value:.0f}/100",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\brisk score\s*\(\s*\$?[\d,]+(?:\.\d+)?\s*\)",
        f"risk score {risk_value:.0f}/100",
        cleaned,
        flags=re.IGNORECASE,
    )
    if runway_value:
        cleaned = re.sub(
            r"\b(income|expenses|savings|buffer|cash|spend|spending)\s+months\b",
            runway_value,
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"\$[\d,]+(?:\.\d+)?\s+months\b", runway_value, cleaned, flags=re.IGNORECASE)
        days_value = f"{max(1, round(metrics.get('runway_months', 0.0) * 30)):d} days"
        cleaned = re.sub(r"\$[\d,]+(?:\.\d+)?\s+days\b", days_value, cleaned, flags=re.IGNORECASE)
    else:
        cleaned = re.sub(r"\$([\d,]+(?:\.\d+)?)\s+months\b", r"\1 months", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned


def fix_cash_flow_statements(text: str, monthly_net: float) -> str:
    if not text:
        return ""
    if monthly_net <= 0:
        return text

    def money(value: float) -> str:
        return f"${value:,.0f}"

    positive_phrase = f"monthly net is positive at about {money(monthly_net)}"
    cleaned = text
    cleaned = re.sub(
        r"\bmonthly net[^.!?]*\bzero\b",
        positive_phrase,
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bnet\s+(?:is|sits|stands)\s+(?:near|around|about|essentially)?\s*zero\b",
        positive_phrase,
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bbreak[- ]even\b",
        "positive cash flow",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned


def enforce_scenario_net_burn_line(
    text: str,
    scenario: Dict[str, Any],
    metrics: Dict[str, float],
) -> str:
    if not text:
        return ""
    def money(value: float) -> str:
        return f"${value:,.0f}"

    monthly_expenses_cut = float(metrics.get("monthly_expenses_cut", 0.0))
    monthly_support = float(metrics.get("monthly_support", 0.0))
    monthly_addons = (
        float(scenario.get("extra_monthly_expenses", 0.0))
        + float(scenario.get("debt_payment_monthly", 0.0))
        + float(scenario.get("healthcare_monthly", 0.0))
        + float(scenario.get("dependent_care_monthly", 0.0))
        + float(scenario.get("job_search_monthly", 0.0))
    )
    monthly_net_burn = float(metrics.get("monthly_net_burn", monthly_expenses_cut + monthly_addons - monthly_support))
    income_start_month = int(scenario.get("income_start_month", 0) or 0)
    income_start_amount = float(scenario.get("income_start_amount", 0.0) or 0.0)

    if abs(monthly_net_burn) < 0.01:
        net_line = (
            f"- Monthly expenses after cuts are {money(monthly_expenses_cut)} "
            f"and monthly support matches them, so cash flow is break-even."
        )
    elif monthly_net_burn >= 0:
        if monthly_addons > 0:
            net_line = (
                f"- Monthly expenses after cuts are {money(monthly_expenses_cut)}, plus "
                f"{money(monthly_addons)} in add-ons"
            )
        else:
            net_line = f"- Monthly expenses after cuts are {money(monthly_expenses_cut)}"

        if monthly_support > 0:
            net_line += f" and {money(monthly_support)} in monthly support"
        else:
            net_line += " with no incoming cash"

        net_line += f", leaving a net burn of {money(monthly_net_burn)}/mo."
    else:
        surplus = abs(monthly_net_burn)
        net_line = (
            f"- Monthly expenses after cuts are {money(monthly_expenses_cut)} with "
            f"{money(monthly_support)} in monthly support, leaving a surplus of {money(surplus)}/mo."
        )
    if income_start_month > 0 and income_start_amount > 0:
        net_line += f" Additional income of {money(income_start_amount)}/mo starts month {income_start_month}."

    replaced = False
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.search(r"net burn|burn rate|monthly burn", line, flags=re.IGNORECASE):
            lines[i] = net_line
            replaced = True
            break
    if not replaced:
        for i, line in enumerate(lines):
            if re.search(r"monthly outlay|expenses after cuts|after a .*% expense|monthly expenses", line, flags=re.IGNORECASE):
                lines[i] = net_line
                break
    return "\n".join(lines).strip()


def fix_time_leaks(text: str, scenario: Dict[str, Any], profile: Dict[str, Any]) -> str:
    if not text:
        return ""
    income_start_month = int(scenario.get("income_start_month", 0) or 0)
    income_monthly = float(profile.get("income_monthly", 0.0))
    expenses_monthly = float(profile.get("expenses_monthly", 0.0))
    savings = float(profile.get("savings", 0.0))
    debt = float(profile.get("debt", 0.0))

    def _replace_month(match: re.Match) -> str:
        raw = match.group(1)
        try:
            value = float(raw.replace(",", ""))
        except ValueError:
            return match.group(0)
        if value >= 100 or value in {income_monthly, expenses_monthly, savings, debt}:
            if income_start_month > 0:
                return f"month {income_start_month}"
            return "month"
        return match.group(0)

    return re.sub(r"\bmonth\s+\$?([\d,]+(?:\.\d+)?)\b", _replace_month, text, flags=re.IGNORECASE)


def enforce_phase_aware_summary(text: str, scenario: Dict[str, Any], metrics: Dict[str, float]) -> str:
    if not text:
        return ""
    income_start_month = int(scenario.get("income_start_month", 0) or 0)
    income_start_amount = float(scenario.get("income_start_amount", 0.0) or 0.0)
    if income_start_month <= 0 or income_start_amount <= 0:
        return text

    runway_months = float(metrics.get("runway_months", 0.0))
    phase_sentence = (
        f"With additional income starting in month {income_start_month}, "
        f"your overall runway is about {runway_months:.1f} months."
    )

    text = re.sub(
        r"(?i)your savings will last[^.]*burn rate[^.]*\.",
        phase_sentence,
        text,
    )
    text = re.sub(r"(?i)current burn rate", "pre-contract burn rate", text)

    if not re.search(r"month\\s+\\d+.*income", text, flags=re.IGNORECASE):
        text = re.sub(
            r"(?i)summary:\\s*",
            f"Summary:\n- Additional income of ${income_start_amount:,.0f}/mo starts month {income_start_month}, reducing the burn rate after that point.\n",
            text,
            count=1,
        )
    return text


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
    text = re.sub(r"\s*(Summary|Actions|Warnings)\s*:\s*", r"\n\1:\n", text, flags=re.IGNORECASE)
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    sections: Dict[str, List[str]] = {"Summary": [], "Actions": [], "Warnings": []}
    current = ""
    for line in lines:
        header_match = re.match(r"^(summary|actions|warnings)\s*:?\s*$", line, flags=re.IGNORECASE)
        if header_match:
            current = header_match.group(1).capitalize()
            continue
        bullet_match = re.match(r"^[-•]\s*(.*)", line)
        if bullet_match and current:
            bullet_text = bullet_match.group(1).strip()
            if bullet_text:
                sections[current].append(bullet_text)
            continue
        inline_bullets = re.split(r"\s+-\s+", line)
        if current and len(inline_bullets) > 1:
            for chunk in inline_bullets:
                chunk = chunk.strip()
                if chunk and chunk not in {"-", "•"}:
                    sections[current].append(chunk)
            continue
        if current and line in {"-", "•"}:
            continue
        if current and line:
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
        bullets = [_clean_bullet(item) for item in sections[header] if item.strip()][:3]
        if not bullets:
            continue
        if not first_section:
            output_lines.append("")
        first_section = False
        output_lines.append(f"{header}:")
        for bullet in bullets:
            output_lines.append(f"- {bullet}")
    return tidy_summary_spacing("\n".join(output_lines).strip())


def tidy_summary_spacing(text: str) -> str:
    if not text:
        return ""
    raw_lines = [line.rstrip() for line in text.splitlines()]
    cleaned_lines: List[str] = []
    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.endswith(":") and cleaned_lines:
            if cleaned_lines[-1] != "":
                cleaned_lines.append("")
        cleaned_lines.append(stripped)
    return "\n".join(cleaned_lines).strip()


def format_section_spacing(text: str) -> str:
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    output: List[str] = []
    for line in lines:
        if re.match(r"^(verdict|summary|actions|warnings)\s*:", line, flags=re.IGNORECASE):
            if output and output[-1] != "":
                output.append("")
            output.append(line)
            continue
        output.append(line)
    return "\n".join(output).strip()


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


def is_structured_intent(prompt_text: str) -> bool:
    if not prompt_text:
        return False
    if is_small_talk(prompt_text):
        return False
    normalized = normalize_chat_text(prompt_text)
    if not normalized:
        return False
    triggers = [
        "what if", "what should", "what actions", "next steps", "biggest risk", "risk",
        "runway", "survival", "timeline", "scenario", "analysis", "summary",
        "job", "layoff", "laid off", "unemployment", "fired", "severance",
        "budget", "debt", "savings", "income", "expenses", "cash flow",
    ]
    return any(term in normalized for term in triggers)


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


def normalize_chat_text(text: str) -> str:
    lowered = text.strip().lower()
    cleaned = re.sub(r"[^a-z0-9\\s]", " ", lowered)
    cleaned = re.sub(r"\\s+", " ", cleaned).strip()
    return cleaned


def strip_bottom_line(text: str) -> str:
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    cleaned = [line for line in lines if not re.match(r"^bottom line\\s*:", line, flags=re.IGNORECASE)]
    return "\n".join(cleaned).strip()


def strip_bottom_line_anywhere(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"\\bBottom line:\\s*[^.!?]*(?:[.!?]|$)", "", text, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\\s{2,}", " ", cleaned).strip()
    return cleaned


def ensure_small_talk_reply(user_text: str, response: str) -> str:
    cleaned = strip_bottom_line_anywhere(response)
    normalized = normalize_chat_text(user_text)
    if "how are you" in normalized or "how are you doing" in normalized:
        if not re.search(r"\\b(i'?m|i am|doing|well|good|great|okay|fine)\\b", cleaned, flags=re.IGNORECASE):
            if cleaned:
                cleaned = f"I'm doing well, thanks for asking. {cleaned}"
            else:
                cleaned = "I'm doing well, thanks for asking. What would you like to look at today?"
    return cleaned.strip()


def parse_summary_sections(text: str) -> Dict[str, Any]:
    if not text:
        return {"sections": {}}
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

    def _clean_bullet(text_line: str) -> str:
        cleaned = re.sub(r"\s+", " ", text_line).strip()
        cleaned = re.sub(r"(\d)\s+%", r"\1%", cleaned)
        if cleaned and cleaned[0].isalpha():
            cleaned = cleaned[0].upper() + cleaned[1:]
        if cleaned and cleaned[-1] not in ".!?":
            cleaned += "."
        return cleaned

    for key in list(sections.keys()):
        sections[key] = [_clean_bullet(item) for item in sections[key] if item.strip()]

    return {"sections": sections}


def render_summary_html(summary_text: str) -> str:
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


def repair_summary_placeholders(
    text: str,
    profile: Dict[str, Any],
    scenario: Dict[str, Any],
    metrics: Dict[str, float],
) -> str:
    if not text:
        return ""

    def money(value: float) -> str:
        return f"${value:,.0f}"

    income = float(profile.get("income_monthly", 0.0))
    expenses = float(profile.get("expenses_monthly", 0.0))
    savings = float(profile.get("savings", 0.0))
    debt = float(profile.get("debt", 0.0))
    baseline_cash_flow = income - expenses
    net_burn = metrics.get("monthly_net_burn")
    net_flow = -float(net_burn) if net_burn is not None else baseline_cash_flow

    def money_signed(value: float) -> str:
        sign = "-" if value < 0 else ""
        return f"{sign}${abs(value):,.0f}"

    replacements = {
        r"\$income\b": money(income),
        r"\$expenses\b": money(expenses),
        r"\$savings\b": money(savings),
        r"\$debt\b": money(debt),
        r"\$buffer\b": money(savings),
        r"\$reserve\b": money(savings),
    }
    expenses_value = metrics.get("monthly_expenses_cut")
    if expenses_value is None:
        expenses_value = expenses
    replacements.update(
        {
            r"\$spend(?:ing)?\b": money(float(expenses_value)),
            r"\$expense(?:s)?\b": money(float(expenses_value)),
            r"\$support\b": money(float(metrics.get("monthly_support", 0.0))),
            r"\$payment(?:s)?\b": money(float(metrics.get("monthly_net_burn", 0.0))),
        }
    )
    for pattern, value in replacements.items():
        text = re.sub(pattern, value, text, flags=re.IGNORECASE)

    text = re.sub(
        r"\$(cash flow|cashflow)(\s+per\s+month|\s+month)?\b",
        money_signed(net_flow),
        text,
        flags=re.IGNORECASE,
    )
    if metrics.get("runway_months") is not None:
        text = re.sub(
            r"\$runway\b",
            f"{metrics.get('runway_months', 0.0):.1f} months",
            text,
            flags=re.IGNORECASE,
        )

    if scenario.get("expense_cut_pct") is not None:
        text = re.sub(
            r"\bexpenses?\s*%\b",
            f"{float(scenario.get('expense_cut_pct', 0.0)):.0f}%",
            text,
            flags=re.IGNORECASE,
        )

    if metrics.get("debt_ratio") is not None:
        debt_ratio_value = float(metrics.get("debt_ratio", 0.0))
        text = re.sub(
            r"\bdebt ratio is\s+debt\b",
            f"debt ratio is {debt_ratio_value:.2f}",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\bdebt ratio\s*:\s*debt\b",
            f"debt ratio: {debt_ratio_value:.2f}",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\bdebt ratio near\s+debt\b",
            f"debt ratio near {debt_ratio_value:.2f}",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\bdebt-to-annual-income ratio\s*:\s*debt\b",
            f"debt-to-annual-income ratio: {debt_ratio_value:.2f}",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\bdebt ratio is\s+\$[\d,]+(?:\.\d+)?\b",
            f"debt ratio is {debt_ratio_value:.2f}",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\bdebt ratio\s*:\s*\$?[\d,]+(?:\.\d+)?\b",
            f"debt ratio: {debt_ratio_value:.2f}",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"(debt ratio[^\d]{0,20})(\$?[\d,]+(?:\.\d+)?%?)",
            lambda m: f"{m.group(1)}{debt_ratio_value:.2f}",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\bdebt ratio is\s+debt(?:\s+of\s+annual\s+income)?\b(?:\s*\([^)]*\))?",
            f"debt ratio is {debt_ratio_value:.2f} ({debt_ratio_value*100:.0f}% of annual income)",
            text,
            flags=re.IGNORECASE,
        )

    if metrics.get("risk_score") is not None:
        risk_value = float(metrics.get("risk_score", 0.0))
        text = re.sub(
            r"\brisk score of\s+(savings|income|expenses|debt|buffer)\b",
            f"risk score of {risk_value:.0f}",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\brisk score is\s+\$?[A-Za-z_]+/100\b",
            f"risk score is {risk_value:.0f}/100",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\brisk score is\s+\$?[A-Za-z_]+\b",
            f"risk score is {risk_value:.0f}",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\brisk score(?:\s+\w+)?\s+(?:at|around|near|remains at)\s+-?\$?[\d,]+(?:\.\d+)?(?:/100|\s+out of 100)?\b",
            f"risk score is {risk_value:.0f}/100",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\brisk score is\s+\$?[\d,]+(?:\.\d+)?/100\b",
            f"risk score is {risk_value:.0f}/100",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\brisk score is\s+\$?[\d,]+(?:\.\d+)?\s+out of 100\b",
            f"risk score is {risk_value:.0f}/100",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\brisk score\s*\(\s*\$?[\d,]+(?:\.\d+)?\s*\)",
            f"risk score {risk_value:.0f}/100",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\brisk score\s*:\s*\$?[\d,]+(?:\.\d+)?(?:\s*/\s*100|\s+out of 100)?\b",
            f"risk score: {risk_value:.0f}/100",
            text,
            flags=re.IGNORECASE,
        )

    if metrics.get("runway_months") is not None:
        runway_value = f"{metrics.get('runway_months', 0.0):.1f} months"
        text = re.sub(
            r"\b(income|expenses|savings|buffer|cash|spend|spending)\s+months\b",
            runway_value,
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\b\d{1,3},\d{3}(?:\.\d+)?\s+months\b",
            runway_value,
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\$[\d,]+(?:\.\d+)?\s+months\b",
            runway_value,
            text,
            flags=re.IGNORECASE,
        )
        days_value = f"{max(1, round(metrics.get('runway_months', 0.0) * 30)):d} days"
        text = re.sub(
            r"\$[\d,]+(?:\.\d+)?\s+days\b",
            days_value,
            text,
            flags=re.IGNORECASE,
        )
    if metrics.get("runway_months") is None:
        text = re.sub(r"\$([\d,]+(?:\.\d+)?)\s+months\b", r"\1 months", text, flags=re.IGNORECASE)
    if metrics.get("runway_months") is not None:
        text = re.sub(
            r"\babout\s+\$?[\d,]+(?:\.\d+)?\s+months\b",
            runway_value,
            text,
            flags=re.IGNORECASE,
        )
    if float(metrics.get("monthly_net", 0.0)) > 0:
        text = re.sub(
            r"(?i)\bmonthly cash flow[^:]*:\s*\$?0(?:\.0+)?\b",
            "monthly cash flow (income - expenses): positive",
            text,
        )
        text = re.sub(
            r"(?i)\bmonthly cash flow[^:]*:\s*about\s*\$?0(?:\.0+)?\b",
            "monthly cash flow (income - expenses): positive",
            text,
        )
    income_start_month = int(scenario.get("income_start_month", 0) or 0)
    if income_start_month > 0:
        text = re.sub(
            r"\bmonth\s+\$[\d,]+(?:\.\d+)?\b",
            f"month {income_start_month}",
            text,
            flags=re.IGNORECASE,
        )
    return text


def enforce_runway_value(text: str, runway_months: float) -> str:
    if not text:
        return ""
    target = f"{runway_months:.1f}"
    text = re.sub(
        r"(runway[^\d]{0,24})(\d+(?:\.\d+)?)",
        lambda m: f"{m.group(1)}{target}",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(\d+(?:\.\d+)?)(\s+months?\s+of\s+runway)",
        lambda m: f"{target}{m.group(2)}",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"((?:cash\s+)?(?:reaches?|hits?|runs?\s+out|exhausted|depleted)\s+(?:zero|out)\s+in\s+)(\d+(?:\.\d+)?)",
        lambda m: f"{m.group(1)}{target}",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"((?:reach|hit|run\s+out|exhaust|deplete)\s+(?:zero|out)\s+in\s+)(\d+(?:\.\d+)?)",
        lambda m: f"{m.group(1)}{target}",
        text,
        flags=re.IGNORECASE,
    )
    return text


def remove_runway_mentions_if_positive(text: str, monthly_net: float) -> str:
    if not text or monthly_net <= 0:
        return text
    lines = text.splitlines()
    filtered_lines: List[str] = []
    for line in lines:
        if not line.strip():
            filtered_lines.append(line)
            continue
        if "runway" not in line.lower():
            filtered_lines.append(line)
            continue
        bullet_prefix = ""
        stripped = line.lstrip()
        if stripped.startswith(("-", "•", "*")):
            bullet_prefix = stripped[0] + " "
            stripped = stripped[1:].lstrip()
        sentences = re.split(r"(?<=[.!?])\s+", stripped)
        kept_sentences = [s for s in sentences if "runway" not in s.lower()]
        if not kept_sentences:
            continue
        rebuilt = " ".join(kept_sentences).strip()
        filtered_lines.append(f"{bullet_prefix}{rebuilt}" if bullet_prefix else rebuilt)
    return "\n".join(filtered_lines).strip()


def has_placeholder_tokens(text: str) -> bool:
    if not text:
        return False
    patterns = [
        r"\b(income|expenses|savings|debt|buffer|cash|spend|spending)\s+months\b",
        r"\bdebt ratio is\s+debt\b",
        r"\bdebt ratio\s*:\s*debt\b",
        r"\bdebt ratio near\s+debt\b",
        r"\bdebt-to-annual-income ratio\s*:\s*debt\b",
        r"\brisk score of\s+(savings|income|expenses|debt|buffer)\b",
        r"\brisk score of\s+-?\$?[\d,]+(?:\.\d+)?\b",
        r"\brisk score is\s+[A-Za-z_]+/100\b",
        r"\brisk score is\s+[A-Za-z_]+\b",
        r"\brisk score(?:\s+\w+)?\s+(?:at|around|near|remains at)\s+-?\$?[\d,]+(?:\.\d+)?(?:/100|\s+out of 100)?\b",
        r"\$[A-Za-z_]+\b",
        r"\bexpenses%|\bincome%|\bsavings%|\bdebt%\b",
        r"\blowpayment\b",
        r"\$[\d,]+(?:\.\d+)?\s+months\b",
        r"\$[\d,]+(?:\.\d+)?\s+days\b",
        r"\bmonthly cash flow[^:]*:\s*\$?0(?:\.0+)?\b",
        r"\bdebt ratio\s+of\s+income\s+of\s+annual\s+income\b",
    ]
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def scrub_placeholder_leaks(
    text: str,
    profile: Dict[str, Any],
    metrics: Dict[str, float],
) -> str:
    if not text:
        return ""
    income = float(profile.get("income_monthly", 0.0))
    expenses = float(profile.get("expenses_monthly", 0.0))
    savings = float(profile.get("savings", 0.0))
    debt = float(profile.get("debt", 0.0))
    def money(value: float) -> str:
        return f"${value:,.0f}"
    runway_value = None
    if metrics.get("runway_months") is not None:
        runway_value = f"{metrics.get('runway_months', 0.0):.1f} months"

    cleaned = text
    cleaned = re.sub(r"\blowpayment\b", "low payment", cleaned, flags=re.IGNORECASE)
    if runway_value:
        cleaned = re.sub(
            r"\b(income|expenses|savings|buffer|cash|spend|spending)\s+months\b",
            runway_value,
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"\b\d{1,3},\d{3}(?:\.\d+)?\s+months\b",
            runway_value,
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"\babout\s+\$?[\d,]+(?:\.\d+)?\s+months\b",
            runway_value,
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"\$[\d,]+(?:\.\d+)?\s+months\b",
            runway_value,
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"\$[\d,]+(?:\.\d+)?\s+months\b",
            runway_value,
            cleaned,
            flags=re.IGNORECASE,
        )
        days_value = f"{max(1, round(metrics.get('runway_months', 0.0) * 30)):d} days"
        cleaned = re.sub(
            r"\$[\d,]+(?:\.\d+)?\s+days\b",
            days_value,
            cleaned,
            flags=re.IGNORECASE,
        )
    cleaned = re.sub(r"\$income\b", money(income), cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\$expenses\b", money(expenses), cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\$savings\b", money(savings), cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\$debt\b", money(debt), cleaned, flags=re.IGNORECASE)
    debt_ratio_value = float(metrics.get("debt_ratio", 0.0))
    cleaned = re.sub(r"\bdebt ratio is\s+debt\b", f"debt ratio is {debt_ratio_value:.2f}", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bdebt ratio\s*:\s*debt\b", f"debt ratio: {debt_ratio_value:.2f}", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bdebt ratio near\s+debt\b", f"debt ratio near {debt_ratio_value:.2f}", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"\bdebt ratio\s+of\s+income\s+of\s+annual\s+income\b",
        f"debt ratio of {debt_ratio_value:.2f} ({debt_ratio_value*100:.0f}% of annual income)",
        cleaned,
        flags=re.IGNORECASE,
    )
    risk_value = float(metrics.get("risk_score", 0.0))
    cleaned = re.sub(
        r"\brisk score of\s+(savings|income|expenses|debt|buffer)\b",
        f"risk score of {risk_value:.0f}",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\brisk score of\s+-?\$?[\d,]+(?:\.\d+)?\b",
        f"risk score of {risk_value:.0f}/100",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\brisk score\s*:\s*-?\$?[\d,]+(?:\.\d+)?(?:\s*/\s*100|\s+out of 100)?\b",
        f"risk score: {risk_value:.0f}/100",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\brisk score(?:\s+\w+)?\s+(?:at|around|near|remains at)\s+-?\$?[\d,]+(?:\.\d+)?(?:/100|\s+out of 100)?\b",
        f"risk score is {risk_value:.0f}/100",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\$([\d,]+(?:\.\d+)?)\s+months\b", r"\1 months", cleaned, flags=re.IGNORECASE)
    # Fix "buffer of $X to 6 months" -> use proper 3-6 month range
    expenses = float(profile.get("expenses_monthly", 0.0))
    if expenses > 0:
        low = f"${expenses * 3:,.0f}"
        high = f"${expenses * 6:,.0f}"
        cleaned = re.sub(
            r"\b(buffer|emergency fund)\s+of\s+\$[\d,]+(?:\.\d+)?\s+to\s+6\s+months\b",
            rf"\1 of {low} to {high} (3 to 6 months of expenses)",
            cleaned,
            flags=re.IGNORECASE,
        )
    return cleaned.strip()


def build_scenario_fallback_summary(
    profile: Dict[str, Any],
    scenario: Dict[str, Any],
    metrics: Dict[str, float],
) -> str:
    def money(value: float) -> str:
        return f"${value:,.0f}"

    base_expenses = float(profile.get("expenses_monthly", 0.0))
    monthly_expenses_cut = float(metrics.get("monthly_expenses_cut", base_expenses))
    if monthly_expenses_cut <= 0 and base_expenses > 0:
        monthly_expenses_cut = base_expenses
    monthly_support = float(metrics.get("monthly_support", 0.0))
    monthly_net_burn = float(metrics.get("monthly_net_burn", 0.0))
    runway_months = float(metrics.get("runway_months", 0.0))
    debt_ratio = float(metrics.get("debt_ratio", 0.0))
    risk_score = float(metrics.get("risk_score", 0.0))
    income_start_month = int(float(scenario.get("income_start_month", 0) or 0))
    income_start_amount = float(scenario.get("income_start_amount", 0.0) or 0.0)

    savings = float(profile.get("savings", 0.0))
    severance = float(scenario.get("severance", 0.0))
    one_time_income = float(scenario.get("one_time_income", 0.0))
    one_time_total = float(scenario.get("one_time_expense", 0.0)) + float(scenario.get("relocation_cost", 0.0))
    starting_cash = savings + severance + one_time_income - one_time_total

    emergency_low = monthly_expenses_cut * 3
    emergency_high = monthly_expenses_cut * 6

    monthly_addons = (
        float(scenario.get("extra_monthly_expenses", 0.0))
        + float(scenario.get("debt_payment_monthly", 0.0))
        + float(scenario.get("healthcare_monthly", 0.0))
        + float(scenario.get("dependent_care_monthly", 0.0))
        + float(scenario.get("job_search_monthly", 0.0))
    )
    computed_net_burn = monthly_expenses_cut + monthly_addons - monthly_support
    if monthly_support <= 0:
        support_phrase = "with no incoming cash"
    else:
        support_phrase = f"with {money(monthly_support)} in monthly support"

    verdict = (
        f"Verdict: Without income, your buffer lasts about {runway_months:.1f} months before the cash runs out."
        if monthly_net_burn > 0
        else "Verdict: Your cash flow is positive under this scenario, so the near-term outlook is stable."
    )

    if abs(computed_net_burn) < 0.01:
        burn_line = (
            f"- Monthly expenses after cuts are {money(monthly_expenses_cut)} and monthly support matches them, "
            "so cash flow is break-even."
        )
    elif monthly_addons > 0:
        burn_line = (
            f"- Base expenses after cuts are {money(monthly_expenses_cut)} plus "
            f"{money(monthly_addons)} in add-ons {support_phrase}, leaving a net burn of "
            f"{money(computed_net_burn)}/mo."
            if computed_net_burn > 0
            else f"- Base expenses after cuts are {money(monthly_expenses_cut)} with add-ons of "
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

    income = float(profile.get("income_monthly", 0.0))
    expenses = float(profile.get("expenses_monthly", 0.0))
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


def clean_text_block(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text).strip()
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"(?<=\d)(?=[A-Za-z])", " ", cleaned)
    cleaned = cleaned.replace("$$", "$")
    cleaned = re.sub(r"\bthe user's\b", "your", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bthe user\b", "you", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\buser's\b", "your", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"(?<!\$)\b(\d{1,3}(?:,\d{3})+|\d{4,})\b(?!\s*(?:months?|years?|%|/100|/mo|/month|/year|/week))",
        r"$\1",
        cleaned,
    )
    return cleaned.strip()


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

    monthly_expenses_cut = expenses * (1 - expense_cut_pct / 100.0)
    monthly_support_base = unemployment_benefit_monthly + other_income_monthly + income_change_monthly
    if baseline_mode:
        monthly_support_base += income

    monthly_addons = (
        extra_monthly_expenses
        + debt_payment_monthly
        + healthcare_monthly
        + dependent_care_monthly
        + job_search_monthly
    )
    monthly_net_burn = monthly_expenses_cut + monthly_addons - monthly_support_base
    one_time_total = one_time_expense + relocation_cost
    starting_balance = savings + severance + one_time_income - one_time_total

    def _support_for_month(month: int) -> float:
        support = monthly_support_base
        if income_start_month > 0 and income_start_amount > 0 and month >= income_start_month:
            support += income_start_amount
        return support

    def _net_burn_for_month(month: int) -> float:
        return monthly_expenses_cut + monthly_addons - _support_for_month(month)

    max_months = 60
    runway_months = float(max_months)
    balance_probe = max(starting_balance, 0.0)
    for month in range(1, max_months + 1):
        balance_probe -= _net_burn_for_month(month)
        if balance_probe <= 0:
            runway_months = float(month)
            break

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
            "monthly_support": monthly_support_base,
            "monthly_net_burn": monthly_net_burn,
            "one_time_expense": one_time_total,
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
        "monthly_net": income - expenses,
    }


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


def render_structured_response(data: Dict[str, Any], include_followup: bool = True) -> str:
    summary = clean_text_block(str(data.get("summary", "")).strip())
    key_facts = [clean_text_block(str(item)) for item in data.get("key_facts", []) if str(item).strip()]
    meaning = clean_text_block(str(data.get("meaning", "")).strip())
    actions = [clean_text_block(str(item)) for item in data.get("actions", []) if str(item).strip()]
    warnings = [clean_text_block(str(item)) for item in data.get("warnings", []) if str(item).strip()]
    followup = clean_text_block(str(data.get("followup", "")).strip())

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
        if not followup:
            followup = "Do you want me to go deeper on any part of this?"
        lines.append(capitalize_first(followup))

    return "\n".join(lines).strip()


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
    expenses = float(profile.get("expenses_monthly", 0.0))
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
        scenario_runway = "Not constrained (cash flow positive)"
        if scenario_net_burn > 0:
            scenario_runway = format_months(scenario_values.get("runway_months", 0.0))
        scenario_payload = {
            "monthly_support": format_currency(float(scenario_values.get("monthly_support", 0.0))),
            "monthly_expenses_after_cut": format_currency(float(scenario_values.get("monthly_expenses_cut", 0.0))),
            "net_monthly_burn": format_currency(float(scenario_values.get("monthly_net_burn", 0.0))),
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
        return format_nemotron_error(str(exc), mode)

    parsed = parse_json_response(raw)
    if not parsed:
        parsed = {}

    def deterministic_fallback() -> str:
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
        )

    text = render_structured_response(parsed, include_followup=include_followup)
    if not text or has_placeholder_artifacts(text):
        return deterministic_fallback()
    return text


def format_readable_text(text: str) -> str:
    if not text:
        return ""
    if "\n" in text:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    if len(sentences) <= 2:
        return text
    return "\n".join(sentences)


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
        data["other_income_monthly"] = _amount_to_float(other_income_match.group(2))

    windfall_match = re.search(
        r"(lottery|windfall|bonus|inheritance|settlement|award|prize|jackpot)[^\d]*\$?([\d,]+)",
        lowered,
    )
    if windfall_match:
        data["one_time_income"] = _amount_to_float(windfall_match.group(2))

    start_month_match = re.search(r"(?:starting|from|beginning|starts?)\s+(?:in\s+)?month\s+(\d+)", lowered)
    income_month_match = re.search(r"\$?([\d,]+)\s*(?:/|per)?\s*(?:month|mo)\b", lowered)
    if start_month_match and income_month_match:
        data["income_start_month"] = int(float(start_month_match.group(1)))
        data["income_start_amount"] = _amount_to_float(income_month_match.group(1))
    else:
        month_any_match = re.search(r"\bmonth\s+(\d+)\b", lowered)
        if month_any_match and income_month_match and re.search(r"(contract|income|job|work|gig|freelance)", lowered):
            data["income_start_month"] = int(float(month_any_match.group(1)))
            data["income_start_amount"] = _amount_to_float(income_month_match.group(1))

    raise_match = re.search(
        r"(raise|promotion|salary increase|pay increase|pay bump)[^\d]*\$?([\d,]+)(?:\\s*(per|/)?\\s*(year|yr|annual|month|mo))?",
        lowered,
    )
    if raise_match:
        amount = _amount_to_float(raise_match.group(2))
        period = (raise_match.group(4) or "").strip()
        if period in {"year", "yr", "annual"}:
            amount = amount / 12.0
        data["income_change_monthly"] = amount

    cut_match = re.search(
        r"(pay cut|salary cut|income cut|pay reduction|salary reduction)[^\d]*\$?([\d,]+)(?:\\s*(per|/)?\\s*(year|yr|annual|month|mo))?",
        lowered,
    )
    if cut_match:
        amount = _amount_to_float(cut_match.group(2))
        period = (cut_match.group(4) or "").strip()
        if period in {"year", "yr", "annual"}:
            amount = amount / 12.0
        data["income_change_monthly"] = -amount

    theft_match = re.search(r"(robbed|stolen|theft|scammed|fraud)[^\d]*\$?([\d,]+)", lowered)
    if theft_match:
        data["one_time_expense"] = _amount_to_float(theft_match.group(2))

    savings_match = re.search(r"(savings|saved|cash on hand|cash)\s*[^\d]*\$?([\d,]+)", lowered)
    if savings_match:
        data["override_savings"] = _amount_to_float(savings_match.group(2))

    debt_match = re.search(r"(debt|owe|loan|credit card|balance)\s*[^\d]*\$?([\d,]+)", lowered)
    if debt_match:
        data["override_debt"] = _amount_to_float(debt_match.group(2))

    income_match = re.search(r"(income|salary|earn)\s*[^\d]*\$?([\d,]+)\s*(?:/|per)?\s*(?:month|mo)", lowered)
    if income_match:
        data["override_income_monthly"] = _amount_to_float(income_match.group(2))

    expense_match = re.search(r"(expenses?|spend|spending|costs?)\s*[^\d]*\$?([\d,]+)\s*(?:/|per)?\s*(?:month|mo)", lowered)
    if expense_match:
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

    debt_ratio = (
        compute_debt_ratio(profile.get("debt", 0.0), profile.get("income_monthly", 0.0))
        if compute_debt_ratio
        else 0.0
    )
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
    metrics = {"debt_ratio": debt_ratio, "risk_score": risk_score}

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
        return summary
    except Exception as exc:
        record_nemotron_status(False)
        return format_nemotron_error(str(exc), "financial overview")


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
        with st.spinner("Generating your financial overview..."):
            summary = generate_baseline_summary(profile, monthly_net, runway_months)
    else:
        summary = generate_baseline_summary(profile, monthly_net, runway_months)

    if summary.startswith("[nemotron error]"):
        return format_nemotron_error(summary, "financial overview")

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

    baseline_mode = bool(scenario.get("baseline_mode"))

    scenario_block = ""
    if scenario_note.strip() and not baseline_mode:
        scenario_block = f"\nUser Scenario Request:\n- {scenario_note.strip()}\n"

    monthly_addons_total = (
        scenario.get("extra_monthly_expenses", 0.0)
        + scenario.get("debt_payment_monthly", 0.0)
        + scenario.get("healthcare_monthly", 0.0)
        + scenario.get("dependent_care_monthly", 0.0)
        + scenario.get("job_search_monthly", 0.0)
    )
    one_time_total = scenario.get("one_time_expense", 0.0) + scenario.get("relocation_cost", 0.0)
    debt_ratio_pct = metrics["debt_ratio"] * 100
    income_start_month = int(scenario.get("income_start_month", 0) or 0)
    income_start_amount = float(scenario.get("income_start_amount", 0.0) or 0.0)

    monthly_net_burn = float(metrics.get("monthly_net_burn", 0.0))
    runway_applicable = monthly_net_burn > 0
    if baseline_mode:
        monthly_net = profile["income_monthly"] - profile["expenses_monthly"]
        computed_lines = [
            f"- Risk score (0-100): {metrics['risk_score']:.0f}",
            f"- Debt ratio (debt / annual income): {metrics['debt_ratio']:.2f} ({debt_ratio_pct:.0f}%)",
            f"- Monthly income (current): {money(profile['income_monthly'])}",
            f"- Monthly expenses (current): {money(profile['expenses_monthly'])}",
            f"- Monthly net (income - expenses): {money(monthly_net)}",
            f"- Estimated savings leaks (monthly): {money(savings_total)}",
        ]
    else:
        computed_lines = [
            f"- Risk score (0-100): {metrics['risk_score']:.0f}",
            f"- Adjusted risk score (0-100): {metrics['adjusted_risk_score']:.0f}",
            f"- Debt ratio (debt / annual income): {metrics['debt_ratio']:.2f} ({debt_ratio_pct:.0f}%)",
            f"- Monthly expenses after cut: {money(metrics['monthly_expenses_cut'])}",
            f"- Monthly support: {money(metrics.get('monthly_support', 0.0))}",
            f"- Net monthly burn: {money(metrics.get('monthly_net_burn', 0.0))}",
            f"- One-time expense: {money(metrics.get('one_time_expense', 0.0))}",
            f"- Estimated savings leaks (monthly): {money(savings_total)}",
        ]
        if runway_applicable:
            computed_lines.insert(0, f"- Runway (months): {metrics['runway_months']:.1f}")
        else:
            computed_lines.insert(0, "- Cash flow is positive; runway months are not a limiting factor.")
        if income_start_month > 0 and income_start_amount > 0:
            net_burn_before = float(metrics.get("monthly_net_burn", 0.0))
            net_burn_after = net_burn_before - income_start_amount
            computed_lines.append(f"- Additional income starts month {income_start_month}: {money(income_start_amount)}/mo")
            computed_lines.append(f"- Net burn before month {income_start_month}: {money(net_burn_before)}/mo")
            computed_lines.append(f"- Net burn from month {income_start_month}: {money(net_burn_after)}/mo")

    computed_block = "\n".join(computed_lines)

    scope_line = (
        "Generate a concise, practical financial overview based on the user's current profile (no scenario applied)."
        if baseline_mode
        else "Generate a concise, practical summary based on the user's profile and scenario."
    )
    action_line = (
        "Write actions as concrete next steps that fit the user's current situation."
        if baseline_mode
        else "Write actions as time-relevant steps (if unemployment is active, avoid passive phrasing like \"preserve\" without action)."
    )
    scenario_section = (
        "Scenario:\n- None (financial overview)"
        if baseline_mode
        else f"""
Scenario:
- Months unemployed: {scenario['months_unemployed']}
- Expense cut: {scenario['expense_cut_pct']:.0f}%
- Severance: {money(scenario['severance'])}
- Unemployment benefit (monthly): {money(scenario.get('unemployment_benefit_monthly', 0.0))}
- Other income (monthly): {money(scenario.get('other_income_monthly', 0.0))}
- New income starts (month): {scenario.get('income_start_month', 0)}
- New income amount (monthly): {money(scenario.get('income_start_amount', 0.0))}
- Income change (monthly): {money(scenario.get('income_change_monthly', 0.0))}
- Debt payments (monthly): {money(scenario.get('debt_payment_monthly', 0.0))}
- Healthcare / insurance (monthly): {money(scenario.get('healthcare_monthly', 0.0))}
- Dependent care (monthly): {money(scenario.get('dependent_care_monthly', 0.0))}
- Job search / reskilling (monthly): {money(scenario.get('job_search_monthly', 0.0))}
- Other monthly expenses: {money(scenario.get('extra_monthly_expenses', 0.0))}
- Total monthly add-ons: {money(monthly_addons_total)}
- One-time expense: {money(scenario.get('one_time_expense', 0.0))}
- One-time income (windfall): {money(scenario.get('one_time_income', 0.0))}
- Relocation / legal (one-time): {money(scenario.get('relocation_cost', 0.0))}
- Total one-time costs: {money(one_time_total)}
"""
    )

    return f"""
You are RiseArc, a financial assistant powered by Nemotron-3-Nano.
{scope_line}
Do NOT provide investment advice, stock picks, buy/sell/hold guidance, or promises of returns.
Avoid language that sounds like a recommendation to invest. Focus on cash flow, runway, and risk reduction.
If asked about investing, redirect to budgeting, debt, and emergency savings fundamentals.
Do not start action bullets with "Actively".
Use the Computed Metrics exactly as provided. Do not recompute or invent new values.
If you mention runway, use the exact runway value from Computed Metrics.
If cash flow is positive, do not mention runway months; say that savings grow instead.
If additional income starts later, explicitly mention the phase change and how the burn rate shifts.
Do not leak internal variable names like months_until_zero or raw placeholders.
Avoid contradictions: if you mention time until cash reaches zero, it must match the runway value.
When you mention risk score, explain what it means in plain terms (low/moderate/elevated/high vulnerability).
When you mention runway, explain it as how long savings would last at the current burn rate.
Order actions by priority; if income is reduced or at risk, prioritize stabilizing income first.
Do not mention inflation or interest rate changes unless the user explicitly provided them.
Do not mention partner income unless the user explicitly mentioned a partner in the scenario note.
{action_line}

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
- ...
- ...
Each section should have 2 to 3 bullets that explain the implications, not just restate numbers.

Avoid template placeholders like $debt, $savings, $income, expenses%, or {{brackets}}. Use real numbers only.
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

{scenario_section}

Computed Metrics:
{computed_block}

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

    horizon = max(int(scenario.get("months_unemployed", 0)), 1, int(scenario.get("income_start_month", 0) or 0), 36)
    computed = compute_financials(
        profile,
        scenario,
        baseline_mode=bool(scenario.get("baseline_mode")),
        horizon_months=horizon,
    )
    metrics = computed["metrics"]
    timeline = computed["timeline"]
    timeline_stats = computed["timeline_stats"]
    baseline_monthly_net = float(profile.get("income_monthly", 0.0)) - float(profile.get("expenses_monthly", 0.0))
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

        st.markdown("---")
        if st.button("Edit profile", use_container_width=True):
            st.session_state.show_profile_dialog = True

        if SAMPLE_REQUEST and st.button("Load demo profile", use_container_width=True):
            st.session_state.show_demo_dialog = True
            st.session_state.show_profile_dialog = False

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
    if "show_profile_dialog" not in st.session_state:
        st.session_state.show_profile_dialog = True
    if "show_demo_dialog" not in st.session_state:
        st.session_state.show_demo_dialog = False
    if "active_view" not in st.session_state:
        st.session_state.active_view = "Introduction"
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
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
                <a class="update-btn" href="?update=1" onclick="window.location.reload()">Update</a>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
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
                f"- Monthly expenses: {money(profile.get('expenses_monthly', 0))}",
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


def parse_optional_float(raw: str, fallback: float, label: str) -> float | None:
    if raw is None or raw.strip() == "":
        return fallback
    try:
        value = float(normalize_numeric_text(raw))
    except ValueError:
        st.error(f"Please enter a valid number for {label}.")
        return None
    return max(value, 0.0)


def parse_optional_float_signed(raw: str, fallback: float, label: str) -> float | None:
    if raw is None or raw.strip() == "":
        return fallback
    try:
        value = float(normalize_numeric_text(raw))
    except ValueError:
        st.error(f"Please enter a valid number for {label}.")
        return None
    return max(min(value, 50000.0), -50000.0)


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
          <div class="hero-title">RiseArc Financial Assistant</div>
          <div class="hero-subtitle">
            A focused financial analysis app that simulates scenarios, summarizes risk, and delivers
            clear, human guidance. Built for clarity and real-world decisions.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("\n")
    cols = st.columns(3)
    cards = [
        ("Survival Simulator", "Stress-test your finances with job-loss and expense-shift scenarios."),
        ("Scenario Builder", "Describe a scenario in plain language and review a tailored analysis."),
        ("Survival Timeline", "See a month-by-month runway and financial overview."),
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
        ("1. Profile", "Secure your financial overview with one-time onboarding."),
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
        return

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
            st.markdown('<div class="field-label">One-time income (windfall)</div>', unsafe_allow_html=True)
            one_time_income_raw = st.text_input(
                "",
                key="one_time_income_raw",
                placeholder="e.g. 100000",
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
            st.markdown('<div class="field-label">New income starts (month)</div>', unsafe_allow_html=True)
            income_start_month_raw = st.text_input(
                "",
                key="income_start_month_raw",
                placeholder="e.g. 4",
                label_visibility="collapsed",
            )
            st.markdown('<div class="field-label">New income amount (monthly)</div>', unsafe_allow_html=True)
            income_start_amount_raw = st.text_input(
                "",
                key="income_start_amount_raw",
                placeholder="e.g. 1200",
                label_visibility="collapsed",
            )
            st.markdown('<div class="field-label">Income change (monthly)</div>', unsafe_allow_html=True)
            income_change_raw = st.text_input(
                "",
                key="income_change_raw",
                placeholder="e.g. 500 or -500",
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
        st.markdown('</div>', unsafe_allow_html=True)

        run_submitted = st.form_submit_button("Run Analysis")

    if run_submitted:
        st.session_state.scenario_note = scenario_note
        months_unemployed = parse_optional_int(
            months_unemployed_raw, st.session_state.get("months_unemployed", 0), "Months unemployed"
        )
        expense_cut_pct = parse_optional_float(
            expense_cut_raw, st.session_state.get("expense_cut", 0.0), "Expense cut (%)"
        )
        severance = parse_optional_float(
            severance_raw, st.session_state.get("severance", 0.0), "Severance / payout"
        )
        one_time_income = parse_optional_float(
            one_time_income_raw, st.session_state.get("one_time_income", 0.0), "One-time income"
        )
        unemployment_benefit_monthly = parse_optional_float(
            unemployment_raw, st.session_state.get("unemployment_benefit_monthly", 0.0), "Unemployment benefits"
        )
        other_income_monthly = parse_optional_float(
            other_income_raw, st.session_state.get("other_income_monthly", 0.0), "Other income"
        )
        income_start_month = parse_optional_int(
            income_start_month_raw, st.session_state.get("income_start_month", 0), "New income start month"
        )
        income_start_amount = parse_optional_float(
            income_start_amount_raw, st.session_state.get("income_start_amount", 0.0), "New income amount"
        )
        income_change_monthly = parse_optional_float_signed(
            income_change_raw, st.session_state.get("income_change_monthly", 0.0), "Income change"
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
        st.session_state.income_start_month = income_start_month
        st.session_state.income_start_amount = income_start_amount
        st.session_state.income_change_monthly = income_change_monthly
        st.session_state.debt_payment_monthly = debt_payment_monthly
        st.session_state.healthcare_monthly = healthcare_monthly
        st.session_state.dependent_care_monthly = dependent_care_monthly
        st.session_state.job_search_monthly = job_search_monthly
        st.session_state.extra_monthly_expenses = extra_monthly_expenses
        st.session_state.one_time_expense = one_time_expense
        st.session_state.relocation_cost = relocation_cost

        with st.spinner("Analyzing scenario..."):
            parsed = extract_scenario_from_text(scenario_note, use_model=True)
            apply_scenario_update(parsed)
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
        summary_text = result.get("summary", "")
        if not summary_text.strip():
            st.info("Nemotron returned an empty summary. Please try again.")
        else:
            st.markdown(format_structured_markdown(summary_text))


def render_survival_timeline() -> None:
    if not st.session_state.profile:
        st.info("Please complete your profile to unlock the full experience.")
        if st.button("Complete profile"):
            st.session_state.show_profile_dialog = True
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
    computed = compute_financials(profile, baseline_scenario, baseline_mode=True, horizon_months=36)
    metrics = computed["metrics"]
    monthly_net = computed["monthly_net"]
    runway_months = metrics.get("runway_months", 0.0)
    risk_score = metrics.get("risk_score", 0.0)
    debt_ratio = metrics.get("debt_ratio", 0.0)
    income = float(profile.get("income_monthly", 0.0))
    expenses = float(profile.get("expenses_monthly", 0.0))
    savings = float(profile.get("savings", 0.0))
    debt = float(profile.get("debt", 0.0))

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
    timeline = computed["timeline"]
    if timeline:
        st.line_chart(timeline, height=260)

    timeline_stats = computed["timeline_stats"]
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

    st.subheader("Financial Overview")
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
    metrics["monthly_net"] = -float(profile.get("expenses_monthly", 0.0))
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

    for message in st.session_state.chat_history:
        avatar = "🤖" if message["role"] == "assistant" else "👤"
        with st.chat_message(message["role"], avatar=avatar):
            if message["role"] == "assistant":
                st.markdown(message["content"])
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
                        "user does."
                        f"\nUser: {pending_prompt}\nAssistant:"
                    )
                    response = extract_text(query_nemotron(smalltalk_prompt)).strip()
                    record_nemotron_status(True)
                    response = clean_text_block(response)
                else:
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
            except Exception as exc:
                record_nemotron_status(False)
                response = format_nemotron_error(str(exc), "chat response")
            display_response = format_readable_text(response)
            typing_placeholder.markdown(display_response)

        st.session_state.chat_history.append({"role": "user", "content": pending_prompt})
        formatted_response = format_readable_text(response)
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
