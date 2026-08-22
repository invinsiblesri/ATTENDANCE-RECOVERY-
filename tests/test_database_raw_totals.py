"""
Unit and Integration Tests for Raw Database Aggregation.
Verifies contract with Member 1 (Calculator Agent):
- Module provides raw attendance totals without calculating percentages or recovery
- Student and subject queries
- Edge cases and error handling
"""

import unittest
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.connection import DatabaseManager
from database.seed import seed_database
from database.repository import AttendanceRepository
from api.attendance_api import (
    get_student,
    get_all_students,
    get_all_subjects,
    get_subject,
    get_raw_attendance_summary,
    get_raw_subject_attendance
)


class TestDatabaseRawTotals(unittest.TestCase):
    """Tests raw totals retrieval for Member 1 Calculator Agent."""

    @classmethod
    def setUpClass(cls):
        # Use seeded database
        cls.db_mgr = DatabaseManager()
        seed_database(cls.db_mgr)
        cls.repo = AttendanceRepository(cls.db_mgr)

    def test_get_all_students_count(self):
        """Verify exactly 20 students exist in the system."""
        students = get_all_students()
        self.assertEqual(len(students), 20)
        student_ids = [s["student_id"] for s in students]
        self.assertIn("S001", student_ids)
        self.assertIn("S020", student_ids)

    def test_get_all_subjects_count(self):
        """Verify exactly 8 equal subjects exist."""
        subjects = get_all_subjects()
        self.assertEqual(len(subjects), 8)
        subject_names = {s["subject_name"] for s in subjects}
        expected = {
            "Python", "Java", "DBMS", "Computer Networks",
            "Software Engineering", "Mathematics",
            "Artificial Intelligence", "Operating Systems"
        }
        self.assertEqual(subject_names, expected)

    def test_get_student_details(self):
        """Verify student metadata retrieval."""
        student = get_student("S001")
        self.assertIsNotNone(student)
        self.assertEqual(student["student_id"], "S001")
        self.assertEqual(student["name"], "Aarav Sharma")
        self.assertEqual(student["department"], "Computer Science & Engineering")
        self.assertEqual(student["year"], 3)
        self.assertEqual(student["semester"], 5)

    def test_get_subject_details(self):
        """Verify individual subject retrieval."""
        subj = get_subject("SUB003")
        self.assertIsNotNone(subj)
        self.assertEqual(subj["subject_id"], "SUB003")
        self.assertEqual(subj["subject_code"], "CS303")
        self.assertEqual(subj["subject_name"], "DBMS")

    def test_raw_attendance_summary_structure(self):
        """
        Verify raw attendance summary returns raw counts for Member 1
        without calculating percentages.
        """
        summary = get_raw_attendance_summary("S001")
        self.assertEqual(summary["student_id"], "S001")
        self.assertIn("total_conducted", summary)
        self.assertIn("total_attended", summary)
        self.assertIn("total_absent", summary)
        self.assertIn("subjects", summary)

        # Verify mathematical consistency
        self.assertEqual(
            summary["total_conducted"],
            summary["total_attended"] + summary["total_absent"]
        )
        self.assertEqual(len(summary["subjects"]), 8)

        for s_id, s_data in summary["subjects"].items():
            self.assertIn("conducted", s_data)
            self.assertIn("attended", s_data)
            self.assertIn("absent", s_data)
            self.assertEqual(
                s_data["conducted"],
                s_data["attended"] + s_data["absent"]
            )

    def test_raw_subject_attendance(self):
        """Verify raw counts for single subject."""
        raw_dbms = get_raw_subject_attendance("S001", "SUB003")
        self.assertEqual(raw_dbms["student_id"], "S001")
        self.assertEqual(raw_dbms["subject_id"], "SUB003")
        self.assertEqual(raw_dbms["subject_name"], "DBMS")
        self.assertEqual(raw_dbms["conducted"], 30)
        self.assertEqual(raw_dbms["attended"], 22)
        self.assertEqual(raw_dbms["absent"], 8)

    def test_nonexistent_student_raises(self):
        """Verify appropriate error on invalid student lookup."""
        with self.assertRaises(ValueError):
            get_raw_attendance_summary("NON_EXISTENT_ID")


if __name__ == "__main__":
    unittest.main()
