# RiseArc, The Nemotron-Powered Financial Resilience Guardian

RiseArc is a prototype financial risk analysis application powered by NVIDIA Nemotron-3-Nano. It simulates personal financial shock scenarios (such as job loss), computes risk metrics, and converts those results into clear, actionable plan.

RiseArc is *not* just another chatbot. It is a profile-aware financial analysis system designed to help users understand how fragile or resilient their situation is under stress.

---

## Philosophy

As employment risk and financial shocks becomes harder to predict, people need tools that help them reason about financial downside scenarios before they happen.

RiseArc focuses on **anticipation rather than reaction**; helping users understand how long they can sustain themselves, where their risk comes from, and what actions matter most. Its job is to ensure that people can survive through financial shocks and be able to put food on their tables.

---

## Key Features (v0.1)

### Survival Scenario Simulator
Simulates job-loss scenarios like a customizable sandbox. For example, users can simulate how long they can sustain their current lifestyle, or simulate what if situations, such as "What if I lose my job next month?" and receive insightful analysis from Nemotron.

### Deterministic Risk Metrics
Core financial metrics are computed using deterministic tools:
- Cash runway (months)
- Debt-to-income ratio
- Financial risk score (0–100)
- etc

This ensures accuracy and prevents hallucinations from the artificial intelligence in financial calculations.

### Cash Runway Timeline
Generates a month-by-month cash balance timeline that visualizes how savings decline over time under stress.

### Nemotron-Powered Insights
NVIDIA Nemotron-3-Nano converts computed metrics into a concise, structured response:
- Summary
- Recommended Actions
- Warnings

The model is used for interpretation and explanation, not the math.

### Nemotron Financial Assistant Chatbot
A live Nemotron chatbot that assists the user and answers questions using the their profile and latest scenario metrics as context.


---

## How It Works

1. Financial Python tools are called by the Nemotron-3-Nano model, which computes financial metrics and timelines.
2. A structured prompt is built from these results.
3. Nemotron generates a clear, human-readable response.
4. The UI presents results in a simple, functional interface.

This architecture separates calculation from reasoning to ensure reliability.

---

## Architecture

- **Model:** NVIDIA Nemotron-3-Nano (deployed locally on DGX Spark)
- **UI:** Streamlit
- **Core Logic:** Python (tools + orchestration pipeline)

---

## Notes

- This project is an early-stage prototype (v0.1) built for demonstration purposes.
- This project was developed with the assistance of AI tools to accelerate development.
- UI perfection is not the primary goal in v0.1.

---

## Future Roadmap

- **Proactive Reasoning:** Enable the Nemotron model to proactively run multiple personalized scenarios everyday based on the user's profile, and warn users if risk probability is above a certain percentage. 
- **Budgeting:** Allow users to track monthly income and expenses, set saving goals, and receive insight.
- **Savings Engine:** Help users identify opportunities to save on subscriptions such as Netflix, Spotify, etc.
- **Improved UI and UX:** Add better UI and UX designed for maximum user satisfaction. 
- **RAG:** Add a real time financial/economic news ingestion system using RAG. 
- **Finetune Nemotron:** Finetune the Nemotron-3-Nano model so that it is specifically used for the finance domain.
- and much more soon