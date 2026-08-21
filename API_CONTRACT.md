# API Contract: AI Attendance Recovery Agent (Member 2 Module)

This document defines the strict API contract, function signatures, input/output data schemas, and integration points for the **AI Attendance Recovery Agent** backend module.

---

## 1. System Overview & Division of Responsibilities

- **Member 1 (Calculator Agent)**: Owns percentage calculations, margin formulas, and consecutive recovery math.
- **Member 2 (Database, RAG, Memory Module - THIS MODULE)**: Owns SQLite database persistence, raw uncalculated totals aggregation, period-by-period class logging, Monday–Friday 8-period timetable management, ChromaDB policy RAG search, and persistent attendance-only memory.
- **Member 3 / AI Agent**: Imports and calls functions from `attendance_recovery_backend.api.attendance_api` to query student state, search policies, log memory events, and manage notifications.

---

## 2. Core Import Entrypoint

All functions are exported directly from `api.attendance_api`:

```python
from attendance_recovery_backend.api.attendance_api import (
    # Student & Subject Lookups
    get_student,
    get_all_students,
    get_all_subjects,
    get_subject,

    # Raw Attendance Totals (Contract for Member 1 Calculator Agent)
    get_raw_attendance_summary,
    get_raw_subject_attendance,
    get_attendance_history,
    record_period_attendance,

    # Timetable (Monday-Friday, 8 Periods/Day)
    get_timetable,
    get_upcoming_classes,

    # Leave Records
    get_leave_records,
    apply_leave,

    # Persistent Attendance Memory
    save_attendance_event,
    get_attendance_memory,
    get_subject_memory,

    # Notifications (In-Database SQLite)
    save_notification,
    get_notifications,
    mark_notification_as_read,

    # ChromaDB Policy RAG Search
    search_attendance_policy
)
```

---

## 3. Function Signatures & Data Schemas

### 3.1 Raw Attendance Totals (For Member 1 Calculator Agent)

#### `get_raw_attendance_summary(student_id: str) -> Dict[str, Any]`
Retrieves uncalculated raw attendance counts (conducted, attended, absent) aggregated overall and broken down per subject.

**Output Schema:**
```json
{
  "student_id": "S001",
  "student_name": "Aarav Sharma",
  "department": "Computer Science & Engineering",
  "year": 3,
  "semester": 5,
  "total_conducted": 240,
  "total_attended": 189,
  "total_absent": 51,
  "subjects": {
    "SUB001": {
      "subject_id": "SUB001",
      "subject_code": "CS301",
      "subject_name": "Python",
      "conducted": 30,
      "attended": 27,
      "absent": 3
    },
    "SUB003": {
      "subject_id": "SUB003",
      "subject_code": "CS303",
      "subject_name": "DBMS",
      "conducted": 30,
      "attended": 22,
      "absent": 8
    }
  }
}
```

#### `get_raw_subject_attendance(student_id: str, subject_id: str) -> Dict[str, Any]`
Retrieves raw counts for a specific subject.

**Output Schema:**
```json
{
  "student_id": "S001",
  "subject_id": "SUB003",
  "subject_code": "CS303",
  "subject_name": "DBMS",
  "conducted": 30,
  "attended": 22,
  "absent": 8
}
```

#### `get_attendance_history(student_id: str, subject_id: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]`
Retrieves chronological period-by-period class attendance records.

**Item Schema:**
```json
{
  "attendance_id": 101,
  "student_id": "S001",
  "subject_id": "SUB003",
  "subject_code": "CS303",
  "subject_name": "DBMS",
  "date": "2026-01-05",
  "period_number": 3,
  "status": "Present",
  "created_at": "2026-01-05 09:00:00"
}
```

---

### 3.2 Timetable & Upcoming Classes

#### `get_timetable(day_of_week: Optional[str] = None) -> List[Dict[str, Any]]`
Retrieves timetable slots. If `day_of_week` is provided (`'Monday'` to `'Friday'`), returns the 8 periods for that day.

**Item Schema:**
```json
{
  "timetable_id": 1,
  "day_of_week": "Monday",
  "period_number": 1,
  "subject_id": "SUB001",
  "subject_code": "CS301",
  "subject_name": "Python",
  "start_time": "09:00",
  "end_time": "09:50"
}
```

#### `get_upcoming_classes(day_of_week: str, current_period: Optional[int] = None) -> List[Dict[str, Any]]`
Returns classes scheduled for a given day remaining after `current_period`.

---

### 3.3 Persistent Attendance Memory

#### `save_attendance_event(student_id: str, subject_id: Optional[str], event_type: str, description: str, metadata: Optional[Dict] = None) -> int`
Persists an attendance-only event.
- `event_type`: Must be one of `['WARNING', 'STATUS_CHANGE', 'RECOVERY_PLAN', 'AGENT_ACTION', 'IMPORTANT_EVENT']`.
- `metadata`: Optional arbitrary dictionary that will be serialized as JSON in SQLite.

#### `get_attendance_memory(student_id: str, limit: int = 50) -> List[Dict[str, Any]]`
Retrieves memory events for a student.

#### `get_subject_memory(student_id: str, subject_id: str, limit: int = 50) -> List[Dict[str, Any]]`
Retrieves memory events filtered by student and subject.

---

### 3.4 In-Database Notifications

#### `save_notification(student_id: str, subject_id: Optional[str], message: str, priority: str = 'MEDIUM') -> int`
Persists a notification in SQLite. Triggered when the AI Agent decides to create one.
- `priority`: Must be one of `['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']`.

#### `get_notifications(student_id: str, unread_only: bool = False) -> List[Dict[str, Any]]`
Retrieves notifications for a student.

#### `mark_notification_as_read(notification_id: int) -> bool`
Marks a notification as read (`is_read = 1`).

---

### 3.5 ChromaDB Policy RAG Search

#### `search_attendance_policy(query: str, n_results: int = 3) -> List[Dict[str, Any]]`
Queries the local ChromaDB vector store containing prototype college policies.

**Output Item Schema:**
```json
{
  "content": "[Demo College Attendance Policy — Hackathon Prototype] 1. Core Minimum Attendance Requirement...",
  "source": "attendance_policy.md",
  "title": "Demo College Attendance Policy — Hackathon Prototype",
  "section": "1. Core Minimum Attendance Requirement",
  "similarity_score": 0.8542,
  "metadata": {
    "source": "attendance_policy.md",
    "title": "Demo College Attendance Policy — Hackathon Prototype",
    "section": "1. Core Minimum Attendance Requirement"
  }
}
```
