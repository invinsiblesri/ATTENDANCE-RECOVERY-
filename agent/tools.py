from __future__ import annotations

import json
import math
import os
import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

import httpx
from langchain_core.tools import tool

from .models import (
    AttendanceCalculation,
    AttendanceHistoryRecord,
    AttendanceRecord,
    MemoryEvent,
    NotificationResult,
    PolicyResult,
    RecoveryPlan,
    Student,
    Subject,
    TimetableEntry,
)


# These demo adapters are temporary. Member 2 should replace their internals with
# SQLite/repository calls while preserving the tool names and JSON shapes.
_STUDENTS: dict[str, Student] = {
    "S001": Student(
        student_id="S001",
        name="Demo Student",
        email="s001@example.edu",
        department="Computer Science",
        semester=4,
    )
}

_SUBJECTS: dict[str, Subject] = {
    "CS101": Subject(subject_id="CS101", subject_name="Computer Science", minimum_attendance=75.0),
    "DBMS": Subject(subject_id="DBMS", subject_name="Database Management Systems", minimum_attendance=75.0),
    "PY101": Subject(subject_id="PY101", subject_name="Python Programming", minimum_attendance=75.0),
    "JAVA101": Subject(subject_id="JAVA101", subject_name="Java Programming", minimum_attendance=75.0),
    "MATH101": Subject(subject_id="MATH101", subject_name="Engineering Mathematics", minimum_attendance=75.0),
    "OS201": Subject(subject_id="OS201", subject_name="Operating Systems", minimum_attendance=75.0),
    "CN201": Subject(subject_id="CN201", subject_name="Computer Networks", minimum_attendance=75.0),
    "AI201": Subject(subject_id="AI201", subject_name="Artificial Intelligence", minimum_attendance=75.0),
}

# S001 has all eight subjects so the dashboard and get_all_subjects() can be demoed.
_ATTENDANCE: dict[tuple[str, str], AttendanceRecord] = {
    ("S001", "CS101"): AttendanceRecord(student_id="S001", course_id="CS101", course_name="Computer Science", present_classes=12, total_classes=18, attendance_percentage=66.67, last_updated=date.today()),
    ("S001", "DBMS"): AttendanceRecord(student_id="S001", course_id="DBMS", course_name="Database Management Systems", present_classes=36, total_classes=50, attendance_percentage=72.0, last_updated=date.today()),
    ("S001", "PY101"): AttendanceRecord(student_id="S001", course_id="PY101", course_name="Python Programming", present_classes=38, total_classes=45, attendance_percentage=84.44, last_updated=date.today()),
    ("S001", "JAVA101"): AttendanceRecord(student_id="S001", course_id="JAVA101", course_name="Java Programming", present_classes=32, total_classes=40, attendance_percentage=80.0, last_updated=date.today()),
    ("S001", "MATH101"): AttendanceRecord(student_id="S001", course_id="MATH101", course_name="Engineering Mathematics", present_classes=29, total_classes=38, attendance_percentage=76.32, last_updated=date.today()),
    ("S001", "OS201"): AttendanceRecord(student_id="S001", course_id="OS201", course_name="Operating Systems", present_classes=27, total_classes=36, attendance_percentage=75.0, last_updated=date.today()),
    ("S001", "CN201"): AttendanceRecord(student_id="S001", course_id="CN201", course_name="Computer Networks", present_classes=25, total_classes=36, attendance_percentage=69.44, last_updated=date.today()),
    ("S001", "AI201"): AttendanceRecord(student_id="S001", course_id="AI201", course_name="Artificial Intelligence", present_classes=16, total_classes=20, attendance_percentage=80.0, last_updated=date.today()),
}

