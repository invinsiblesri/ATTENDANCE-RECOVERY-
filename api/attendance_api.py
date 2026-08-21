"""
Public Facade API for AI Attendance Recovery Agent.
Designed for immediate import and use by AI Agent team members.

Exposes clean functions for:
- Student & Subject metadata
- Raw Attendance Aggregation (for Member 1 Calculator Agent)
- Timetable & Upcoming classes (Monday-Friday, 8 periods/day)
- Period-Wise Attendance History
- Leave record management
- Persistent Attendance Memory
- In-Database Notification management
- ChromaDB Policy RAG Search
"""

from typing import Optional, List, Dict, Any
from database.repository import AttendanceRepository
from database.connection import db_manager
from memory.attendance_memory import memory_store
from rag.service import search_attendance_policy as _search_policy

_default_repo = AttendanceRepository(db_manager)


# -----------------------------------------------------------------------------
# 1. Student Operations
# -----------------------------------------------------------------------------
def get_student(student_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves student metadata by student_id (e.g. 'S001').
    Returns dict: {'student_id', 'name', 'department', 'year', 'semester'} or None.
    """
    return _default_repo.get_student(student_id)


def get_all_students() -> List[Dict[str, Any]]:
    """
    Retrieves list of all 20 registered students.
    """
    return _default_repo.get_all_students()


# -----------------------------------------------------------------------------
# 2. Subject Operations (8 Equal Subjects)
# -----------------------------------------------------------------------------
def get_subject(subject_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves subject details by subject_id (e.g. 'SUB001').
    Returns dict: {'subject_id', 'subject_code', 'subject_name'} or None.
    """
    return _default_repo.get_subject(subject_id)


def get_all_subjects() -> List[Dict[str, Any]]:
    """
    Retrieves list of all 8 curriculum subjects.
    All subjects have equal weight; no priority or coefficient.
    """
    return _default_repo.get_all_subjects()


# -----------------------------------------------------------------------------
# 3. Raw Data Provision for Member 1 (Calculator Agent)
# -----------------------------------------------------------------------------
def get_raw_attendance_summary(student_id: str) -> Dict[str, Any]:
    """
    Retrieves uncalculated raw attendance counts (conducted, attended, absent)
    aggregated overall and broken down per subject for consumption by Member 1's Calculator Agent.
    
    Does NOT perform percentage or recovery calculations.
    """
    return _default_repo.get_raw_attendance_summary(student_id)


def get_raw_subject_attendance(student_id: str, subject_id: str) -> Dict[str, Any]:
    """
    Retrieves raw attendance counts for a single subject for a student.
    Returns: {'student_id', 'subject_id', 'subject_code', 'subject_name', 'conducted', 'attended', 'absent'}
    """
    return _default_repo.get_raw_subject_attendance(student_id, subject_id)


def get_attendance_history(
    student_id: str,
    subject_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieves chronological period-by-period class attendance records for a student.
    """
    return _default_repo.get_attendance_history(
        student_id=student_id,
        subject_id=subject_id,
        start_date=start_date,
        end_date=end_date
    )


def record_period_attendance(
    student_id: str,
    subject_id: str,
    date: str,
    period_number: int,
    status: str
) -> int:
    """
    Records or updates a class-wise attendance record.
    Status must be 'Present' or 'Absent'.
    """
    return _default_repo.record_period_attendance(
        student_id=student_id,
        subject_id=subject_id,
        date=date,
        period_number=period_number,
        status=status
    )


# -----------------------------------------------------------------------------
# 4. Timetable Operations (Monday to Friday, 8 Periods/Day)
# -----------------------------------------------------------------------------
def get_timetable(day_of_week: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves timetable slots. If day_of_week is provided ('Monday'..'Friday'), filters by day.
    """
    return _default_repo.get_timetable(day_of_week=day_of_week)


def get_upcoming_classes(day_of_week: str, current_period: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Retrieves classes scheduled for a given day remaining after current_period.
    """
    return _default_repo.get_upcoming_classes(day_of_week=day_of_week, current_period=current_period)


# -----------------------------------------------------------------------------
# 5. Leave Records
# -----------------------------------------------------------------------------
def get_leave_records(student_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves leave records for a student.
    """
    return _default_repo.get_leave_records(student_id)


def apply_leave(student_id: str, date: str, reason: str, status: str = "Pending") -> int:
    """
    Submits a leave record in SQLite.
    """
    return _default_repo.apply_leave(student_id=student_id, date=date, reason=reason, status=status)


# -----------------------------------------------------------------------------
# 6. Persistent Attendance Memory
# -----------------------------------------------------------------------------
def save_attendance_event(
    student_id: str,
    subject_id: Optional[str],
    event_type: str,
    description: str,
    metadata: Optional[Dict[str, Any]] = None
) -> int:
    """
    Saves an attendance-only event in persistent memory.
    Valid event_type: 'WARNING', 'STATUS_CHANGE', 'RECOVERY_PLAN', 'AGENT_ACTION', 'IMPORTANT_EVENT'.
    """
    return memory_store.save_event(
        student_id=student_id,
        subject_id=subject_id,
        event_type=event_type,
        description=description,
        metadata=metadata
    )


def get_attendance_memory(student_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieves persistent attendance memory events for a student.
    """
    return memory_store.get_student_memory(student_id=student_id, limit=limit)


def get_subject_memory(student_id: str, subject_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieves persistent attendance memory events for a specific subject.
    """
    return memory_store.get_subject_memory(student_id=student_id, subject_id=subject_id, limit=limit)


# -----------------------------------------------------------------------------
# 7. Notifications (SQLite Storage & Retrieval)
# -----------------------------------------------------------------------------
def save_notification(
    student_id: str,
    subject_id: Optional[str],
    message: str,
    priority: str = "MEDIUM"
) -> int:
    """
    Persists a notification in SQLite. Triggered when the AI Agent decides to issue one.
    Priority: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'.
    """
    return _default_repo.save_notification(
        student_id=student_id,
        subject_id=subject_id,
        message=message,
        priority=priority
    )


def get_notifications(student_id: str, unread_only: bool = False) -> List[Dict[str, Any]]:
    """
    Retrieves notifications stored for a student.
    """
    return _default_repo.get_notifications(student_id=student_id, unread_only=unread_only)


def mark_notification_as_read(notification_id: int) -> bool:
    """
    Marks a stored notification as read in SQLite.
    """
    return _default_repo.mark_notification_as_read(notification_id)


# -----------------------------------------------------------------------------
# 8. ChromaDB RAG Policy Search
# -----------------------------------------------------------------------------
def search_attendance_policy(query: str, n_results: int = 3) -> List[Dict[str, Any]]:
    """
    Queries the local ChromaDB vector store for demo attendance policy documentation.
    """
    return _search_policy(query=query, n_results=n_results)
