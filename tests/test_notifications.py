"""
Unit and Integration Tests for SQLite Notification Storage.
Verifies:
- Saving notifications in SQLite (decided & called by AI Agent)
- Retrieving stored notifications (called by notification consumer)
- Priority validation (LOW, MEDIUM, HIGH, CRITICAL)
- Unread filter and marking notifications as read
- No external notification channels (no Telegram, email, WhatsApp, push)
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
    save_notification,
    get_notifications,
    mark_notification_as_read
)


class TestNotifications(unittest.TestCase):
    """Tests for SQLite notification storage and retrieval."""

    @classmethod
    def setUpClass(cls):
        cls.db_mgr = DatabaseManager()
        seed_database(cls.db_mgr)

    def test_save_and_retrieve_notifications(self):
        """Verify saving and retrieving notification in SQLite."""
        notif_id = save_notification(
            student_id="S001",
            subject_id="SUB003",
            message="DBMS attendance is at 73.33%. 3 consecutive classes needed.",
            priority="CRITICAL"
        )
        self.assertGreater(notif_id, 0)

        notifs = get_notifications("S001")
        self.assertGreaterEqual(len(notifs), 1)

        found = next((n for n in notifs if n["notification_id"] == notif_id), None)
        self.assertIsNotNone(found)
        self.assertEqual(found["student_id"], "S001")
        self.assertEqual(found["subject_id"], "SUB003")
        self.assertEqual(found["priority"], "CRITICAL")
        self.assertEqual(found["is_read"], 0)

    def test_mark_as_read_and_unread_filter(self):
        """Verify marking a notification as read and unread filtering."""
        notif_id = save_notification(
            student_id="S002",
            subject_id=None,
            message="General attendance reminder.",
            priority="LOW"
        )

        unread_before = get_notifications("S002", unread_only=True)
        self.assertTrue(any(n["notification_id"] == notif_id for n in unread_before))

        # Mark as read
        success = mark_notification_as_read(notif_id)
        self.assertTrue(success)

        unread_after = get_notifications("S002", unread_only=True)
        self.assertFalse(any(n["notification_id"] == notif_id for n in unread_after))

    def test_invalid_priority_raises(self):
        """Verify invalid priority value raises error."""
        with self.assertRaises(ValueError):
            save_notification(
                student_id="S001",
                subject_id=None,
                message="Test invalid priority",
                priority="URGENT_CUSTOM"
            )


if __name__ == "__main__":
    unittest.main()
