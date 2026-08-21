"""
Unit Tests for Primary Demo Student S001 & Cohort Attendance Calibration.
Verifies:
- S001 overall attendance is around 78-79% (exact: 189 / 240 = 78.75%)
- S001 DBMS attendance is ~73-74% (exact: 22 / 30 = 73.33%)
- Subject-wise variation across safe, borderline, and shortage
- Cohort students (S002-S020) distribution
"""

import unittest
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.connection import DatabaseManager
from database.seed import seed_database
from api.attendance_api import get_raw_attendance_summary, get_all_students


class TestDemoStudentS001(unittest.TestCase):
    """Verifies calibration of demo student S001 and student cohort."""

    @classmethod
    def setUpClass(cls):
        cls.db_mgr = DatabaseManager()
        seed_database(cls.db_mgr)

    def test_s001_overall_attendance_calibration(self):
        """Verify S001 overall attendance is exactly in the 78-79% range."""
        summary = get_raw_attendance_summary("S001")
        self.assertEqual(summary["total_conducted"], 240)
        self.assertEqual(summary["total_attended"], 189)
        self.assertEqual(summary["total_absent"], 51)

        pct = (summary["total_attended"] / summary["total_conducted"]) * 100
        self.assertAlmostEqual(pct, 78.75, places=2)
        self.assertTrue(78.0 <= pct <= 79.0, f"Expected 78-79%, got {pct}%")

    def test_s001_dbms_attendance_calibration(self):
        """Verify S001 DBMS attendance is ~73-74% (22/30)."""
        summary = get_raw_attendance_summary("S001")
        dbms = summary["subjects"]["SUB003"]
        self.assertEqual(dbms["subject_name"], "DBMS")
        self.assertEqual(dbms["conducted"], 30)
        self.assertEqual(dbms["attended"], 22)
        self.assertEqual(dbms["absent"], 8)

        dbms_pct = (dbms["attended"] / dbms["conducted"]) * 100
        self.assertAlmostEqual(dbms_pct, 73.33, places=1)
        self.assertTrue(73.0 <= dbms_pct <= 74.5)

    def test_s001_subject_breakdown_tiers(self):
        """Verify S001 has safe (>80%), borderline (~76-80%), and shortage (<75%) subjects."""
        summary = get_raw_attendance_summary("S001")
        subjects = summary["subjects"]

        # Safe (>80%)
        self.assertEqual(subjects["SUB001"]["attended"], 27)  # Python 90.0%
        self.assertEqual(subjects["SUB002"]["attended"], 25)  # Java 83.33%
        self.assertEqual(subjects["SUB006"]["attended"], 26)  # Math 86.67%

        # Borderline (76-80%)
        self.assertEqual(subjects["SUB004"]["attended"], 24)  # CN 80.0%
        self.assertEqual(subjects["SUB005"]["attended"], 23)  # SE 76.67%

        # Shortage (<75%)
        self.assertEqual(subjects["SUB003"]["attended"], 22)  # DBMS 73.33%
        self.assertEqual(subjects["SUB007"]["attended"], 22)  # AI 73.33%
        self.assertEqual(subjects["SUB008"]["attended"], 20)  # OS 66.67%

    def test_cohort_distribution(self):
        """Verify all 20 students have 240 conducted classes and realistic attendance."""
        students = get_all_students()
        safe_count = 0
        borderline_count = 0
        shortage_count = 0

        for st in students:
            s_id = st["student_id"]
            summary = get_raw_attendance_summary(s_id)
            self.assertEqual(summary["total_conducted"], 240)
            pct = (summary["total_attended"] / summary["total_conducted"]) * 100

            if pct >= 85.0:
                safe_count += 1
            elif pct >= 78.0:
                borderline_count += 1
            else:
                shortage_count += 1

        self.assertGreater(safe_count, 0, "Should have safe students")
        self.assertGreater(borderline_count, 0, "Should have borderline students")
        self.assertGreater(shortage_count, 0, "Should have shortage students")


if __name__ == "__main__":
    unittest.main()
