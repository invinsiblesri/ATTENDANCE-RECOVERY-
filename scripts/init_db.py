"""
Database Initialization Script.
Creates tables and populates seed data (20 students, 8 equal subjects, 30 days x 8 periods attendance).
"""

import os
import sys

# Ensure backend root is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.connection import db_manager
from database.seed import seed_database


def main():
    print("=" * 60)
    print("AI Attendance Recovery Agent - Database Initializer")
    print("=" * 60)
    print(f"Target DB Path: {db_manager.db_path}")

    counts = seed_database(db_manager)

    print("\nDatabase initialization complete! Summary:")
    print(f"  - Students created:          {counts.get('students', 0)}")
    print(f"  - Subjects configured:       {counts.get('subjects', 0)}")
    print(f"  - Timetable slots seeded:    {counts.get('timetable_slots', 0)}")
    print(f"  - Attendance records logged: {counts.get('attendance_records', 0)}")
    print(f"  - Leave records created:     {counts.get('leave_records', 0)}")
    print(f"  - Notifications seeded:      {counts.get('notifications', 0)}")
    print(f"  - Memory events logged:      {counts.get('memory_events', 0)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
