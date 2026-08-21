import json

from agent.tools import (
    calculate_attendance,
    calculate_recovery,
    create_recovery_plan,
    get_all_subjects,
    get_attendance,
    get_attendance_history,
    get_attendance_memory,
    get_student,
    get_subject_attendance,
    get_timetable,
    get_upcoming_classes,
    save_attendance_event,
    save_notification,
    search_attendance_policy,
)


def test_get_student():
    result = json.loads(get_student.invoke({"student_id": "S001"}))
    assert result["student_id"] == "S001"


def test_get_all_eight_subjects():
    result = json.loads(get_all_subjects.invoke({}))
    assert len(result["subjects"]) == 8


def test_get_attendance_returns_all_subjects():
    result = json.loads(get_attendance.invoke({"student_id": "S001"}))
    assert len(result["records"]) == 8


def test_subject_and_history_tools():
    subject = json.loads(get_subject_attendance.invoke({"student_id": "S001", "subject_id": "DBMS"}))
    history = json.loads(get_attendance_history.invoke({"student_id": "S001", "subject_id": "DBMS"}))
    assert subject["present_classes"] == 22
    assert len(history["history"]) == 30


def test_timetable_and_upcoming_classes():
    tomorrow = json.loads(get_timetable.invoke({"student_id": "S001", "day": "tomorrow"}))
    upcoming = json.loads(get_upcoming_classes.invoke({"student_id": "S001", "day": "week"}))
    assert tomorrow["classes"]
    assert upcoming["classes"]


def test_calculate_attendance_and_recovery_are_deterministic():
    attendance = json.loads(calculate_attendance.invoke({"student_id": "S001", "subject_id": "DBMS"}))
    recovery = json.loads(calculate_recovery.invoke({"attended": 22, "conducted": 30, "target": 75}))
    assert attendance["current_percentage"] == 73.33
    assert recovery["required_additional_classes"] == 2
    assert recovery["projected_percentage"] == 75.0


def test_policy_has_sources():
    result = json.loads(search_attendance_policy.invoke({"question": "Can I take leave tomorrow?", "subject_id": "DBMS"}))
    assert result["results"]
    assert result["results"][0]["source"] == "attendance_policy.md"


def test_memory_save_and_retrieve():
    saved = json.loads(save_attendance_event.invoke({"event_data": {"student_id": "S001", "event_type": "warning", "subject_id": "DBMS"}}))
    memory = json.loads(get_attendance_memory.invoke({"student_id": "S001"}))
    assert saved["status"] == "saved"
    assert memory["events"]


def test_recovery_plan_and_notification():
    plan = json.loads(create_recovery_plan.invoke({"student_id": "S001", "subject_id": "DBMS", "target_percentage": 75}))
    notification = json.loads(save_notification.invoke({"notification_data": {"student_id": "S001", "message": "DBMS reminder", "priority": "HIGH"}}))
    assert plan["additional_classes_needed"] == 2
    assert notification["status"] == "QUEUED"
    assert notification["priority"] == "HIGH"
