from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api import attendance_api as data_api

from .agent import agent
from .graph import MODEL_NAME
from .models import AgentQuery, AgentResponse, HealthResponse

app = FastAPI(
    title="AI Attendance Recovery Agent",
    version="1.0.0",
    description="A free, local, goal-driven attendance recovery agent with trusted SQLite, RAG, memory, and notification tools.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _percentage(attended: int, conducted: int) -> float:
    return round((attended / conducted * 100.0), 2) if conducted else 0.0


@app.get("/", tags=["system"])
def root() -> dict:
    return {"service": "AI Attendance Recovery Agent", "docs": "/docs", "health": "/health"}


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", model=MODEL_NAME, backend_mode="sqlite-rag-memory")


@app.get("/dashboard/{student_id}", tags=["dashboard"])
def dashboard(student_id: str) -> dict:
    try:
        student = data_api.get_student(student_id)
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        raw = data_api.get_raw_attendance_summary(student_id)
        subjects = {subject["subject_id"]: subject for subject in data_api.get_all_subjects()}
        subject_cards = []
        for subject_id, values in raw["subjects"].items():
            percentage = _percentage(int(values["attended"]), int(values["conducted"]))
            risk = "HIGH" if percentage < 75 else "MEDIUM" if percentage < 80 else "LOW"
            subject_cards.append({
                "subject_id": subject_id,
                "subject_name": subjects[subject_id]["subject_name"],
                "subject_code": subjects[subject_id]["subject_code"],
                "attended": values["attended"],
                "conducted": values["conducted"],
                "percentage": percentage,
                "risk": risk,
            })
        subject_cards.sort(key=lambda card: card["percentage"])
        overall = _percentage(int(raw["total_attended"]), int(raw["total_conducted"]))
        return {
            "student": student,
            "overall": {"percentage": overall, "attended": raw["total_attended"], "conducted": raw["total_conducted"], "risk": "HIGH" if overall < 75 else "MEDIUM" if overall < 80 else "LOW"},
            "subjects": subject_cards,
            "timetable": data_api.get_timetable(),
            "notifications": data_api.get_notifications(student_id, unread_only=True),
            "memory": data_api.get_attendance_memory(student_id, limit=5),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Dashboard data failed: {exc}") from exc


@app.get("/notifications/{student_id}", tags=["dashboard"])
def notifications(student_id: str) -> dict:
    return {"student_id": student_id, "notifications": data_api.get_notifications(student_id)}


@app.post("/notifications/{notification_id}/read", tags=["dashboard"])
def read_notification(notification_id: int) -> dict:
    return {"notification_id": notification_id, "updated": data_api.mark_notification_as_read(notification_id)}


@app.post("/agent/query", response_model=AgentResponse, tags=["agent"])
def query_agent(payload: AgentQuery) -> AgentResponse:
    try:
        result = agent.ask(
            student_id=payload.student_id,
            message=payload.message,
            goal=payload.goal,
            subject_id=payload.subject_id,
            confirmed=payload.confirmed,
        )
        return AgentResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {exc}") from exc
