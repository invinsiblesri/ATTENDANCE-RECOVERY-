
# AI Attendance Recovery Agent

Team workspace for the four-member hackathon project.

Branches:

- `member-1`: AI agent and orchestration
- `member-2`: SQLite database, RAG, and memory
- `member-3`: Streamlit UI and dashboard
- `member-4`: Notifications and integration
# AI Attendance Recovery Agent — Database + RAG + Attendance Memory Backend

Production-grade, offline-first backend subsystem for the **AI Attendance Recovery Agent** college hackathon prototype.

---

## Key Features

1. **Structured SQLite Database**:
   - 20 realistic dummy students (`S001` to `S020`) in Year 3, Semester 5.
   - 8 equal-importance subjects (Python, Java, DBMS, Computer Networks, Software Engineering, Mathematics, Artificial Intelligence, Operating Systems).
   - Monday–Friday timetable with 8 periods/day (40 weekly slots, exactly 5 per subject).
   - 30 academic weekdays of period-wise history (240 conducted classes per student = 4,800 raw attendance records).
   - Demo student **S001** calibrated to **78.75% overall attendance** (189/240) and **73.33% DBMS attendance** (22/30).
   - Leave records and in-database notifications.

2. **Clean Contract with Member 1 (Calculator Agent)**:
   - Module provides pure raw totals (`attended`, `conducted`, `absent`) overall and per subject.
   - Zero duplicated percentage/recovery math in this module.

3. **ChromaDB Policy RAG Pipeline**:
   - Ingests simulated policy documents explicitly titled `# Demo College Attendance Policy — Hackathon Prototype`.
   - Zero invented bureaucratic regulations; focuses strictly on the 80% overall rule, equal weights, period-wise tracking, and upcoming class recovery guidance.
   - 100% offline local vector store with deterministic embeddings.

4. **Persistent Attendance-Only Memory**:
   - Stores warnings, status transitions, recovery roadmaps, agent actions, and important events with structured JSON metadata.
   - Strictly ignores arbitrary conversation chatter.

5. **Clean Public API Facade**:
   - Easily imported via `from attendance_recovery_backend.api.attendance_api import ...`.

---

## Directory Structure

```
attendance_recovery_backend/
├── data/
│   ├── attendance_system.db          # Persistent SQLite database
│   └── chroma_db/                    # Persistent ChromaDB vector database
├── database/
│   ├── __init__.py
│   ├── connection.py                 # SQLite connection manager (WAL mode, Foreign Keys enabled)
│   ├── schema.sql                    # SQL DDL definitions & indexes
│   ├── repository.py                 # Data Access Layer & raw totals aggregation
│   └── seed.py                       # High-fidelity seed generator
├── rag/
│   ├── __init__.py
│   ├── documents/
│   │   ├── attendance_policy.md      # Demo College Attendance Policy — 80% overall rule & period logging
│   │   ├── exam_eligibility.md       # Demo College Attendance Policy — 80% overall exam eligibility
│   │   └── attendance_recovery.md    # Demo College Attendance Policy — Upcoming class attendance recovery
│   ├── vector_store.py               # ChromaDB collection indexer with offline local embeddings
│   └── service.py                    # search_attendance_policy(query: str, n_results: int = 3)
├── memory/
│   ├── __init__.py
│   └── attendance_memory.py          # Persistent attendance-only event logging & retrieval
├── api/
│   ├── __init__.py
│   └── attendance_api.py             # Public API facade for AI Agent teammate
├── scripts/
│   ├── init_db.py                    # CLI script to initialize schema & seed data
│   └── build_rag.py                  # CLI script to index policy documents into ChromaDB
├── tests/
│   ├── __init__.py
│   ├── test_database_raw_totals.py  # Tests raw counts provision for Member 1 Calculator Agent
│   ├── test_timetable_and_history.py# Tests 8 periods/day, 40 slots, 30 days history
│   ├── test_demo_student_s001.py    # Tests S001 overall 78.75% and DBMS ~74%
│   ├── test_memory.py               # Tests persistent attendance-only memory
│   ├── test_notifications.py        # Tests SQLite notifications
│   ├── test_rag_retrieval.py        # Tests ChromaDB policy search
│   └── run_all_tests.py             # Master test runner
├── API_CONTRACT.md                   # Full API contract & schemas
├── requirements.txt                  # Local dependencies
└── README.md                         # This documentation
```

