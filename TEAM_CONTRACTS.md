# Corrected Four-Member Team Plan

The original division is good, but it is **not perfectly compatible yet**. The following changes are required so that the agent does not duplicate database logic, the RAG layer is actually used, memory persists across turns, and the Streamlit UI and notification service communicate through stable contracts.

## Final ownership

| Member | Owns | Must not own |
|---|---|---|
| Member 1 | Ollama model, LangGraph workflow, tool schemas, deterministic orchestration, final answer formatting | SQLite queries, vector-store internals, UI layouts, notification database writes |
| Member 2 | SQLite repositories, policy-document ingestion, retrieval, conversation/memory persistence | LLM tool selection, Streamlit rendering, notification side effects |
| Member 3 | Streamlit dashboard, chat interface, charts, recovery-plan display | Attendance calculations, policy interpretation, direct database access |
| Member 4 | In-app notification service, integration configuration, startup scripts, end-to-end testing | LLM reasoning, duplicate attendance logic, UI business rules |

## Required architecture change

Member 1 should not directly import Member 2’s SQLite implementation, vector-store implementation, or memory implementation. Instead, Member 1 should call a small adapter interface. During the first demo, these adapters may be in-process Python classes. If the team has time, Member 2 and Member 4 may expose them as local HTTP services. The agent’s tool names and JSON shapes remain unchanged in both cases.

```text
Streamlit UI (Member 3)
        |
        | POST /agent/query
        v
Agent API + LangGraph (Member 1)
        |
        +--> DataRepository adapter (Member 2) --> SQLite
        |
        +--> PolicyRetriever adapter (Member 2) --> vector store + policy metadata
        |
        +--> MemoryStore adapter (Member 2) --> SQLite memory tables
        |
        +--> NotificationService adapter (Member 4) --> in-app notifications
```

## SQLite schema owned by Member 2

The proposed tables are correct, but add primary keys, timestamps, and a stable `course_id`. Do not use only a free-text subject name as the join key.

```sql
CREATE TABLE students (
    student_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    department TEXT,
    semester INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE subjects (
    course_id TEXT PRIMARY KEY,
    course_name TEXT NOT NULL,
    minimum_attendance REAL NOT NULL DEFAULT 75.0,
    weekly_recovery_limit INTEGER NOT NULL DEFAULT 3
);

CREATE TABLE attendance (
    attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    course_id TEXT NOT NULL,
    conducted INTEGER NOT NULL CHECK (conducted >= 0),
    attended INTEGER NOT NULL CHECK (attended >= 0 AND attended <= conducted),
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(student_id, course_id),
    FOREIGN KEY(student_id) REFERENCES students(student_id),
    FOREIGN KEY(course_id) REFERENCES subjects(course_id)
);

CREATE TABLE timetable (
    timetable_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT NOT NULL,
    class_date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    room TEXT,
    section TEXT,
    is_cancelled INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(course_id) REFERENCES subjects(course_id)
);

CREATE TABLE leave_records (
    leave_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    course_id TEXT,
    leave_date TEXT NOT NULL,
    reason TEXT,
    status TEXT NOT NULL CHECK(status IN ('PENDING', 'APPROVED', 'REJECTED')),
    decision_note TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(student_id) REFERENCES students(student_id)
);

CREATE TABLE notifications (
    notification_id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL,
    message TEXT NOT NULL,
    priority TEXT NOT NULL CHECK(priority IN ('LOW', 'MEDIUM', 'HIGH')),
    status TEXT NOT NULL CHECK(status IN ('QUEUED', 'READ', 'DISMISSED')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    read_at TEXT,
    FOREIGN KEY(student_id) REFERENCES students(student_id)
);

CREATE TABLE memory_events (
    memory_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(student_id) REFERENCES students(student_id)
);
```

The `memory_events` table is the missing part of the original database design. It stores previous conversations, warnings, plans, and leave decisions without forcing Member 1 to know the database schema.

## Member 2 RAG contract

RAG should be used for **policy explanations and citations**, not for attendance arithmetic. The authoritative minimum percentage and weekly limit should come from the `subjects` table or a policy repository; the vector store should provide the relevant policy text and source filename.

Recommended files:

```text
data/
├── attendance.db
└── policies/
    ├── attendance_policy.txt
    ├── exam_eligibility.txt
    └── leave_policy.txt

rag/
├── ingest.py
└── retriever.py
```

Required interface:

```python
class PolicyRetriever:
    def search(self, question: str, course_id: str | None = None, k: int = 3) -> list[dict]:
        """Return policy passages with source and relevance metadata."""
```

Example result:

