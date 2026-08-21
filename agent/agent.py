from __future__ import annotations

from .graph import MODEL_NAME, run_agent


class AttendanceAgent:
    """Stable facade used by the API, tests, and the other team members."""

    def __init__(self, model_name: str | None = None):
        # The graph is initialized from OLLAMA_MODEL at import time. Keep this facade
        # intentionally small so a future model-specific factory can be added safely.
        self.model_name = model_name or MODEL_NAME

    def ask(self, student_id: str, message: str) -> dict:
        answer, tool_trace = run_agent(student_id=student_id, user_message=message)
        return {
            "answer": answer,
            "student_id": student_id,
            "tool_trace": tool_trace,
        }


agent = AttendanceAgent()