_TIMETABLE: list[TimetableEntry] = [
    TimetableEntry(course_id="DBMS", course_name="Database Management Systems", class_date=date.today() + timedelta(days=1), start_time=time(9, 0), end_time=time(10, 0), room="B-204"),
    TimetableEntry(course_id="PY101", course_name="Python Programming", class_date=date.today() + timedelta(days=1), start_time=time(10, 0), end_time=time(11, 0), room="A-101"),
    TimetableEntry(course_id="CS101", course_name="Computer Science", class_date=date.today() + timedelta(days=1), start_time=time(11, 0), end_time=time(12, 0), room="B-204"),
    TimetableEntry(course_id="JAVA101", course_name="Java Programming", class_date=date.today() + timedelta(days=2), start_time=time(9, 0), end_time=time(10, 0), room="C-102"),
    TimetableEntry(course_id="CN201", course_name="Computer Networks", class_date=date.today() + timedelta(days=3), start_time=time(12, 0), end_time=time(13, 0), room="C-102"),
    TimetableEntry(course_id="MATH101", course_name="Engineering Mathematics", class_date=date.today() + timedelta(days=4), start_time=time(10, 0), end_time=time(11, 0), room="A-101"),
    TimetableEntry(course_id="OS201", course_name="Operating Systems", class_date=date.today() + timedelta(days=5), start_time=time(11, 0), end_time=time(12, 0), room="B-204"),
    TimetableEntry(course_id="AI201", course_name="Artificial Intelligence", class_date=date.today() + timedelta(days=6), start_time=time(14, 0), end_time=time(15, 0), room="D-301"),
]

_POLICIES: dict[str, PolicyResult] = {
    subject_id: PolicyResult(
        course_id=subject_id,
        minimum_percentage=subject.minimum_attendance,
        maximum_recovery_classes_per_week=subject.weekly_recovery_limit,
        recovery_allowed=True,
        notes=["Leave approval is subject to college policy and the effect on eligibility."],
    )
    for subject_id, subject in _SUBJECTS.items()
}

_POLICY_PASSAGES = [
    {"text": "Students normally require at least 75% attendance to remain eligible for examinations.", "source": "attendance_policy.txt", "score": 0.98},
    {"text": "If attendance falls below the minimum, examination eligibility may be restricted until the student receives an approved exception.", "source": "exam_eligibility.txt", "score": 0.93},
    {"text": "Leave requests should be checked against scheduled classes, attendance impact, and the applicable leave policy before approval.", "source": "leave_policy.txt", "score": 0.91},
]

_MEMORY: dict[str, list[MemoryEvent]] = {"S001": []}


def _json(value: Any) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.dumps(value, indent=2, default=str)


def _parse_day(day: str) -> date:
    normalized = day.strip().lower()
    if normalized == "today":
        return date.today()
    if normalized == "tomorrow":
        return date.today() + timedelta(days=1)
    if normalized in {"week", "this week", "next 7 days"}:
        return date.today()
    try:
        return date.fromisoformat(day)
    except ValueError:
        return date.today() + timedelta(days=1)


def _calculate(attended: int, conducted: int, target: float) -> dict[str, Any]:
    target = max(0.0, min(float(target), 100.0))
    current = (attended / conducted * 100.0) if conducted else 0.0
    if current >= target:
        needed = 0
    elif target >= 100.0:
        needed = 0
    else:
        needed = max(0, math.ceil(((target / 100.0) * conducted - attended) / (1.0 - target / 100.0)))
    projected = ((attended + needed) / (conducted + needed) * 100.0) if conducted + needed else 0.0
    return {
        "attended": attended,
        "conducted": conducted,
        "current_percentage": round(current, 2),
        "target_percentage": target,
        "required_additional_classes": needed,
        "projected_percentage": round(projected, 2),
        "mathematically_possible": current >= target or target < 100.0,
    }


@tool
def get_student(student_id: str) -> str:
    """Get the profile details for one student."""
    student = _STUDENTS.get(student_id)
    return _json(student) if student else _json({"error": "Student not found", "student_id": student_id})


@tool
def get_all_subjects() -> str:
    """Get all subjects available for the student's attendance dashboard."""
    return _json({"subjects": [subject.model_dump(mode="json") for subject in _SUBJECTS.values()]})


