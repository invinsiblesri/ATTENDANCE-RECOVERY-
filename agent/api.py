from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .agent import agent
from .graph import MODEL_NAME
from .models import AgentQuery, AgentResponse, HealthResponse

app = FastAPI(
    title="AI Attendance Recovery Agent",
    version="0.1.0",
    description="A free local tool-calling attendance recovery agent.",
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", model=MODEL_NAME, backend_mode="local-demo-adapter")


@app.post("/agent/query", response_model=AgentResponse)
def query_agent(payload: AgentQuery) -> AgentResponse:
    try:
        result = agent.ask(student_id=payload.student_id, message=payload.message)
        return AgentResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {exc}") from exc
