"""
Seed Data Generator for AI Attendance Recovery Agent.
Generates:
- Exactly 20 students (S001 to S020)
- Exactly 8 equal subjects (no priority/weighting)
- Monday-Friday 8-period timetable (40 slots, exactly 5 per subject)
- 30 academic weekdays of period-wise attendance history (240 conducted periods per student = 4,800 records)
- S001 primary demo student calibrated to 78.75% overall (189/240) and ~73.3% DBMS (22/30)
- Cohort variations (safe, borderline, shortage)
- Realistic leave records, notifications, and memory events
"""

import os
import random
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from .connection import DatabaseManager, db_manager
from .repository import AttendanceRepository


# 1. Exactly 20 Students
STUDENTS_DATA = [
    ("S001", "Aarav Sharma", "Computer Science & Engineering", 3, 5),
    ("S002", "Priya Patel", "Computer Science & Engineering", 3, 5),
    ("S003", "Rohan Iyer", "Computer Science & Engineering", 3, 5),
    ("S004", "Ananya Gupta", "Computer Science & Engineering", 3, 5),
    ("S005", "Vikram Malhotra", "Computer Science & Engineering", 3, 5),
    ("S006", "Sneha Reddy", "Computer Science & Engineering", 3, 5),
    ("S007", "Rahul Verma", "Computer Science & Engineering", 3, 5),
    ("S008", "Neha Nair", "Computer Science & Engineering", 3, 5),
    ("S009", "Siddharth Rao", "Computer Science & Engineering", 3, 5),
    ("S010", "Pooja Joshi", "Computer Science & Engineering", 3, 5),
    ("S011", "Karan Mehta", "Computer Science & Engineering", 3, 5),
    ("S012", "Divya Deshmukh", "Computer Science & Engineering", 3, 5),
    ("S013", "Aditya Kulkarni", "Computer Science & Engineering", 3, 5),
    ("S014", "Ritu Choudhury", "Computer Science & Engineering", 3, 5),
    ("S015", "Varun Kapoor", "Computer Science & Engineering", 3, 5),
    ("S016", "Ishita Sen", "Computer Science & Engineering", 3, 5),
    ("S017", "Manish Pandey", "Computer Science & Engineering", 3, 5),
    ("S018", "Tanvi Bhat", "Computer Science & Engineering", 3, 5),
    ("S019", "Nikhil Saxena", "Computer Science & Engineering", 3, 5),
    ("S020", "Meera Pillai", "Computer Science & Engineering", 3, 5),
]

# 2. Exactly 8 Equal Subjects
SUBJECTS_DATA = [
    ("SUB001", "CS301", "Python"),
    ("SUB002", "CS302", "Java"),
    ("SUB003", "CS303", "DBMS"),
    ("SUB004", "CS304", "Computer Networks"),
    ("SUB005", "CS305", "Software Engineering"),
    ("SUB006", "CS306", "Mathematics"),
    ("SUB007", "CS307", "Artificial Intelligence"),
    ("SUB008", "CS308", "Operating Systems"),
]

# 3. Monday - Friday, 8 Periods/Day
PERIOD_TIMINGS = [
    (1, "09:00", "09:50"),
    (2, "09:50", "10:40"),
    (3, "10:55", "11:45"),
    (4, "11:45", "12:35"),
    (5, "13:30", "14:20"),
    (6, "14:20", "15:10"),
    (7, "15:20", "16:10"),
    (8, "16:10", "17:00"),
]

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

TIMETABLE_MATRIX = {
    "Monday":    ["SUB001", "SUB002", "SUB003", "SUB004", "SUB005", "SUB006", "SUB007", "SUB008"],
    "Tuesday":   ["SUB008", "SUB001", "SUB002", "SUB003", "SUB004", "SUB005", "SUB006", "SUB007"],
    "Wednesday": ["SUB007", "SUB008", "SUB001", "SUB002", "SUB003", "SUB004", "SUB005", "SUB006"],
    "Thursday":  ["SUB006", "SUB007", "SUB008", "SUB001", "SUB002", "SUB003", "SUB004", "SUB005"],
    "Friday":    ["SUB005", "SUB006", "SUB007", "SUB008", "SUB001", "SUB002", "SUB003", "SUB004"],
}