---

## Getting Started

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Initialize and Seed SQLite Database
```bash
python scripts/init_db.py
```
Output:
- 20 Students created (`S001` - `S020`)
- 8 Equal subjects configured
- 40 Timetable slots configured (Monday to Friday, Periods 1 to 8)
- 4,800 Raw period-wise attendance records generated (240 per student)
- S001 seeded with 189/240 attended (78.75% overall, DBMS 22/30 = 73.33%)

### 3. Build ChromaDB Vector Index
```bash
python scripts/build_rag.py
```
Indexes all documents from `rag/documents/` into `data/chroma_db/`.

### 4. Run the Full Test Suite
```bash
python tests/run_all_tests.py
```
All 32 tests will run and validate database raw aggregation, timetable rotation, demo student calibration, memory events, notifications, and ChromaDB RAG retrieval.

---

## Python API Quick Reference for Teammates

```python
from api.attendance_api import (
    get_student,
    get_all_subjects,
    get_raw_attendance_summary,
    get_upcoming_classes,
    save_attendance_event,
    get_attendance_memory,
    save_notification,
    get_notifications,
    search_attendance_policy
)

# 1. Fetch raw attendance totals for Member 1 Calculator Agent
summary = get_raw_attendance_summary("S001")
print(f"Conducted: {summary['total_conducted']}, Attended: {summary['total_attended']}")

# 2. Query today's upcoming classes
upcoming = get_upcoming_classes(day_of_week="Monday", current_period=4)

# 3. Search college attendance policies via local ChromaDB RAG
policy_chunks = search_attendance_policy("What is the minimum attendance requirement?")

# 4. Save persistent memory event
save_attendance_event(
    student_id="S001",
    subject_id="SUB003",
    event_type="RECOVERY_PLAN",
    description="Student committed to attend next 5 DBMS lectures."
)

# 5. Save in-database notification
save_notification(
    student_id="S001",
    subject_id="SUB003",
    message="Attendance is below 80%. Recovery required.",
    priority="HIGH"
)
```
 (Add Member 2 attendance backend)


---

## Member 1 Agent Integration

Member 1’s local AI agent runs with Ollama and `qwen3:latest`, LangGraph, LangChain, and FastAPI. The agent is responsible for intent understanding, tool selection, deterministic recovery calculations, and final answers. Member 2’s database, RAG, and memory backend is the authoritative source for attendance and policy data.

The public integration endpoint is:

```http
POST http://localhost:8000/agent/query
Content-Type: application/json
```

Example request:

```json
{
  "student_id": "S001",
  "message": "Can I take leave tomorrow?"
}
```

Member 1 should use the shared backend functions without directly depending on SQLite internals. The official functions include `get_student`, `get_all_subjects`, `get_attendance`, `get_subject_attendance`, `get_attendance_history`, `get_timetable`, `get_upcoming_classes`, `calculate_attendance`, `calculate_recovery`, `search_attendance_policy`, `save_attendance_event`, `get_attendance_memory`, `save_notification`, and `create_recovery_plan`.

## Team Branches

| Branch | Responsibility |
|---|---|
| `member-1` | AI agent and orchestration |
| `member-2` | SQLite database, RAG, and memory |
| `member-3` | Streamlit UI and dashboard |
| `member-4` | Notifications and integration |

The final integration flow is: Member 2 provides trusted data, Member 1 calls the backend through stable contracts, Member 4 provides notification persistence, and Member 3 displays the final result through Streamlit.


---

## Member 3 Frontend Integration

Member 3’s frontend lives in `frontend/` and is intentionally decoupled from the Python internals. The dashboard should call the backend through `frontend/services/api.js` rather than importing SQLite, RAG, or agent modules directly.

Frontend files:

```text
frontend/
├── index.html
├── styles.css
├── config.js
├── app.js
├── services/
│   └── api.js
└── README.md
```

The frontend should call the agent endpoint:

```http
POST http://localhost:8000/agent/query
Content-Type: application/json
```

Example request:

```json
{
  "student_id": "S001",
  "message": "What subjects are risky?"
}
```

Member 3 should start the backend first:

```powershell
.\.venv\Scripts\python.exe -m uvicorn agent.api:app --reload --port 8000
```

Then open `frontend/index.html` in a browser or use the frontend instructions in `frontend/README.md`. The UI must display backend results and must not duplicate attendance calculations or policy rules.