```json
{
  "query": "What happens below 75 percent?",
  "results": [
    {
      "text": "Students below 75% may be restricted from the final examination...",
      "source": "exam_eligibility.txt",
      "score": 0.91
    }
  ]
}
```

For a fully free stack, use a local embedding model and a local vector store. If setup time is very short, a SQLite FTS5 search over policy chunks is a valid fallback for the hackathon; label it as lexical retrieval rather than pretending it is semantic RAG.

## Member 2 memory contract

Memory is infrastructure around the agent, not necessarily a visible LLM tool. Before each model turn, Member 1 requests a short student-specific context. After the turn, Member 1 saves the interaction and any generated plan or warning.

```python
class MemoryStore:
    def get_context(self, student_id: str, limit: int = 8) -> list[dict]:
        """Return recent relevant events for this student."""

    def save_event(self, student_id: str, event_type: str, payload: dict) -> None:
        """Persist a conversation, warning, recovery plan, or leave decision."""
```

Use event types such as `conversation`, `warning`, `recovery_plan`, and `leave_decision`. Never pass every historical conversation to the model. Retrieve a small, relevant, privacy-safe context.

## Revised Member 1 tool contracts

The original six tools remain, but their signatures need two changes: timetable retrieval should be student-aware, and policy checking should expose retrieved policy evidence.

| Tool | Revised signature | Data source |
|---|---|---|
| `get_attendance` | `get_attendance(student_id, course_id=None)` | Member 2 repository over SQLite |
| `get_timetable` | `get_timetable(student_id, course_id=None, days=14)` | Member 2 repository over SQLite |
| `calculate_attendance` | `calculate_attendance(student_id, course_id, target_percentage=75.0)` | Attendance repository + deterministic Python math |
| `check_policy` | `check_policy(course_id, question='')` | Subject policy metadata + Member 2 RAG retriever |
| `create_recovery_plan` | `create_recovery_plan(student_id, course_id, target_percentage=75.0)` | Attendance + timetable + policy repository |
| `trigger_notification` | `trigger_notification(student_id, message, priority='MEDIUM')` | Member 4 notification service |

`calculate_attendance` and `create_recovery_plan` must remain deterministic. The language model may choose these tools, but it must not calculate the number itself.

## Revised Member 3 UI contract

Streamlit is an appropriate choice for a time-limited hackathon. It should call Member 1’s API rather than importing the agent graph or querying SQLite.

```http
POST http://localhost:8000/agent/query
Content-Type: application/json
```

```json
{
  "student_id": "S001",
  "message": "How many classes do I need to attend in DBMS?"
}
```

The UI should use separate read-only dashboard calls if the team wants cards with exact numeric values. A chat response is not a reliable substitute for dashboard data. Recommended optional endpoints are:

```text
GET /students/{student_id}/summary
GET /students/{student_id}/timetable
GET /students/{student_id}/notifications
```

If time is limited, keep only `POST /agent/query`; the agent can answer all four demo questions. The UI must not duplicate percentage calculations or policy rules.

## Revised Member 4 notification contract

Because the team explicitly chose in-app notifications, remove the email/channel requirement from the first version. Use priority instead.

```http
POST http://localhost:8001/notifications
Content-Type: application/json
```

```json
{
  "student_id": "S001",
  "message": "DBMS attendance is below 75%. Attend the next four classes to recover.",
  "priority": "HIGH"
}
```

Response:

```json
{
  "notification_id": "N1001",
  "student_id": "S001",
  "message": "DBMS attendance is below 75%. Attend the next four classes to recover.",
  "priority": "HIGH",
  "status": "QUEUED",
  "created_at": "2026-08-21T10:30:00Z"
}
```

Member 4 should also provide:

```text
notification/
└── notifier.py
```

with a stable function:

```python
def send_notification(student_id: str, message: str, priority: str = "MEDIUM") -> dict:
    """Create an in-app notification and return its persisted result."""
```

The agent should call this only when the student explicitly requests a reminder or when the product flow contains a clearly labeled consent action such as **“Notify me”**.

## Revised final folder layout

```text
project/
├── agent/
│   ├── agent.py
│   ├── graph.py
│   ├── prompts.py
│   ├── tools.py
│   └── models.py
├── data/
│   ├── attendance.db
│   └── policies/
├── rag/
│   ├── ingest.py
│   └── retriever.py
├── memory/
│   └── memory.py
├── notification/
│   └── notifier.py
├── ui/
│   ├── dashboard.py
│   ├── chat.py
│   └── components.py
├── tests/
│   ├── test_tools.py
│   ├── test_rag.py
│   ├── test_memory.py
│   └── test_integration.py
├── requirements.txt
├── .env.example
└── README.md
```