S001_TARGET_ATTENDANCE = {
    "SUB001": 27,  # Python: 27/30 (90.0%) - Safe
    "SUB002": 25,  # Java: 25/30 (83.33%) - Safe
    "SUB003": 22,  # DBMS: 22/30 (73.33%) - Shortage (~74%)
    "SUB004": 24,  # Computer Networks: 24/30 (80.0%) - Borderline
    "SUB005": 23,  # Software Engineering: 23/30 (76.67%) - Borderline
    "SUB006": 26,  # Mathematics: 26/30 (86.67%) - Safe
    "SUB007": 22,  # Artificial Intelligence: 22/30 (73.33%) - Shortage
    "SUB008": 20,  # Operating Systems: 20/30 (66.67%) - Shortage
}

COHORT_ATTENDANCE_RATES = {
    "S002": 0.93,
    "S003": 0.90,
    "S004": 0.88,
    "S005": 0.92,
    "S006": 0.87,
    "S007": 0.91,
    "S008": 0.89,
    "S009": 0.81,
    "S010": 0.80,
    "S011": 0.82,
    "S012": 0.79,
    "S013": 0.81,
    "S014": 0.79,
    "S015": 0.74,
    "S016": 0.72,
    "S017": 0.75,
    "S018": 0.69,
    "S019": 0.73,
    "S020": 0.68,
}


def generate_academic_dates(num_days: int = 30) -> List[Tuple[str, str]]:
    """
    Generates 30 academic dates (Monday to Friday only, excluding weekends).
    Returns list of (date_str, day_of_week).
    """
    dates = []
    current_date = datetime(2026, 1, 5)  # Monday, Jan 5, 2026
    while len(dates) < num_days:
        day_name = current_date.strftime("%A")
        if day_name in DAYS_OF_WEEK:
            dates.append((current_date.strftime("%Y-%m-%d"), day_name))
        current_date += timedelta(days=1)
    return dates