@tool
def get_attendance(student_id: str) -> str:
    """Get attendance for all subjects belonging to a student."""
    records = [record for (sid, _), record in _ATTENDANCE.items() if sid == student_id]
    if not records:
        return _json({"error": "No attendance records found", "student_id": student_id})
    return _json({"student_id": student_id, "records": [record.model_dump(mode="json") for record in records]})


@tool
def get_subject_attendance(student_id: str, subject_id: str) -> str:
    """Get attendance for one student and one subject."""
    record = _ATTENDANCE.get((student_id, subject_id))
    return _json(record) if record else _json({"error": "Subject attendance not found", "student_id": student_id, "subject_id": subject_id})


@tool
def get_attendance_history(student_id: str, subject_id: str) -> str:
    """Get period-wise attendance history for one subject."""
    record = _ATTENDANCE.get((student_id, subject_id))
    if not record:
        return _json({"error": "Subject attendance not found", "student_id": student_id, "subject_id": subject_id})
    periods = [("Period 1", 0.80), ("Period 2", 0.90), ("Period 3", 1.00)]
    history = []
    for label, ratio in periods:
        conducted = max(1, round(record.total_classes / 3))
        attended = min(conducted, round(record.present_classes / 3 * ratio))
        history.append(AttendanceHistoryRecord(student_id=student_id, subject_id=subject_id, period=label, conducted=conducted, attended=attended, percentage=round(attended / conducted * 100, 2)))
    return _json({"student_id": student_id, "subject_id": subject_id, "history": [item.model_dump(mode="json") for item in history]})


@tool
def get_timetable(student_id: str, day: str = "tomorrow") -> str:
    """Get classes for a student on today, tomorrow, an ISO date, or a week."""
    requested_day = _parse_day(day)
    if day.strip().lower() in {"week", "this week", "next 7 days"}:
        end_day = date.today() + timedelta(days=7)
        entries = [entry for entry in _TIMETABLE if date.today() <= entry.class_date <= end_day]
    else:
        entries = [entry for entry in _TIMETABLE if entry.class_date == requested_day]
    return _json({"student_id": student_id, "day": day, "classes": [entry.model_dump(mode="json") for entry in entries]})


@tool
def get_upcoming_classes(student_id: str, day: str = "week") -> str:
    """Get upcoming classes for a student, for a requested day or the next seven days."""
    return get_timetable.invoke({"student_id": student_id, "day": day})


@tool
def calculate_attendance(student_id: str, subject_id: str) -> str:
    """Calculate the current attendance percentage for one student and subject."""
    record = _ATTENDANCE.get((student_id, subject_id))
    if not record:
        return _json({"error": "Subject attendance not found", "student_id": student_id, "subject_id": subject_id})
    result = _calculate(record.present_classes, record.total_classes, _POLICIES[subject_id].minimum_percentage)
    return _json({"student_id": student_id, "subject_id": subject_id, **result})


@tool
def calculate_recovery(attended: int, conducted: int, target: float = 75.0) -> str:
    """Calculate the exact number of future attended classes required to reach a target percentage."""
    if attended < 0 or conducted < 0 or attended > conducted:
        return _json({"error": "Invalid attendance values"})
    return _json(_calculate(attended, conducted, target))


@tool
def search_attendance_policy(question: str, subject_id: str | None = None) -> str:
    """Retrieve relevant attendance policy passages with source names for the final answer."""
    policy = _POLICIES.get(subject_id) if subject_id else None
    return _json({"question": question, "policy": policy.model_dump(mode="json") if policy else None, "results": _POLICY_PASSAGES})


@tool
def save_attendance_event(event_data: dict[str, Any]) -> str:
    """Store an attendance-related event in the memory adapter."""
    student_id = str(event_data.get("student_id", ""))
    if not student_id:
        return _json({"error": "student_id is required"})
    event = MemoryEvent(memory_id=f"M-{uuid.uuid4().hex[:10]}", student_id=student_id, event_type=str(event_data.get("event_type", "attendance_event")), payload=event_data, created_at=datetime.now(timezone.utc).isoformat())
    _MEMORY.setdefault(student_id, []).append(event)
    return _json({"status": "saved", "event": event})


