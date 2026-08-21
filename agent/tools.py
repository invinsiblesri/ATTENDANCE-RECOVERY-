"""Trusted tool layer for the Attendance Recovery Agent.

Every tool reads or writes through Member 2's public facade. The model may choose a
tool, but deterministic Python owns percentage arithmetic and all database access.
"""
from __future__ import annotations

import json
import math
from datetime import date, timedelta
from typing import Any

from langchain_core.tools import tool

from api import attendance_api as backend

TARGET_ATTENDANCE = 75.0
WEEKLY_RECOVERY_LIMIT = 3
VALID_EVENT_TYPES = {"WARNING", "STATUS_CHANGE", "RECOVERY_PLAN", "AGENT_ACTION", "IMPORTANT_EVENT"}
VALID_PRIORITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def _json(value: Any) -> str:
    return json.dumps(value, indent=2, default=str)


def _error(message: str, **details: Any) -> str:
    return _json({"error": message, **details})


def _subjects() -> list[dict[str, Any]]:
    return backend.get_all_subjects()


def _subject(identifier: str | None) -> dict[str, Any] | None:
    if not identifier:
        return None
    query = str(identifier).strip().lower()
    for subject in _subjects():
        identifiers = {
            str(subject.get("subject_id", "")).lower(),
            str(subject.get("subject_code", "")).lower(),
            str(subject.get("subject_name", "")).lower(),
        }
        if query in identifiers:
            return subject
    return None


def _calculate(attended: int, conducted: int, target: float = TARGET_ATTENDANCE) -> dict[str, Any]:
    target = max(0.0, min(float(target), 100.0))
    current = round((attended / conducted * 100.0), 2) if conducted else 0.0
    if current >= target:
        needed = 0
    elif target >= 100.0:
        needed = 0
    else:
        needed = max(0, math.ceil(((target / 100.0) * conducted - attended) / (1.0 - target / 100.0)))
    projected = round(((attended + needed) / (conducted + needed) * 100.0), 2) if conducted + needed else 0.0
    return {
        "attended": attended,
        "conducted": conducted,
        "current_percentage": current,
        "target_percentage": target,
        "required_additional_classes": needed,
        "projected_percentage": projected,
        "mathematically_possible": current >= target or target < 100.0,
    }


def _academic_days(day: str) -> list[str]:
    normalized = day.strip().lower()
    if normalized in {"week", "this week", "next 7 days"}:
        return ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    if normalized == "today":
        requested = date.today()
    elif normalized == "tomorrow":
        requested = date.today() + timedelta(days=1)
    else:
        try:
            requested = date.fromisoformat(day)
        except ValueError:
            requested = None
    if requested is not None:
        while requested.weekday() > 4:
            requested += timedelta(days=1)
        return [requested.strftime("%A")]
    for weekday in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
        if normalized == weekday.lower():
            return [weekday]
    return ["Monday"]


def _timetable_payload(student_id: str, day: str) -> dict[str, Any]:
    classes: list[dict[str, Any]] = []
    for weekday in _academic_days(day):
        for entry in backend.get_timetable(weekday):
            classes.append({**entry, "requested_day": weekday})
    return {"student_id": student_id, "day": day, "classes": classes}


@tool
def get_student(student_id: str) -> str:
    """Get trusted student profile details from SQLite."""
    student = backend.get_student(student_id)
    return _json(student) if student else _error("Student not found", student_id=student_id)


@tool
def get_all_subjects() -> str:
    """Get all eight curriculum subjects from SQLite."""
    return _json({"subjects": _subjects()})


