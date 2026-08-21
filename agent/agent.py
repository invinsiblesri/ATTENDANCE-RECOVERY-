from __future__ import annotations

import json
from typing import Any

from .graph import MODEL_NAME, run_agent
from .tools import (
    calculate_recovery,
    create_recovery_plan,
    get_attendance,
    get_attendance_memory,
    get_subject_attendance,
    get_timetable,
    save_attendance_event,
    save_notification,
    search_attendance_policy,
)


class AttendanceAgent:
    """Goal-driven agent facade.

    Defined product goals use an explicit, inspectable tool plan. Free-form requests still
    use the LangGraph/Ollama loop, but the product UI does not depend on chat-only behavior.
    """

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or MODEL_NAME

    @staticmethod
    def _tool(tool: Any, trace: list[str], **payload: Any) -> dict[str, Any]:
        trace.append(tool.name)
        return json.loads(tool.invoke(payload))

    @staticmethod
    def _base(student_id: str, goal: str, answer: str, decision: str, trace: list[str], **extra: Any) -> dict[str, Any]:
        return {
            "answer": answer,
            "student_id": student_id,
            "goal": goal,
            "goal_status": extra.pop("goal_status", "COMPLETED"),
            "decision": decision,
            "evidence": extra.pop("evidence", []),
            "recommendations": extra.pop("recommendations", []),
            "action": extra.pop("action", None),
            "tool_trace": trace,
        }

    def _risk(self, student_id: str) -> dict[str, Any]:
        trace: list[str] = []
        attendance = self._tool(get_attendance, trace, student_id=student_id)
        records = attendance.get("records", [])
        risks = []
        for record in records:
            percentage = float(record["attendance_percentage"])
            level = "HIGH" if percentage < 75 else "MEDIUM" if percentage < 80 else "LOW"
            risks.append({"subject": record["course_name"], "subject_id": record["course_id"], "percentage": percentage, "risk": level, "attended": record["present_classes"], "conducted": record["total_classes"]})
        risks.sort(key=lambda item: item["percentage"])
        high = [item for item in risks if item["risk"] == "HIGH"]
        decision = "Immediate recovery is required for at-risk subjects." if high else "No subject is below the 75% threshold, but medium-risk subjects need monitoring."
        answer = f"I found {len(high)} high-risk subject(s). The most urgent is {risks[0]['subject']} at {risks[0]['percentage']}%." if risks else "No attendance data was returned."
        recommendations = [f"Prioritize the next classes for {item['subject']}; {item['attended']}/{item['conducted']} attended." for item in risks[:3]]
        return self._base(student_id, "risk", answer, decision, trace, evidence=risks[:5], recommendations=recommendations, action={"type": "RISK_ASSESSMENT", "status": "COMPLETED"})

    def _leave(self, student_id: str) -> dict[str, Any]:
        trace: list[str] = []
        timetable = self._tool(get_timetable, trace, student_id=student_id, day="tomorrow")
        memory = self._tool(get_attendance_memory, trace, student_id=student_id)
        affected: list[dict[str, Any]] = []
        for class_entry in timetable.get("classes", []):
            subject_id = class_entry["subject_id"]
            attendance = self._tool(get_subject_attendance, trace, student_id=student_id, subject_id=subject_id)
            recovery = self._tool(calculate_recovery, trace, attended=attendance["present_classes"], conducted=attendance["total_classes"], target=75.0)
            policy = self._tool(search_attendance_policy, trace, question="Can a student take leave without harming attendance eligibility?", subject_id=subject_id)
            affected.append({
                "subject": attendance["course_name"],
                "subject_id": subject_id,
                "percentage": attendance["attendance_percentage"],
                "classes_needed": recovery["required_additional_classes"],
                "policy_sources": [item.get("source") or item.get("document") for item in policy.get("results", [])],
            })
        risky = [item for item in affected if item["percentage"] < 75]
        decision = "Avoid non-essential leave tomorrow because one or more affected subjects are already below the threshold." if risky else "The attendance impact is manageable, but this is an impact assessment—not official leave approval."
        answer = "I checked tomorrow's classes, the affected attendance records, recovery math, policy evidence, and previous memory. " + decision
        return self._base(student_id, "leave", answer, decision, trace, evidence=affected + [{"previous_memory_events": len(memory.get("events", []))}], recommendations=["Attend the next scheduled class in every high-risk subject.", "Use the college leave process separately if leave is still required."], action={"type": "LEAVE_IMPACT_ASSESSED", "status": "COMPLETED"})

    def _recovery(self, student_id: str, subject_id: str | None) -> dict[str, Any]:
        trace: list[str] = []
        selected_subject = subject_id or "DBMS"
        plan = self._tool(create_recovery_plan, trace, student_id=student_id, subject_id=selected_subject, target_percentage=75.0)
        if plan.get("error"):
            return self._base(student_id, "recovery", "I could not create a recovery plan because the requested subject was not found.", plan["error"], trace, goal_status="BLOCKED")
        memory = self._tool(save_attendance_event, trace, event_data={
            "student_id": student_id,
            "subject_id": plan["subject_id"],
            "event_type": "RECOVERY_PLAN",
            "description": f"Recovery plan created for {plan['course_name']} with {plan['required_additional_classes']} required classes.",
            "metadata": plan,
        })
        answer = f"Recovery plan saved for {plan['course_name']}. Attend the next {plan['required_additional_classes']} class(es) to reach {plan['target_percentage']}%."
        return self._base(student_id, "recovery", answer, "The plan is calculated from real attendance totals and the upcoming timetable.", trace, evidence=[plan], recommendations=["Attend every recommended class shown in the plan.", "Re-run risk analysis after attendance is updated."], action={"type": "RECOVERY_PLAN_SAVED", "status": "COMPLETED", "memory_id": memory.get("memory_id")})

    def _notification(self, student_id: str, subject_id: str | None, confirmed: bool) -> dict[str, Any]:
        trace: list[str] = []
        subject = self._tool(get_subject_attendance, trace, student_id=student_id, subject_id=subject_id or "DBMS")
        message = f"Recovery reminder: {subject['course_name']} is at {subject['attendance_percentage']}%. Attend the next scheduled class."
        if not confirmed:
            return self._base(student_id, "notification", "A high-priority recovery reminder is ready, but I need your confirmation before saving it.", "Notification requires explicit student confirmation.", trace, goal_status="NEEDS_CONFIRMATION", evidence=[{"subject": subject["course_name"], "percentage": subject["attendance_percentage"]}], action={"type": "NOTIFICATION", "status": "PENDING_CONFIRMATION", "message": message, "priority": "HIGH"})
        notification = self._tool(save_notification, trace, notification_data={"student_id": student_id, "subject_id": subject["subject_id"], "message": message, "priority": "HIGH"})
        self._tool(save_attendance_event, trace, event_data={"student_id": student_id, "subject_id": subject["subject_id"], "event_type": "AGENT_ACTION", "description": "Student confirmed a high-priority recovery reminder.", "metadata": notification})
        return self._base(student_id, "notification", "Your high-priority recovery reminder has been saved in the in-app notification centre.", "The requested reminder was recorded after explicit confirmation.", trace, evidence=[{"subject": subject["course_name"], "percentage": subject["attendance_percentage"]}], action={"type": "NOTIFICATION_SAVED", "status": "COMPLETED", "notification_id": notification.get("notification_id")})

    def ask(self, student_id: str, message: str, goal: str | None = None, subject_id: str | None = None, confirmed: bool = False) -> dict[str, Any]:
        if goal == "risk":
            return self._risk(student_id)
        if goal == "leave":
            return self._leave(student_id)
        if goal == "recovery":
            return self._recovery(student_id, subject_id)
        if goal == "notification":
            return self._notification(student_id, subject_id, confirmed)
        answer, trace = run_agent(student_id=student_id, user_message=message)
        return self._base(student_id, "freeform", answer, "The local agent completed a tool-driven response.", trace)


agent = AttendanceAgent()
