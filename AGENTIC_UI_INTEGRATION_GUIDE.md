# Make the Merged Project Truly Agentic

## The key distinction

A chatbot mainly produces text. An agentic attendance system accepts a student goal, gathers evidence through tools, makes a constrained decision, and performs an approved action when one is required.

The expected flow is:

```text
Student goal
    ↓
Agent understands the goal
    ↓
Agent selects tools
    ↓
Tools retrieve SQLite/RAG/memory data
    ↓
Agent evaluates the evidence
    ↓
Agent chooses the next step
    ↓
Agent creates a recovery plan or saves a notification
    ↓
UI displays the evidence, decision, and action result
```

The model must not invent attendance values, perform policy arithmetic in natural language, access SQLite directly, or silently send notifications.

## Current state of the main branch

The main branch already contains the agent, database, RAG, memory, notification, and frontend directories. However, two connections must be completed before the product is fully live:

1. `agent/tools.py` still contains temporary demo dictionaries. Its public tools must call Member 2’s public functions in `api/attendance_api.py`.
2. The frontend currently starts with `USE_MOCK_DATA: true` and its `/api` paths do not exactly match the existing `/health` and `/agent/query` FastAPI routes.

Do not call the system fully integrated until these two items are fixed.

## Target architecture

```text
frontend/index.html + app.js
          │
          │ POST /agent/query
          ▼
agent/api.py
          │
          ▼
LangGraph agent graph
  ├── understand goal
  ├── call trusted tools
  ├── inspect tool results
  ├── decide whether more evidence is needed
  └── return answer + evidence + action result
          │
          ├── Member 2 public facade: api/attendance_api.py
          │       ├── SQLite attendance
          │       ├── timetable
          │       ├── memory
          │       └── ChromaDB policy RAG
          │
          └── Member 4 notification persistence
```

The frontend must call the agent API. It must not calculate attendance, search policy documents, or import the database package.

## Step 1: Create an integration branch

Run these commands from the repository root:

```powershell
git switch main
git pull --ff-only origin main
git switch -c agentic-live-integration
```

This keeps the final integration changes reviewable. Push the branch later with:

```powershell
git push -u origin agentic-live-integration
```

## Step 2: Use one student ID everywhere

The current frontend uses `24CS042`, while the Member 2 demo database uses `S001`. Select one ID for the hackathon. The fastest option is to use `S001` everywhere.

In `frontend/config.js`, change:

```javascript
DEFAULT_STUDENT_ID: "24CS042"
```

to:

```javascript
DEFAULT_STUDENT_ID: "S001"
```

Do not allow the frontend and backend to silently use different student identifiers.

## Step 3: Replace demo tool data with Member 2’s public facade

The clean boundary is `api/attendance_api.py`. Member 1 tools should call that facade rather than importing SQLite classes or opening the database directly.

At the top of `agent/tools.py`, add imports similar to:

```python
from api.attendance_api import (
    get_student as db_get_student,
    get_all_subjects as db_get_all_subjects,
    get_raw_attendance_summary,
    get_raw_subject_attendance,
    get_attendance_history as db_get_attendance_history,
    get_timetable as db_get_timetable,
    get_upcoming_classes as db_get_upcoming_classes,
    search_attendance_policy as db_search_attendance_policy,
    save_attendance_event as db_save_attendance_event,
    get_attendance_memory as db_get_attendance_memory,
    save_notification as db_save_notification,
)
```

Then replace the internal demo lookups inside the public tools. The public tool names and input shapes should remain stable.

The essential mappings are:

| Member 1 tool | Member 2 facade function |
|---|---|
| `get_student(student_id)` | `db_get_student(student_id)` |
| `get_all_subjects()` | `db_get_all_subjects()` |
| `get_attendance(student_id)` | `get_raw_attendance_summary(student_id)` |
| `get_subject_attendance(student_id, subject_id)` | `get_raw_subject_attendance(student_id, subject_id)` |
| `get_attendance_history(student_id, subject_id)` | `db_get_attendance_history(student_id, subject_id)` |
| `get_timetable(student_id, day)` | `db_get_timetable(day_of_week=resolved_day)` |
| `get_upcoming_classes(student_id, day)` | `db_get_upcoming_classes(day_of_week=resolved_day)` |
| `search_attendance_policy(question)` | `db_search_attendance_policy(question)` |
| `save_attendance_event(event_data)` | `db_save_attendance_event(...)` |
| `get_attendance_memory(student_id)` | `db_get_attendance_memory(student_id)` |
| `save_notification(notification_data)` | `db_save_notification(...)` |

