"""
Persistent Attendance-Only Memory Module.
Records attendance-related events:
- WARNING: Attendance warnings issued
- STATUS_CHANGE: Attendance status changes
- RECOVERY_PLAN: Attendance recovery plans agreed/proposed
- AGENT_ACTION: Attendance-related agent actions
- IMPORTANT_EVENT: Important events like approved leaves or medical submissions

Does NOT store arbitrary conversation history.
"""

from typing import Optional, List, Dict, Any
from database.repository import AttendanceRepository
from database.connection import DatabaseManager, db_manager


class AttendanceMemoryStore:
    """Interface for managing persistent attendance-only memory."""

    VALID_EVENT_TYPES = ("WARNING", "STATUS_CHANGE", "RECOVERY_PLAN", "AGENT_ACTION", "IMPORTANT_EVENT")

    def __init__(self, db_manager_instance: Optional[DatabaseManager] = None):
        self.repo = AttendanceRepository(db_manager_instance or db_manager)
        self.db = db_manager_instance or db_manager

    def save_event(
        self,
        student_id: str,
        subject_id: Optional[str],
        event_type: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Persists a structured attendance event to memory.
        """
        if event_type not in self.VALID_EVENT_TYPES:
            raise ValueError(f"Invalid event_type '{event_type}'. Must be one of {self.VALID_EVENT_TYPES}.")
        return self.repo.save_attendance_event(
            student_id=student_id,
            subject_id=subject_id,
            event_type=event_type,
            description=description,
            metadata=metadata
        )

    def get_student_memory(self, student_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieves all attendance memory events for a student.
        """
        return self.repo.get_attendance_memory(student_id=student_id, limit=limit)

    def get_subject_memory(self, student_id: str, subject_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieves attendance memory events filtered by student and subject.
        """
        return self.repo.get_subject_memory(student_id=student_id, subject_id=subject_id, limit=limit)

    def clear_memory(self, student_id: Optional[str] = None) -> int:
        """
        Clears attendance memory for a student, or all students if None.
        Used primarily for test resets.
        """
        with self.db.connection() as conn:
            cursor = conn.cursor()
            if student_id:
                cursor.execute("DELETE FROM attendance_memory WHERE student_id = ?", (student_id,))
            else:
                cursor.execute("DELETE FROM attendance_memory")
            return cursor.rowcount


# Default global instance
memory_store = AttendanceMemoryStore()


def save_attendance_event(
    student_id: str,
    subject_id: Optional[str],
    event_type: str,
    description: str,
    metadata: Optional[Dict[str, Any]] = None
) -> int:
    """Convenience function to save an attendance memory event."""
    return memory_store.save_event(
        student_id=student_id,
        subject_id=subject_id,
        event_type=event_type,
        description=description,
        metadata=metadata
    )


def get_attendance_memory(student_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Convenience function to retrieve attendance memory for a student."""
    return memory_store.get_student_memory(student_id=student_id, limit=limit)


def get_subject_memory(student_id: str, subject_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Convenience function to retrieve attendance memory for a subject."""
    return memory_store.get_subject_memory(student_id=student_id, subject_id=subject_id, limit=limit)


def clear_attendance_memory(student_id: Optional[str] = None) -> int:
    """Convenience function to clear memory."""
    return memory_store.clear_memory(student_id=student_id)