def seed_database(db_manager_instance: Optional[DatabaseManager] = None) -> Dict[str, int]:
    """
    Seeds the SQLite database with full schema and realistic data.
    Cleanly resets tables to guarantee exact deterministic counts.
    Returns counts of inserted records.
    """
    mgr = db_manager_instance or db_manager
    mgr.init_schema()

    repo = AttendanceRepository(mgr)
    counts = {}

    with mgr.connection() as conn:
        cursor = conn.cursor()

        # Clean reset tables in reverse dependency order
        cursor.execute("DELETE FROM attendance_records;")
        cursor.execute("DELETE FROM attendance_memory;")
        cursor.execute("DELETE FROM notifications;")
        cursor.execute("DELETE FROM leave_records;")
        cursor.execute("DELETE FROM timetable;")
        cursor.execute("DELETE FROM subjects;")
        cursor.execute("DELETE FROM students;")

        # 1. Seed Students
        cursor.executemany(
            """
            INSERT INTO students (student_id, name, department, year, semester)
            VALUES (?, ?, ?, ?, ?)
            """,
            STUDENTS_DATA
        )
        counts["students"] = len(STUDENTS_DATA)

        # 2. Seed Subjects
        cursor.executemany(
            """
            INSERT INTO subjects (subject_id, subject_code, subject_name)
            VALUES (?, ?, ?)
            """,
            [(s[0], s[1], s[2]) for s in SUBJECTS_DATA]
        )
        counts["subjects"] = len(SUBJECTS_DATA)

        # 3. Seed Timetable (40 slots)
        timetable_records = []
        for day in DAYS_OF_WEEK:
            subj_list = TIMETABLE_MATRIX[day]
            for period_idx, (p_num, start_t, end_t) in enumerate(PERIOD_TIMINGS):
                subj_id = subj_list[period_idx]
                timetable_records.append((day, p_num, subj_id, start_t, end_t))

        cursor.executemany(
            """
            INSERT INTO timetable (day_of_week, period_number, subject_id, start_time, end_time)
            VALUES (?, ?, ?, ?, ?)
            """,
            timetable_records
        )
        counts["timetable_slots"] = len(timetable_records)

    # 4. Generate Period-Wise Attendance Records (30 days * 8 periods = 240 per student)
    academic_days = generate_academic_dates(30)
    attendance_records = []

    class_schedule_log = []
    for date_str, day_name in academic_days:
        subj_list = TIMETABLE_MATRIX[day_name]
        for p_num, subj_id in enumerate(subj_list, start=1):
            class_schedule_log.append({
                "date": date_str,
                "period_number": p_num,
                "subject_id": subj_id
            })

    # Prepare S001 Attendance (exact counts)
    s001_subject_occurrences = {s[0]: [] for s in SUBJECTS_DATA}
    for idx, item in enumerate(class_schedule_log):
        s001_subject_occurrences[item["subject_id"]].append(idx)

    # Determine absent slot indices for S001
    s001_absent_indices = set()
    rng_s001 = random.Random(101)
    for s_id, target_att in S001_TARGET_ATTENDANCE.items():
        all_slots = s001_subject_occurrences[s_id]
        conducted = len(all_slots)  # exactly 30
        needed_absences = conducted - target_att
        absent_chosen = rng_s001.sample(all_slots, needed_absences)
        s001_absent_indices.update(absent_chosen)

    # Populate S001 records
    for idx, item in enumerate(class_schedule_log):
        status = "Absent" if idx in s001_absent_indices else "Present"
        attendance_records.append({
            "student_id": "S001",
            "subject_id": item["subject_id"],
            "date": item["date"],
            "period_number": item["period_number"],
            "status": status
        })

    # Populate S002 to S020 records
    for s_tuple in STUDENTS_DATA[1:]:
        s_id = s_tuple[0]
        prob = COHORT_ATTENDANCE_RATES.get(s_id, 0.85)
        rng = random.Random(int(s_id.replace("S", "")) * 1337)
        for item in class_schedule_log:
            status = "Present" if rng.random() < prob else "Absent"
            attendance_records.append({
                "student_id": s_id,
                "subject_id": item["subject_id"],
                "date": item["date"],
                "period_number": item["period_number"],
                "status": status
            })

    # Bulk insert attendance records
    repo.bulk_record_attendance(attendance_records)
    counts["attendance_records"] = len(attendance_records)

    # 5. Seed Leave Records for S001
    repo.apply_leave("S001", "2026-01-21", "Viral Fever / Medical Rest", "Approved")
    repo.apply_leave("S001", "2026-02-06", "Family Emergency", "Approved")
    repo.apply_leave("S015", "2026-01-15", "Outstation Travel", "Pending")
    counts["leave_records"] = 3

    # 6. Seed Notifications for S001
    repo.save_notification(
        student_id="S001",
        subject_id="SUB003",
        message="Overall attendance is 78.75% (below 80% threshold). DBMS attendance is at 73.33%. Attendance recovery required.",
        priority="HIGH"
    )
    repo.save_notification(
        student_id="S001",
        subject_id="SUB007",
        message="Artificial Intelligence attendance is at 73.33% (below 80% threshold).",
        priority="MEDIUM"
    )
    counts["notifications"] = 2

    # 7. Seed Attendance Memory for S001
    repo.save_attendance_event(
        student_id="S001",
        subject_id="SUB003",
        event_type="WARNING",
        description="DBMS attendance dropped to 73.33% (below 80% target).",
        metadata={"subject_code": "CS303", "conducted": 30, "attended": 22}
    )
    repo.save_attendance_event(
        student_id="S001",
        subject_id=None,
        event_type="IMPORTANT_EVENT",
        description="Approved medical leave on 2026-01-21 logged in record.",
        metadata={"date": "2026-01-21", "reason": "Viral Fever / Medical Rest"}
    )
    repo.save_attendance_event(
        student_id="S001",
        subject_id=None,
        event_type="AGENT_ACTION",
        description="Initial attendance summary generated for student S001.",
        metadata={"overall_conducted": 240, "overall_attended": 189}
    )
    counts["memory_events"] = 3

    return counts


if __name__ == "__main__":
    print("Seeding database...")
    result = seed_database()
    print("Database seeded successfully:")
    for k, v in result.items():
        print(f"  - {k}: {v}")