@tool
def get_attendance(student_id: str) -> str:
    """Get attendance across every subject using raw SQLite totals."""
    try:
        summary = backend.get_raw_attendance_summary(student_id)
    except ValueError:
        return _error("No attendance records found", student_id=student_id)
    subject_index = {subject["subject_id"]: subject for subject in _subjects()}
    records = []
    for subject_id, raw in summary.get("subjects", {}).items():
        subject = subject_index.get(subject_id, {})
        conducted = int(raw.get("conducted", 0))
        attended = int(raw.get("attended", 0))
        records.append({
            "student_id": student_id,
            "course_id": subject_id,
            "course_code": subject.get("subject_code", subject_id),
            "course_name": subject.get("subject_name", subject_id),
            "present_classes": attended,
            "total_classes": conducted,
            "attendance_percentage": round((attended / conducted * 100.0), 2) if conducted else 0.0,
        })
    return _json({"student_id": student_id, "records": records, "overall": _calculate(int(summary["total_attended"]), int(summary["total_conducted"]))})


@tool
def get_subject_attendance(student_id: str, subject_id: str) -> str:
    """Get trusted raw attendance for one subject. Accepts ID, code, or name."""
    subject = _subject(subject_id)
    if not subject:
        return _error("Subject not found", subject_id=subject_id)
    try:
        raw = backend.get_raw_subject_attendance(student_id, subject["subject_id"])
    except ValueError:
        return _error("Subject attendance not found", student_id=student_id, subject_id=subject_id)
    conducted = int(raw["conducted"])
    attended = int(raw["attended"])
    return _json({
        "student_id": student_id,
        "subject_id": subject["subject_id"],
        "subject_code": subject.get("subject_code"),
        "course_name": raw.get("subject_name", subject.get("subject_name")),
        "present_classes": attended,
        "total_classes": conducted,
        "absent_classes": int(raw.get("absent", conducted - attended)),
        "attendance_percentage": round((attended / conducted * 100.0), 2) if conducted else 0.0,
    })


@tool
def get_attendance_history(student_id: str, subject_id: str) -> str:
    """Get real period-by-period attendance history from SQLite."""
    subject = _subject(subject_id)
    if not subject:
        return _error("Subject not found", subject_id=subject_id)
    history = backend.get_attendance_history(student_id, subject["subject_id"])
    return _json({"student_id": student_id, "subject_id": subject["subject_id"], "history": history})


@tool
def get_timetable(student_id: str, day: str = "tomorrow") -> str:
    """Get the trusted shared college timetable for today, tomorrow, a weekday, or a week."""
    return _json(_timetable_payload(student_id, day))


@tool
def get_upcoming_classes(student_id: str, day: str = "week") -> str:
    """Get upcoming classes from the trusted timetable."""
    return _json(_timetable_payload(student_id, day))


@tool
def calculate_attendance(student_id: str, subject_id: str) -> str:
    """Calculate an attendance percentage and recovery requirement deterministically."""
    raw = json.loads(get_subject_attendance.invoke({"student_id": student_id, "subject_id": subject_id}))
    if raw.get("error"):
        return _json(raw)
    calculation = _calculate(int(raw["present_classes"]), int(raw["total_classes"]))
    return _json({"student_id": student_id, "subject_id": raw["subject_id"], **calculation})


@tool
def calculate_recovery(attended: int, conducted: int, target: float = TARGET_ATTENDANCE) -> str:
    """Calculate the exact future attended classes required to reach a target."""
    if attended < 0 or conducted < 0 or attended > conducted:
        return _error("Invalid attendance values")
    return _json(_calculate(attended, conducted, target))


@tool
def search_attendance_policy(question: str, subject_id: str | None = None) -> str:
    """Retrieve relevant local policy evidence through ChromaDB RAG."""
    subject = _subject(subject_id) if subject_id else None
    results = backend.search_attendance_policy(question)
    return _json({"question": question, "subject": subject, "results": results})


@tool
def save_attendance_event(event_data: dict[str, Any]) -> str:
    """Persist an agent action, warning, or recovery plan in attendance memory."""
    student_id = str(event_data.get("student_id", ""))
    if not student_id:
        return _error("student_id is required")
    subject = _subject(event_data.get("subject_id"))
    event_type = str(event_data.get("event_type", "AGENT_ACTION")).upper()
    if event_type not in VALID_EVENT_TYPES:
        event_type = "AGENT_ACTION"
    description = str(event_data.get("description") or event_data.get("message") or "Attendance agent action recorded.")
    memory_id = backend.save_attendance_event(student_id, subject["subject_id"] if subject else None, event_type, description, event_data.get("metadata", event_data))
    return _json({"status": "saved", "memory_id": memory_id, "event_type": event_type})