@tool
def get_attendance_memory(student_id: str) -> str:
    """Retrieve recent attendance-related memory for a student."""
    events = _MEMORY.get(student_id, [])[-8:]
    return _json({"student_id": student_id, "events": [event.model_dump(mode="json") for event in events]})


@tool
def save_notification(notification_data: dict[str, Any]) -> str:
    """Persist an in-app notification through Member 4's notification service or local fallback."""
    student_id = str(notification_data.get("student_id", ""))
    message = str(notification_data.get("message", ""))
    priority = str(notification_data.get("priority", "MEDIUM")).upper()
    notification_url = os.getenv("NOTIFICATION_SERVICE_URL")
    if notification_url:
        try:
            response = httpx.post(f"{notification_url.rstrip('/')}/notifications", json={"student_id": student_id, "message": message, "priority": priority}, timeout=5.0)
            response.raise_for_status()
            return response.text
        except httpx.HTTPError as exc:
            return _json({"error": "Notification service unavailable", "detail": str(exc)})
    notification = NotificationResult(notification_id=f"N-{uuid.uuid4().hex[:10]}", student_id=student_id, priority=priority if priority in {"LOW", "MEDIUM", "HIGH"} else "MEDIUM", status="QUEUED", message=message)
    return _json(notification)


@tool
def create_recovery_plan(student_id: str, subject_id: str, target_percentage: float = 75.0) -> str:
    """Create a constrained recovery plan using subject attendance, policy, and upcoming classes."""
    record = _ATTENDANCE.get((student_id, subject_id))
    policy = _POLICIES.get(subject_id)
    if not record or not policy:
        return _json({"error": "Attendance or policy not found", "student_id": student_id, "subject_id": subject_id})
    calculation = _calculate(record.present_classes, record.total_classes, target_percentage)
    upcoming = [entry for entry in _TIMETABLE if entry.course_id == subject_id and entry.class_date >= date.today()]
    recommended = upcoming[: min(calculation["required_additional_classes"], policy.maximum_recovery_classes_per_week)]
    warnings = list(policy.notes)
    if calculation["required_additional_classes"] > policy.maximum_recovery_classes_per_week:
        warnings.append("The recommendation is capped by the weekly recovery policy limit.")
    if calculation["required_additional_classes"] > len(upcoming):
        warnings.append("There are not enough scheduled upcoming classes to recover immediately.")
    plan = RecoveryPlan(student_id=student_id, course_id=subject_id, course_name=record.course_name, current_percentage=calculation["current_percentage"], target_percentage=target_percentage, additional_classes_needed=calculation["required_additional_classes"], recommended_classes=recommended, weekly_limit=policy.maximum_recovery_classes_per_week, recovery_allowed=policy.recovery_allowed, warnings=warnings)
    return _json(plan)


# Backward-compatible aliases for the first implementation.
@tool
def check_policy(course_id: str, question: str = "What is the attendance policy?") -> str:
    """Backward-compatible wrapper around search_attendance_policy."""
    return search_attendance_policy.invoke({"question": question, "subject_id": course_id})


@tool
def trigger_notification(student_id: str, message: str, priority: str = "MEDIUM") -> str:
    """Backward-compatible wrapper around save_notification."""
    return save_notification.invoke({"student_id": student_id, "message": message, "priority": priority})


TOOLS = [
    get_student,
    get_all_subjects,
    get_attendance,
    get_subject_attendance,
    get_attendance_history,
    get_timetable,
    get_upcoming_classes,
    calculate_attendance,
    calculate_recovery,
    search_attendance_policy,
    save_attendance_event,
    get_attendance_memory,
    save_notification,
    create_recovery_plan,
    check_policy,
    trigger_notification,
]

TOOL_MAP = {tool.name: tool for tool in TOOLS}
