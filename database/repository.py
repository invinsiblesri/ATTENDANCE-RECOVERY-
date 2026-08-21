"""
Data Access Layer (Repository) for Attendance Recovery Agent.
Provides clean query operations, uncalculated raw counts for Member 1 Calculator Agent,
and management functions for students, subjects, timetable, leave, and notifications.
"""

import json
import sqlite3
from typing import Optional, List, Dict, Any
from .connection import DatabaseManager, db_manager


class AttendanceRepository:
    """Data access repository for database tables."""

    def __init__(self, db_manager_instance: Optional[DatabaseManager] = None):
        self.db = db_manager_instance or db_manager

    # -------------------------------------------------------------------------
    # Student Operations
    # -------------------------------------------------------------------------
    def get_student(self, student_id: str) -> Optional[Dict[str, Any]]:
        """Fetch student details by student_id."""
        with self.db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT student_id, name, department, year, semester FROM students WHERE student_id = ?",
                (student_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_students(self) -> List[Dict[str, Any]]:
        """Fetch all registered students."""
        with self.db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT student_id, name, department, year, semester FROM students ORDER BY student_id ASC"
            )
            return [dict(row) for row in cursor.fetchall()]

    # -------------------------------------------------------------------------
    # Subject Operations (8 Equal Subjects)
    # -------------------------------------------------------------------------
    def get_subject(self, subject_id: str) -> Optional[Dict[str, Any]]:
        """Fetch subject details by subject_id."""
        with self.db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT subject_id, subject_code, subject_name FROM subjects WHERE subject_id = ?",
                (subject_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_subjects(self) -> List[Dict[str, Any]]:
        """Fetch all 8 subjects."""
        with self.db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT subject_id, subject_code, subject_name FROM subjects ORDER BY subject_id ASC"
            )
            return [dict(row) for row in cursor.fetchall()]

    # -------------------------------------------------------------------------
    # Raw Attendance Data for Member 1 (Calculator Agent)
    # -------------------------------------------------------------------------
    def get_raw_attendance_summary(self, student_id: str) -> Dict[str, Any]:
        """
        Retrieves uncalculated raw attendance totals (attended, conducted, absent)
        aggregated overall and per subject for consumption by Member 1's Calculator Agent.
        Does NOT perform percentage or recovery calculations.
        """
        student = self.get_student(student_id)
        if not student:
            raise ValueError(f"Student '{student_id}' does not exist.")

        subjects = self.get_all_subjects()
        subject_map = {s["subject_id"]: s for s in subjects}

        with self.db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 
                    subject_id,
                    COUNT(*) as conducted,
                    SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) as attended,
                    SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) as absent
                FROM attendance_records
                WHERE student_id = ?
                GROUP BY subject_id
                """,
                (student_id,)
            )
            rows = cursor.fetchall()

        subject_stats = {}
        total_conducted = 0
        total_attended = 0
        total_absent = 0

        for s_id, s_info in subject_map.items():
            subject_stats[s_id] = {
                "subject_id": s_id,
                "subject_code": s_info["subject_code"],
                "subject_name": s_info["subject_name"],
                "conducted": 0,
                "attended": 0,
                "absent": 0,
            }

        for row in rows:
            s_id = row["subject_id"]
            cond = int(row["conducted"])
            att = int(row["attended"] or 0)
            ab = int(row["absent"] or 0)
            if s_id in subject_stats:
                subject_stats[s_id]["conducted"] = cond
                subject_stats[s_id]["attended"] = att
                subject_stats[s_id]["absent"] = ab
                total_conducted += cond
                total_attended += att
                total_absent += ab

        return {
            "student_id": student_id,
            "student_name": student["name"],
            "department": student["department"],
            "year": student["year"],
            "semester": student["semester"],
            "total_conducted": total_conducted,
            "total_attended": total_attended,
            "total_absent": total_absent,
            "subjects": subject_stats
        }

    def get_raw_subject_attendance(self, student_id: str, subject_id: str) -> Dict[str, Any]:
        """
        Retrieves raw attendance counts for a single specific subject for a student.
        """
        subject = self.get_subject(subject_id)
        if not subject:
            raise ValueError(f"Subject '{subject_id}' does not exist.")

        with self.db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as conducted,
                    SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) as attended,
                    SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) as absent
                FROM attendance_records
                WHERE student_id = ? AND subject_id = ?
                """,
                (student_id, subject_id)
            )
            row = cursor.fetchone()

        conducted = int(row["conducted"]) if row and row["conducted"] else 0
        attended = int(row["attended"]) if row and row["attended"] else 0
        absent = int(row["absent"]) if row and row["absent"] else 0

        return {
            "student_id": student_id,
            "subject_id": subject_id,
            "subject_code": subject["subject_code"],
            "subject_name": subject["subject_name"],
            "conducted": conducted,
            "attended": attended,
            "absent": absent
        }

    def get_attendance_history(
        self,
        student_id: str,
        subject_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves raw period-by-period attendance records for a student with optional filters.
        """
        query = """
            SELECT 
                a.attendance_id,
                a.student_id,
                a.subject_id,
                s.subject_code,
                s.subject_name,
                a.date,
                a.period_number,
                a.status,
                a.created_at
            FROM attendance_records a
            JOIN subjects s ON a.subject_id = s.subject_id
            WHERE a.student_id = ?
        """
        params: List[Any] = [student_id]

        if subject_id:
            query += " AND a.subject_id = ?"
            params.append(subject_id)
        if start_date:
            query += " AND a.date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND a.date <= ?"
            params.append(end_date)

        query += " ORDER BY a.date ASC, a.period_number ASC"

        with self.db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]

    def record_period_attendance(
        self,
        student_id: str,
        subject_id: str,
        date: str,
        period_number: int,
        status: str
    ) -> int:
        """Insert or update a period-wise attendance record."""
        if status not in ("Present", "Absent"):
            raise ValueError(f"Invalid status '{status}'. Must be 'Present' or 'Absent'.")
        if not (1 <= period_number <= 8):
            raise ValueError(f"Invalid period_number '{period_number}'. Must be 1 to 8.")

        with self.db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO attendance_records (student_id, subject_id, date, period_number, status)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(student_id, date, period_number) DO UPDATE SET
                    subject_id = excluded.subject_id,
                    status = excluded.status
                """,
                (student_id, subject_id, date, period_number, status)
            )
            return cursor.lastrowid

    def bulk_record_attendance(self, records: List[Dict[str, Any]]) -> int:
        """Bulk insert attendance records in a single transaction."""
        with self.db.connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(
                """
                INSERT INTO attendance_records (student_id, subject_id, date, period_number, status)
                VALUES (:student_id, :subject_id, :date, :period_number, :status)
                ON CONFLICT(student_id, date, period_number) DO UPDATE SET
                    subject_id = excluded.subject_id,
                    status = excluded.status
                """,
                records
            )
            return len(records)

    # -------------------------------------------------------------------------
    # Timetable Operations (Monday to Friday, 8 Periods/Day)
    # -------------------------------------------------------------------------
    def get_timetable(self, day_of_week: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch timetable slots. If day_of_week is provided, filters by that day.
        """
        query = """
            SELECT 
                t.timetable_id,
                t.day_of_week,
                t.period_number,
                t.subject_id,
                s.subject_code,
                s.subject_name,
                t.start_time,
                t.end_time
            FROM timetable t
            JOIN subjects s ON t.subject_id = s.subject_id
        """
        params: List[Any] = []
        if day_of_week:
            query += " WHERE t.day_of_week = ?"
            params.append(day_of_week)

        query += " ORDER BY CASE t.day_of_week " \
                 "WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 " \
                 "WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 ELSE 6 END, t.period_number ASC"

        with self.db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]

    def get_upcoming_classes(self, day_of_week: str, current_period: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch classes for a given day remaining after current_period (or all if current_period is None).
        """
        query = """
            SELECT 
                t.timetable_id,
                t.day_of_week,
                t.period_number,
                t.subject_id,
                s.subject_code,
                s.subject_name,
                t.start_time,
                t.end_time
            FROM timetable t
            JOIN subjects s ON t.subject_id = s.subject_id
            WHERE t.day_of_week = ?
        """
        params: List[Any] = [day_of_week]

        if current_period is not None:
            query += " AND t.period_number > ?"
            params.append(current_period)

        query += " ORDER BY t.period_number ASC"

        with self.db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]

    # -------------------------------------------------------------------------
    # Leave Records
    # -------------------------------------------------------------------------
    def get_leave_records(self, student_id: str) -> List[Dict[str, Any]]:
        """Fetch leave records for a student."""
        with self.db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT leave_id, student_id, date, reason, status, created_at
                FROM leave_records
                WHERE student_id = ?
                ORDER BY date DESC
                """,
                (student_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def apply_leave(self, student_id: str, date: str, reason: str, status: str = "Pending") -> int:
        """Submit a new leave record."""
        if status not in ("Pending", "Approved", "Rejected"):
            raise ValueError(f"Invalid leave status '{status}'.")

        with self.db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO leave_records (student_id, date, reason, status)
                VALUES (?, ?, ?, ?)
                """,
                (student_id, date, reason, status)
            )
            return cursor.lastrowid

    # -------------------------------------------------------------------------
    # Notifications (Stored strictly in SQLite)
    # -------------------------------------------------------------------------
    def save_notification(
        self,
        student_id: str,
        subject_id: Optional[str],
        message: str,
        priority: str = "MEDIUM"
    ) -> int:
        """
        Store a notification in SQLite. Triggered when the AI Agent decides to create one.
        """
        if priority not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
            raise ValueError(f"Invalid priority '{priority}'.")

        with self.db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO notifications (student_id, subject_id, message, priority, is_read)
                VALUES (?, ?, ?, ?, 0)
                """,
                (student_id, subject_id, message, priority)
            )
            return cursor.lastrowid

    def get_notifications(self, student_id: str, unread_only: bool = False) -> List[Dict[str, Any]]:
        """
        Retrieve stored notifications for a student.
        """
        query = """
            SELECT 
                n.notification_id,
                n.student_id,
                n.subject_id,
                s.subject_name,
                n.message,
                n.priority,
                n.is_read,
                n.created_at
            FROM notifications n
            LEFT JOIN subjects s ON n.subject_id = s.subject_id
            WHERE n.student_id = ?
        """
        params: List[Any] = [student_id]
        if unread_only:
            query += " AND n.is_read = 0"

        query += " ORDER BY n.created_at DESC, n.notification_id DESC"

        with self.db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]

    def mark_notification_as_read(self, notification_id: int) -> bool:
        """Mark a stored notification as read."""
        with self.db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE notifications SET is_read = 1 WHERE notification_id = ?",
                (notification_id,)
            )
            return cursor.rowcount > 0

    # -------------------------------------------------------------------------
    # Attendance-Only Persistent Memory
    # -------------------------------------------------------------------------
    def save_attendance_event(
        self,
        student_id: str,
        subject_id: Optional[str],
        event_type: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Persist an attendance-only event in SQLite memory.
        """
        valid_types = ("WARNING", "STATUS_CHANGE", "RECOVERY_PLAN", "AGENT_ACTION", "IMPORTANT_EVENT")
        if event_type not in valid_types:
            raise ValueError(f"Invalid event_type '{event_type}'. Must be one of {valid_types}.")

        meta_json = json.dumps(metadata) if metadata is not None else None

        with self.db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO attendance_memory (student_id, subject_id, event_type, description, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (student_id, subject_id, event_type, description, meta_json)
            )
            return cursor.lastrowid

    def get_attendance_memory(self, student_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch attendance memory events for a student."""
        with self.db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 
                    m.memory_id,
                    m.student_id,
                    m.subject_id,
                    s.subject_name,
                    m.event_type,
                    m.description,
                    m.metadata,
                    m.created_at
                FROM attendance_memory m
                LEFT JOIN subjects s ON m.subject_id = s.subject_id
                WHERE m.student_id = ?
                ORDER BY m.created_at DESC, m.memory_id DESC
                LIMIT ?
                """,
                (student_id, limit)
            )
            rows = cursor.fetchall()

        events = []
        for r in rows:
            d = dict(r)
            if d.get("metadata"):
                try:
                    d["metadata"] = json.loads(d["metadata"])
                except Exception:
                    pass
            events.append(d)
        return events

    def get_subject_memory(self, student_id: str, subject_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch attendance memory events filtered by student and subject."""
        with self.db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 
                    m.memory_id,
                    m.student_id,
                    m.subject_id,
                    s.subject_name,
                    m.event_type,
                    m.description,
                    m.metadata,
                    m.created_at
                FROM attendance_memory m
                LEFT JOIN subjects s ON m.subject_id = s.subject_id
                WHERE m.student_id = ? AND m.subject_id = ?
                ORDER BY m.created_at DESC, m.memory_id DESC
                LIMIT ?
                """,
                (student_id, subject_id, limit)
            )
            rows = cursor.fetchall()

        events = []
        for r in rows:
            d = dict(r)
            if d.get("metadata"):
                try:
                    d["metadata"] = json.loads(d["metadata"])
                except Exception:
                    pass
            events.append(d)
        return events
