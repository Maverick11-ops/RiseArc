from fastapi import FastAPI
from ai.nemotron_client import query_nemotron

app = FastAPI()

@app.get("/")
def root():
    return {"message": "RiseArc backend is running"}

@app.post("/chat")
def chat(prompt: str):
    response = query_nemotron(prompt)
    return {"response": response}
