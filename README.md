# RiseArc: The Nemotron-Powered Financial Guardian
RiseArc is a next-generation financial AI app powered by NVIDIA Nemotron-3-Nano. It simulates personalized risk scenarios, surfaces savings opportunities, and delivers actionable plans based on a user's profile. RiseArc is **not** just a chatbot. It's a proactive, profile-aware financial intelligence layer built to protect people from financial instability.

## Our Philosophy
With the rapid rise of AI, new jobs and opportunities are emerging, but many roles are also being displaced. RiseArc exists to help people anticipate financial shocks, understand their risk in plain language, and take practical steps before problems hit.

## Key Features
All core features are powered by NVIDIA Nemotron-3-Nano and deterministic financial tools.

### Profile Onboarding
One-time financial intake (income, expenses, savings, debt, industry, stability) that powers every simulation, alert, and chat response.

### Scenario Engine
Interactive "what-if" simulations with adjustable unemployment duration, expense cuts, and severance to stress-test survival runway.

### Survival Timeline + Signals
Month-by-month cash runway chart with distilled signals:
- Months until zero
- Max drawdown
- Trend slope

### Guardian Signals (Proactive Alerts)
Simulated news triggers that shift risk scores based on industry exposure and profile context.

### Savings Leak Detector
Quick audit of recurring subscriptions with immediate monthly savings estimates.

### Risk Drivers Panel
Explains the top factors pushing the user’s risk score up or down, in plain language.

### RiseArc Assistant (Nemotron)
Real-time financial assistant that:
- Interprets profile + scenario context
- Explains risk in human-readable language
- Suggests concrete next actions and warnings

### Conversation Memory
Save and revisit past chat sessions from the sidebar.

## How It Works
1. **Deterministic tools** compute runway, debt ratio, risk score, and timeline signals.
2. **Nemotron** converts those results into a concise, structured narrative.
3. **UI** presents the analysis with a premium command center and chat experience.

This approach keeps the math accurate and the explanations clear.

## Architecture
- **Model:** NVIDIA Nemotron-3-Nano (local `llama-server`)
- **UI:** Streamlit
- **Core Logic:** Python tools + structured prompting
- **Optional Backend:** FastAPI `/analyze` endpoint (for API-first deployments)

## Quickstart
### One-click demo (local)
```bash
./run_demo.sh
```
This starts Streamlit and opens the app at `http://127.0.0.1:8501`.
If Nemotron is running, the assistant will respond live. If not, the app still loads and you can test UI flows.

### 1. Run Nemotron locally
Example (llama-server):
```bash
./bin/llama-server \
  --model ~/models/nemotron3-gguf/Nemotron-3-Nano-30B-A3B-UD-Q8_K_XL.gguf \
  --host 0.0.0.0 \
  --port 30000 \
  --n-gpu-layers 99 \
  --ctx-size 8192 \
  --threads 8
```

### 2. Set environment variables
```bash
export NEMOTRON_URL="http://127.0.0.1:30000/v1/chat/completions"
export NEMOTRON_MODEL="local-model"
```

### 3. Run the UI
```bash
code/risearc-env/bin/streamlit run code/app/streamlit_chat.py
```

### 4. (Optional) Run the API
If FastAPI is installed:
```bash
code/risearc-env/bin/python -m uvicorn app.main:app --app-dir code --reload
```

## Configuration
Environment variables:
- `NEMOTRON_URL` - Nemotron chat endpoint
- `NEMOTRON_MODEL` - Model id expected by the server
- `NEMOTRON_TIMEOUT` - Request timeout in seconds
- `RISEARC_API_URL` - Optional backend URL for Streamlit

## Roadmap
- Real-time news ingestion and signal classification
- Bank/transaction integrations
- More granular debt payoff and budget optimization
- Portfolio risk analysis (read-only)
- Personalized long-term savings strategies

## Notes
- This is a prototype demo focused on core intelligence and UX.
- No real bank integrations are included in v0.1.
- Alerts are simulated for demo purposes.
- Not financial advice.