@tool
def get_attendance_memory(student_id: str) -> str:
    """Retrieve persistent attendance warnings, plans, and past agent actions."""
    return _json({"student_id": student_id, "events": backend.get_attendance_memory(student_id, limit=8)})


@tool
def save_notification(notification_data: dict[str, Any]) -> str:
    """Persist a student-confirmed in-app notification in SQLite."""
    student_id = str(notification_data.get("student_id", ""))
    message = str(notification_data.get("message", ""))
    if not student_id or not message:
        return _error("student_id and message are required")
    subject = _subject(notification_data.get("subject_id"))
    priority = str(notification_data.get("priority", "MEDIUM")).upper()
    if priority not in VALID_PRIORITIES:
        priority = "MEDIUM"
    notification_id = backend.save_notification(student_id, subject["subject_id"] if subject else None, message, priority)
    return _json({"status": "QUEUED", "notification_id": notification_id, "student_id": student_id, "priority": priority, "message": message})


@tool
def create_recovery_plan(student_id: str, subject_id: str, target_percentage: float = TARGET_ATTENDANCE) -> str:
    """Create a constrained recovery plan using real attendance, policy, and timetable facts."""
    raw = json.loads(get_subject_attendance.invoke({"student_id": student_id, "subject_id": subject_id}))
    if raw.get("error"):
        return _json(raw)
    policy = json.loads(search_attendance_policy.invoke({"question": "What attendance recovery rules apply?", "subject_id": raw["subject_id"]}))
    calculation = _calculate(int(raw["present_classes"]), int(raw["total_classes"]), target_percentage)
    weekly_schedule = json.loads(get_upcoming_classes.invoke({"student_id": student_id, "day": "week"}))
    candidates = [entry for entry in weekly_schedule["classes"] if entry.get("subject_id") == raw["subject_id"]]
    recommended = candidates[: min(calculation["required_additional_classes"], WEEKLY_RECOVERY_LIMIT)]
    warnings: list[str] = []
    if calculation["required_additional_classes"] > WEEKLY_RECOVERY_LIMIT:
        warnings.append("The plan prioritizes the next three scheduled classes; continue the same pattern in the following week.")
    if not candidates and calculation["required_additional_classes"]:
        warnings.append("No matching timetable classes were found this week; check the next timetable cycle.")
    return _json({
        "student_id": student_id,
        "subject_id": raw["subject_id"],
        "course_name": raw["course_name"],
        **calculation,
        "additional_classes_needed": calculation["required_additional_classes"],
        "recommended_classes": recommended,
        "weekly_limit": WEEKLY_RECOVERY_LIMIT,
        "policy_sources": [item.get("source") or item.get("document") for item in policy.get("results", [])],
        "warnings": warnings,
    })


@tool
def check_policy(course_id: str, question: str = "What is the attendance policy?") -> str:
    """Backward-compatible wrapper for policy lookup."""
    return search_attendance_policy.invoke({"question": question, "subject_id": course_id})


@tool
def trigger_notification(student_id: str, message: str, priority: str = "MEDIUM") -> str:
    """Backward-compatible wrapper for the persistent notification action."""
    return save_notification.invoke({"notification_data": {"student_id": student_id, "message": message, "priority": priority}})


TOOLS = [
    get_student, get_all_subjects, get_attendance, get_subject_attendance,
    get_attendance_history, get_timetable, get_upcoming_classes,
    calculate_attendance, calculate_recovery, search_attendance_policy,
    save_attendance_event, get_attendance_memory, save_notification,
    create_recovery_plan, check_policy, trigger_notification,
]
TOOL_MAP = {registered_tool.name: registered_tool for registered_tool in TOOLS}