Keep `calculate_recovery()` as a deterministic Python function. The LLM should never calculate the required class count itself.

A simple temporary switch can help debugging:

```python
USE_REAL_BACKEND = os.getenv("USE_REAL_BACKEND", "true").lower() == "true"
```

Use the real facade by default. Keep the demo adapter only as an explicit fallback for offline UI development.

## Step 4: Make the agent return evidence and actions

The existing LangGraph loop already supports model → tool → model. Make the response visibly agentic by returning a structured result containing:

```json
{
  "answer": "DBMS is below the 75% threshold.",
  "goal_status": "ACTION_COMPLETED",
  "evidence": [
    "DBMS attendance: 22/30",
    "Current percentage: 73.33%",
    "Minimum policy threshold: 75%"
  ],
  "decision": "Attend the next recovery classes before taking non-essential leave.",
  "action_taken": {
    "type": "RECOVERY_PLAN_CREATED",
    "status": "SAVED"
  },
  "tool_trace": [
    "get_subject_attendance",
    "calculate_recovery",
    "search_attendance_policy",
    "create_recovery_plan",
    "save_attendance_event"
  ]
}
```

The agent should distinguish between read-only operations and side effects:

| Operation | Examples | Confirmation |
|---|---|---|
| Observe | attendance, timetable, history, memory, policy | Not required |
| Decide | calculate attendance, calculate recovery, assess risk | Not required |
| Plan | create recovery plan, save recovery memory | User request is sufficient |
| Act | save notification, submit leave request | Explicit user confirmation is required |

For example, “Can I take leave tomorrow?” should inspect evidence and make a recommendation. It should not submit leave or send a notification. “Create the recovery plan and remind me tomorrow” may create the plan and queue a notification because the user explicitly requested those actions.

## Step 5: Use explicit goal buttons in the existing UI

The dashboard should not be only a chat box. Add goal-oriented buttons such as:

```text
Analyze my attendance risk
Create my recovery plan
Can I take leave tomorrow?
Show classes I must attend this week
Send me a recovery reminder
```

Each button should send a complete goal to the same agent endpoint.

Add this function to `frontend/services/api.js`:

```javascript
async function askAgent(studentId, message) {
  const base = window.APP_CONFIG?.API_BASE_URL || "http://127.0.0.1:8000";
  const response = await fetch(`${base}/agent/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ student_id: studentId, message })
  });
  if (!response.ok) {
    throw new Error(`Agent request failed: ${response.status}`);
  }
  return await response.json();
}
```

Add `askAgent` to the returned `ApiService` object:

```javascript
return {
  PERIOD_DEFINITIONS,
  fetchProfile,
  fetchTimetable,
  updatePeriodStatus,
  calculateMetrics,
  askAgent
};
```

In `frontend/config.js`, use the actual Member 1 API root:

```javascript
USE_MOCK_DATA: false,
API_BASE_URL: "http://127.0.0.1:8000",
DEFAULT_STUDENT_ID: "S001"
```

Do not use `/api` unless you create matching `/api` routes in FastAPI.

## Step 6: Connect the UI to the agent

Add a small agent panel in `frontend/index.html`:

```html
<section id="agent-panel" class="agent-panel">
  <h2>Attendance Recovery Agent</h2>
  <button data-agent-goal="Analyze my attendance risk">Analyze risk</button>
  <button data-agent-goal="Create my recovery plan">Create recovery plan</button>
  <button data-agent-goal="Can I take leave tomorrow?">Check tomorrow's leave</button>
  <button data-agent-goal="Show classes I must attend this week">Show recovery classes</button>
  <pre id="agent-result">Choose an action to begin.</pre>