## Final integration order

First, Member 2 creates the SQLite database, seeds one realistic demo student, and confirms repository outputs against the shared Pydantic shapes. Second, Member 2 ingests the three policy files and makes `PolicyRetriever.search()` return source-tagged passages. Third, Member 1 replaces the demo dictionaries with the repository, retriever, and memory adapters while keeping tool signatures stable. Fourth, Member 4 exposes or imports `send_notification()` and confirms that a notification is persisted in SQLite. Fifth, Member 3 points Streamlit to `POST /agent/query` and displays the returned answer. Finally, the full team runs one end-to-end scenario: low DBMS attendance, policy lookup, exact recovery calculation, plan creation, explicit reminder request, in-app notification, and notification display in the dashboard.

## Acceptance checklist

| Check | Pass condition |
|---|---|
| SQLite integration | Agent reads real attendance and timetable values, not demo dictionaries |
| RAG integration | Policy answer includes a source filename or citation |
| Memory integration | A second question can use a previous plan or warning without resending the entire conversation |
| Calculation correctness | `calculate_attendance` matches a manually verified result |
| UI integration | Streamlit calls the API and does not access internal agent state |
| Notification safety | No notification is created unless the user requests it or clicks consent |
| Error handling | Missing student/course/policy data produces a clear response instead of hallucinated data |
| Reproducibility | One command or documented terminal sequence starts all components locally |


## Latest official Member 1 tool interface

The following functions are now included in `agent/tools.py` and are the authoritative interface between Member 1 and the other members:

| Function | Input | Purpose | Owner of internal data |
|---|---|---|---|
| `get_student()` | `student_id` | Get student details | Member 2 SQLite repository |
| `get_all_subjects()` | None | Get all eight subjects | Member 2 SQLite repository |
| `get_attendance()` | `student_id` | Get attendance for all subjects | Member 2 SQLite repository |
| `get_subject_attendance()` | `student_id, subject_id` | Get one subject’s attendance | Member 2 SQLite repository |
| `get_attendance_history()` | `student_id, subject_id` | Get period-wise history | Member 2 SQLite repository |
| `get_timetable()` | `student_id, day` | Get classes for a day such as `tomorrow` | Member 2 SQLite repository |
| `get_upcoming_classes()` | `student_id, day` | Get upcoming classes | Member 2 SQLite repository |
| `calculate_attendance()` | `student_id, subject_id` | Calculate current percentage | Member 1 deterministic logic using Member 2 data |
| `calculate_recovery()` | `attended, conducted, target` | Calculate required future classes | Member 1 deterministic logic |
| `search_attendance_policy()` | `question, subject_id` | Retrieve policy passages and source names | Member 2 RAG layer |
| `save_attendance_event()` | `event_data` | Store attendance memory | Member 2 memory layer |
| `get_attendance_memory()` | `student_id` | Retrieve attendance memory | Member 2 memory layer |
| `save_notification()` | `notification_data` | Save an in-app notification | Member 4 notification service |

The earlier `check_policy()`, `trigger_notification()`, and `create_recovery_plan()` functions remain as compatibility tools. New agent prompts should prefer `search_attendance_policy()` and `save_notification()` because those names match the final team design.

## Leave-tomorrow workflow

For the request, **“I need to know whether S001 can take leave tomorrow,”** the model should follow this sequence:

```text
User request
    |
    v
get_timetable(student_id="S001", day="tomorrow")
    |
    v
For each class returned:
get_subject_attendance(student_id="S001", subject_id=...)
    |
    v
calculate_recovery(attended=..., conducted=..., target=75)
    |
    v
search_attendance_policy(
    question="Can S001 take leave tomorrow?",
    subject_id=...
)
    |
    v
get_attendance_memory(student_id="S001")
    |
    v
Agent explains attendance impact, policy evidence, and uncertainty
```

The agent must not say that leave is officially approved unless an authorized leave-approval function is added. In the current design it should say whether leave appears **low-risk or risky**, explain the projected attendance effect, cite the retrieved policy source, and direct the student to the official approval process. If the student explicitly asks to record the request, call `save_attendance_event()` with an event type such as `leave_request`.

## Tool-calling versus direct function calls

The language model selects tools and decides the sequence, but the tools themselves are ordinary Python functions. Member 1’s tests invoke them directly, so calculations and data contracts can be validated without Ollama. Member 2 may replace the demo dictionaries with SQLite, RAG, and memory adapters without changing the model-facing names. Member 3 should call the agent API rather than these functions directly, and Member 4 should implement the notification persistence behind `save_notification()`.
