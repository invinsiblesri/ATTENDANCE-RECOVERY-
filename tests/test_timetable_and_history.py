"""
Unit and Integration Tests for Timetable and Attendance History.
Verifies:
- Monday to Friday timetable (8 periods/day = 40 weekly slots)
- Equal slot distribution (5 slots per subject)
- Upcoming classes filtering
- Period-wise attendance history across 30 days (240 records per student)
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
    get_timetable,
    get_upcoming_classes,
    get_attendance_history,
    record_period_attendance,
    get_leave_records
)


class TestTimetableAndHistory(unittest.TestCase):
    """Tests for timetable schedule and historical period records."""

    @classmethod
    def setUpClass(cls):
        cls.db_mgr = DatabaseManager()
        seed_database(cls.db_mgr)

    def test_full_timetable_slots_count(self):
        """Verify timetable has exactly 40 weekly slots (5 days * 8 periods)."""
        slots = get_timetable()
        self.assertEqual(len(slots), 40)

    def test_timetable_equal_subject_distribution(self):
        """Verify each of the 8 subjects has exactly 5 weekly periods."""
        slots = get_timetable()
        subject_counts = {}
        for slot in slots:
            s_name = slot["subject_name"]
            subject_counts[s_name] = subject_counts.get(s_name, 0) + 1

        self.assertEqual(len(subject_counts), 8)
        for s_name, count in subject_counts.items():
            self.assertEqual(count, 5, f"Subject '{s_name}' should have 5 slots, found {count}")

    def test_daily_timetable_periods(self):
        """Verify each weekday has periods 1 to 8 in order."""
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
            day_slots = get_timetable(day_of_week=day)
            self.assertEqual(len(day_slots), 8, f"{day} should have 8 periods")
            periods = [s["period_number"] for s in day_slots]
            self.assertEqual(periods, [1, 2, 3, 4, 5, 6, 7, 8])

    def test_upcoming_classes_filtering(self):
        """Verify upcoming classes returns only remaining periods."""
        # Remaining after period 5
        upcoming = get_upcoming_classes(day_of_week="Monday", current_period=5)
        self.assertEqual(len(upcoming), 3)
        self.assertEqual([u["period_number"] for u in upcoming], [6, 7, 8])

        # All classes when current_period is None
        all_mon = get_upcoming_classes(day_of_week="Monday", current_period=None)
        self.assertEqual(len(all_mon), 8)

        # After last period (period 8)
        after_last = get_upcoming_classes(day_of_week="Monday", current_period=8)
        self.assertEqual(len(after_last), 0)

    def test_student_history_count(self):
        """Verify 30 days * 8 periods = 240 period-wise records for S001."""
        history = get_attendance_history("S001")
        self.assertEqual(len(history), 240)

    def test_history_filtering_by_subject(self):
        """Verify filtering history by specific subject yields exactly 30 classes."""
        dbms_history = get_attendance_history("S001", subject_id="SUB003")
        self.assertEqual(len(dbms_history), 30)
        for record in dbms_history:
            self.assertEqual(record["subject_id"], "SUB003")
            self.assertIn(record["status"], ["Present", "Absent"])

    def test_history_filtering_by_date(self):
        """Verify date range filtering on attendance history."""
        # 1 week of records (5 days * 8 periods = 40 records)
        week1 = get_attendance_history("S001", start_date="2026-01-05", end_date="2026-01-09")
        self.assertEqual(len(week1), 40)

    def test_record_new_period_attendance(self):
        """Verify inserting or updating an attendance record with clean isolation."""
        test_date = "2099-01-01"
        try:
            row_id = record_period_attendance(
                student_id="S001",
                subject_id="SUB001",
                date=test_date,
                period_number=1,
                status="Present"
            )
            self.assertGreater(row_id, 0)
        finally:
            with self.db_mgr.connection() as conn:
                conn.execute("DELETE FROM attendance_records WHERE date = ?", (test_date,))

    def test_leave_records_retrieval(self):
        """Verify leave records retrieval for student."""
        leaves = get_leave_records("S001")
        self.assertGreaterEqual(len(leaves), 1)
        self.assertEqual(leaves[0]["student_id"], "S001")


if __name__ == "__main__":
    unittest.main()
