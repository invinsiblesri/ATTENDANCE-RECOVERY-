# AttendAI — Team Integration & Architecture Guide

This guide defines the interfaces and contracts connecting **Member 1 (AI Agent)**, **Member 2 (Database & RAG)**, **Member 3 (Frontend Dashboard)**, and **Member 4 (Automation & Notifications)**.

---

## 1. Member 1 — AI Agent / Brain
**Main Responsibility:** LangGraph / LangChain + Ollama agent workflow, Tool calling, Decision making, and Recovery-plan generation.

### Expected Directory Deliverable
```
agent/
├── agent.py               # Main agent execution loop
├── graph.py               # LangGraph state graph definition
├── prompts.py             # System prompts & recovery planning instructions
└── tools.py               # Agent tools
```

### Agent Tool Signatures
In `agent/tools.py`, Member 1 implements:
1. `get_attendance(student_id: str) -> dict`: Returns total attended, missed, and percentage from SQLite.
2. `get_timetable(student_id: str, week: str) -> dict`: Fetches 6-day × 8-period matrix.
3. `calculate_attendance(student_id: str, simulate_absence: int) -> float`: Calculates projected attendance.
4. `check_policy(threshold: float = 0.75) -> str`: Queries ChromaDB for college policy clauses (e.g. 75% minimum).
5. `create_recovery_plan(student_id: str, missed_subjects: list) -> dict`: Generates step-by-step roadmap.
6. `trigger_notification(student_id: str, message: str)`: Sends alert to Member 4.

---

## 2. Member 2 — Database + RAG + Memory
**Main Responsibility:** Store 20 students' attendance records in SQLite and college policy documents in ChromaDB.

### SQLite Schema (`database.sqlite`)
```sql
CREATE TABLE students (
    student_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    branch TEXT,
    year TEXT,
    semester TEXT,
    roll_no TEXT,
    email TEXT,
    base_rate REAL
);

CREATE TABLE timetable (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT,
    day TEXT,
    period INTEGER,
    subject TEXT,
    status TEXT, -- 'Present', 'Absent', 'Upcoming', 'Leave'
    FOREIGN KEY(student_id) REFERENCES students(student_id)
);
```

---

## 3. Member 3 — Frontend UI & Timetable
**Main Responsibility:** Modern, minimal 1440 × 900 desktop attendance dashboard with an 8-period × 6-day timetable.
- Standalone module located in `frontend/`.
- Features dynamic week switching (`Previous`, `Next`, `Today`).
- Decoupled API service in `frontend/services/api.js`.
- Config toggle in `frontend/config.js`.

---

## 4. Member 4 — Automation + Notification + Integration
**Main Responsibility:** Proactive background monitoring engine.

### Automated Triggers
1. **Threshold Drop Monitor**: If `overall_attendance < 75.0%` or student is marked `Absent` in any period today, automatically dispatch a warning.
2. **Upcoming Period Reminder**: 15 minutes before high-priority periods (e.g. Period 5 AI).
3. **Recovery Plan Auto-Dispatch**: When absence occurs, invoke Member 1's `create_recovery_plan()` and push the result directly to the frontend's notification center.