</section>
```

Add this to `frontend/app.js` after the existing event handlers are initialized:

```javascript
function initAgentActions() {
  const resultBox = document.getElementById("agent-result");
  document.querySelectorAll("[data-agent-goal]").forEach(button => {
    button.addEventListener("click", async () => {
      const goal = button.dataset.agentGoal;
      resultBox.textContent = "Agent is inspecting attendance, timetable, policy, and memory...";
      try {
        const result = await ApiService.askAgent(state.studentId, goal);
        resultBox.textContent = [
          result.answer || "No answer returned.",
          "",
          `Goal status: ${result.goal_status || "COMPLETED"}`,
          `Tools used: ${(result.tool_trace || []).join(" → ")}`,
          result.action_taken ? `Action: ${JSON.stringify(result.action_taken)}` : ""
        ].filter(Boolean).join("\n");
      } catch (error) {
        resultBox.textContent = `Agent error: ${error.message}`;
      }
    });
  });
}
```

Call `initAgentActions()` inside the existing `DOMContentLoaded` handler.

The UI is now an agent client: it sends goals, waits for tool-driven reasoning, and displays the decision and evidence instead of generating an answer itself.

## Step 7: Add a safe action workflow

For a hackathon, use this policy:

```text
Read-only request:
  execute tools automatically

Recovery-plan request:
  create the plan and save it as an attendance memory event

Notification request:
  show a confirmation button first
  only call save_notification after confirmation

Leave request:
  analyze impact and policy
  never claim official approval without a real approval workflow
```

This prevents the model from silently creating side effects while still making the system proactive.

## Step 8: Run the integrated project

From the repository root, run these commands in separate PowerShell terminals.

Terminal 1 — dependencies and data:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\init_db.py
.\.venv\Scripts\python.exe scripts\build_rag.py
```

Terminal 2 — Ollama:

```powershell
ollama list
```

Confirm that `qwen3:latest` exists. Do not run `ollama serve` a second time if Ollama is already running.

Terminal 3 — agent API:

```powershell
$env:OLLAMA_MODEL="qwen3:latest"
$env:USE_REAL_BACKEND="true"
.\.venv\Scripts\python.exe -m uvicorn agent.api:app --reload --port 8000
```

Terminal 4 — frontend:

```powershell
.\.venv\Scripts\python.exe -m http.server 5500 --directory frontend
```

Open:

```text
http://127.0.0.1:5500
```

## Step 9: Test the agentic behavior

Test the health endpoint:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Test a goal that requires multiple tools:

```powershell
$body = @{ student_id = "S001"; message = "Can I take leave tomorrow? Check my timetable, attendance impact, recovery requirement, policy, and previous warnings before deciding." } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/agent/query -Method Post -ContentType "application/json" -Body $body
```

A valid agentic response should show more than a sentence. It should include a decision and a tool trace similar to:

```text
get_timetable
get_subject_attendance
calculate_recovery
search_attendance_policy
get_attendance_memory
```

Test an action goal:

```powershell
$body = @{ student_id = "S001"; message = "Create a DBMS recovery plan to reach 75 percent and save the plan in my attendance memory." } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/agent/query -Method Post -ContentType "application/json" -Body $body
```

Test a notification confirmation separately. The UI should ask the student to confirm before sending a notification.

## Agentic acceptance criteria

The project qualifies as an agentic attendance system only if all of these are true:

| Criterion | Required behavior |
|---|---|
| Goal understanding | The student can request a real attendance task, not only ask for a definition |
| Tool selection | The model chooses different tools for attendance, timetable, policy, and memory goals |
| Multi-step reasoning | The model uses tool results to select the next tool |
| Deterministic math | Python calculates percentages and required classes |
| Reliable data | Tools call SQLite/RAG/memory, not demo dictionaries |
| Planning | The agent produces a recovery plan based on constraints and upcoming classes |
| Action | The agent saves a plan or notification only when the request permits it |
| Transparency | The UI shows the decision, evidence, and tool trace |
| Safety | Leave is recommended or recorded as pending, never falsely approved |
| Recovery | Tool/API failures are reported clearly and do not become invented answers |

## Recommended hackathon demo

Use one complete story rather than showing random chatbot questions:

```text
1. Student clicks “Analyze my attendance risk.”
2. Agent retrieves all subject attendance.
3. Agent identifies DBMS and Computer Networks as risky.
4. Student clicks “Create my recovery plan.”
5. Agent checks policy, calculates required classes, and checks the timetable.
6. Agent saves the recovery plan in attendance memory.
7. Student clicks “Send recovery reminder.”
8. UI asks for confirmation.
9. Agent saves a HIGH-priority in-app notification.
10. Dashboard shows the updated plan and notification.
```

This demonstrates perception, reasoning, planning, tool use, memory, and action. It is materially different from a chatbot that only generates text.
