"""
Master Test Runner for AI Attendance Recovery Agent Backend.
Executes all unit and integration test suites.
"""

import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def run_tests():
    print("=" * 70)
    print("AI Attendance Recovery Agent - Master Test Suite Runner")
    print("=" * 70)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Import and add test classes
    from tests.test_database_raw_totals import TestDatabaseRawTotals
    from tests.test_timetable_and_history import TestTimetableAndHistory
    from tests.test_demo_student_s001 import TestDemoStudentS001
    from tests.test_memory import TestAttendanceMemory
    from tests.test_notifications import TestNotifications
    from tests.test_rag_retrieval import TestRAGRetrieval

    test_classes = [
        TestDatabaseRawTotals,
        TestTimetableAndHistory,
        TestDemoStudentS001,
        TestAttendanceMemory,
        TestNotifications,
        TestRAGRetrieval,
    ]

    for tc in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(tc))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("=" * 70)
    if result.wasSuccessful():
        print(f"ALL TESTS PASSED! ({result.testsRun} tests executed)")
    else:
        print(f"TESTS FAILED: {len(result.failures)} failures, {len(result.errors)} errors out of {result.testsRun} tests.")
    print("=" * 70)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
