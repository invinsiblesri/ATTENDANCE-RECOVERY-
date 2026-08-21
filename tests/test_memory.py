"""
Unit and Integration Tests for Persistent Attendance Memory.
Verifies:
- Saving only attendance-related events
- Event types: WARNING, STATUS_CHANGE, RECOVERY_PLAN, AGENT_ACTION, IMPORTANT_EVENT
- Rejecting arbitrary/invalid event types
- Student-level and subject-level retrieval
- JSON metadata serialization/deserialization
"""

import unittest
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.connection import DatabaseManager
from database.seed import seed_database
from api.attendance_api import (
    save_attendance_event,
    get_attendance_memory,
    get_subject_memory
)


class TestAttendanceMemory(unittest.TestCase):
    """Tests for persistent attendance-only memory store."""

    @classmethod
    def setUpClass(cls):
        cls.db_mgr = DatabaseManager()
        seed_database(cls.db_mgr)

    def test_save_and_retrieve_student_memory(self):
        """Verify saving and retrieving attendance memory for a student."""
        mem_id = save_attendance_event(
            student_id="S001",
            subject_id="SUB003",
            event_type="RECOVERY_PLAN",
            description="Agreed to attend next 5 consecutive DBMS lectures.",
            metadata={"target_classes": 5, "subject": "DBMS"}
        )
        self.assertGreater(mem_id, 0)

        events = get_attendance_memory("S001", limit=10)
        self.assertGreaterEqual(len(events), 1)

        # Find the inserted event
        found = next((e for e in events if e["memory_id"] == mem_id), None)
        self.assertIsNotNone(found)
        self.assertEqual(found["student_id"], "S001")
        self.assertEqual(found["subject_id"], "SUB003")
        self.assertEqual(found["event_type"], "RECOVERY_PLAN")
        self.assertEqual(found["description"], "Agreed to attend next 5 consecutive DBMS lectures.")
        self.assertIsInstance(found["metadata"], dict)
        self.assertEqual(found["metadata"]["target_classes"], 5)

    def test_get_subject_memory(self):
        """Verify querying memory filtered by student and subject."""
        save_attendance_event(
            student_id="S001",
            subject_id="SUB007",
            event_type="WARNING",
            description="AI subject attendance dropped to 73.33%.",
            metadata={"subject": "Artificial Intelligence"}
        )

        ai_events = get_subject_memory(student_id="S001", subject_id="SUB007")
        self.assertGreaterEqual(len(ai_events), 1)
        for ev in ai_events:
            self.assertEqual(ev["subject_id"], "SUB007")
            self.assertEqual(ev["student_id"], "S001")

    def test_all_valid_event_types(self):
        """Verify all supported attendance event types can be stored."""
        valid_types = ["WARNING", "STATUS_CHANGE", "RECOVERY_PLAN", "AGENT_ACTION", "IMPORTANT_EVENT"]
        for ev_type in valid_types:
            mem_id = save_attendance_event(
                student_id="S002",
                subject_id=None,
                event_type=ev_type,
                description=f"Test event for {ev_type}",
                metadata={"test": True}
            )
            self.assertGreater(mem_id, 0)

    def test_invalid_event_type_raises(self):
        """Verify arbitrary conversation/invalid events are rejected."""
        with self.assertRaises(ValueError):
            save_attendance_event(
                student_id="S001",
                subject_id=None,
                event_type="CHAT_CONVERSATION",
                description="Random conversational chat"
            )


if __name__ == "__main__":
    unittest.main()
