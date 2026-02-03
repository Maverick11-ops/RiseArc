from fastapi import FastAPI

from app.core.models import AnalyzeRequest, AnalyzeResponse
from app.core.pipeline import run_analysis

app = FastAPI(title="RiseArc Core API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest):
    return run_analysis(payload)
