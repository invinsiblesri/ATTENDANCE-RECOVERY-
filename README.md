# AI Attendance Recovery Agent

## Purpose

This project is the **Member 1 AI Agent / Brain module** for a four-member hackathon system. It uses a local Ollama model and LangGraph to understand a student’s request, select the correct tool, execute deterministic attendance operations, and return a clear answer or recovery action. No paid API is required.

The important engineering principle is to keep the language model responsible for **intent understanding and tool selection**, while keeping attendance calculations, policy enforcement, timetable filtering, and notifications in ordinary Python services. This prevents the model from inventing numbers or making policy decisions that should be auditable.

> The final product should be presented as an agent that reasons over trusted academic data, not as a chatbot that guesses attendance values.

## Recommended free architecture

Use Python, FastAPI, LangGraph, LangChain’s Ollama integration, Ollama, and a locally downloaded open-source model such as `qwen3:latest`. The model runs on the team’s own computer through Ollama, so the application does not send student information to a paid cloud API. Ollama documents both function/tool calling and multi-turn tool loops, which match this project’s required behavior [1]. Ollama also supports structured JSON output, and its documentation recommends schema validation with Pydantic for reliable structured responses [2]. LangGraph is useful here because it combines deterministic nodes with model-driven nodes in one explicit workflow [3]. FastAPI and Pydantic provide a typed HTTP contract and automatic request validation for the final integration endpoint [4].

| Component | Responsibility | Free implementation | Owner |
|---|---|---|---|
| Local LLM runtime | Run the language model on a laptop | Ollama + `qwen3:latest` | Member 1 |
| Agent orchestration | Model/tool loop and state transitions | LangGraph + LangChain | Member 1 |
| Attendance and timetable data | Return authoritative student records | SQLite/PostgreSQL/CSV adapter | Member 2 |
| Policy and calculations | Store policy and expose safe business rules | Python service or backend API | Member 2 |
| Notifications | Display or queue reminders | Local console/in-app/email adapter | Member 3 or 4 |
| User interface | Student chat and plan display | Team-selected frontend | Member 4 |
| Integration boundary | Stable request/response API | `POST /agent/query` | Member 1 |

## Agent workflow

The workflow is intentionally explicit:

```text
User message + student_id
        |
        v
Local LLM understands intent
        |
        v
LLM requests one or more typed tools
        |
        v
ToolNode executes trusted Python adapters
        |
        v
Tool result is returned to the LLM
        |
        v
LLM decides whether another tool is needed
        |
        +---- another tool call ----> ToolNode
        |
        +---- no tool call ----------> final answer
```

Typical examples are:

| User request | Expected tool sequence |
|---|---|
| “What is my attendance in CS101?” | `get_attendance` |
| “How many classes do I need to attend to reach 75%?” | `calculate_attendance` |
| “Am I allowed to recover CS101?” | `get_attendance` → `check_policy` → possibly `calculate_attendance` |
| “Create a recovery plan for CS101.” | `create_recovery_plan` |
| “What CS101 classes are coming up?” | `get_timetable` |
| “Create a plan and remind me tomorrow.” | `create_recovery_plan` → explicit confirmation or `trigger_notification` according to the team’s product decision |

The model should never perform the attendance arithmetic itself. For example, `calculate_attendance` computes the smallest integer `n` satisfying:

```text
(present + n) / (total + n) >= target_percentage / 100
```

The tool returns the calculation as structured JSON, and the model explains it in natural language.

## Member 1 responsibilities

Your work is complete when the following items are implemented and demonstrated:

| Deliverable | Acceptance condition |
|---|---|
| Ollama connection | A local model answers through the application without a cloud API key |
| Tool schemas | All six tools have names, descriptions, typed arguments, and predictable JSON results |
| Agent graph | The model can call tools, receive results, call another tool, and stop with a final response |
| Prompt rules | The agent never fabricates data and does not notify unless the user requests it |
| Business-safe calculations | Percentage and recovery math is deterministic and tested |
| Public API | Other members can call `POST /agent/query` without importing LangGraph internals |
| Tests | Tool behavior works even if Ollama is unavailable |
| Integration document | The other three members know the exact request and response shapes |

## Project structure

```text
attendance-recovery-agent/
├── agent/
│   ├── __init__.py       # Package exports
│   ├── agent.py          # Stable AttendanceAgent facade
│   ├── api.py            # FastAPI integration endpoint
│   ├── graph.py          # LangGraph model/tool workflow
│   ├── models.py         # Shared Pydantic contracts
│   ├── prompts.py        # System behavior and safety rules
│   └── tools.py          # Six tools and replaceable adapters
├── tests/
│   └── test_tools.py     # Deterministic unit tests
├── requirements.txt
└── README.md
```

## Local installation

Install Ollama from the official [Ollama website](https://ollama.com/), then download the selected local model. The commands below are intentionally simple:

```bash
ollama pull qwen3:latest
ollama list
```

Create a Python virtual environment and install the project packages:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Start Ollama if it is not already running:

```bash
ollama serve
```

In a second terminal, start the API from the project root:

```bash
source .venv/bin/activate
uvicorn agent.api:app --reload --port 8000
```

If the team chooses a different local model, set it without changing application code:

```bash
export OLLAMA_MODEL=qwen3:latest
```

Choose a model that fits the available laptop memory. The application design deliberately isolates the model name in an environment variable.

## Public integration contract

The frontend or another backend member should call only this endpoint:

```http
POST http://localhost:8000/agent/query
Content-Type: application/json
```

Request:

```json
{
  "student_id": "S001",
  "message": "Create a recovery plan for CS101 to reach 75 percent"
}
```

Response:

```json
{
  "answer": "You are currently at 66.67% in Introduction to Computer Science. You need to attend 6 additional classes to mathematically reach 75%. The policy allows a maximum recommendation of 3 recovery classes per week, so I recommend starting with the next three CS101 classes...",
  "student_id": "S001",
  "tool_trace": [
    "create_recovery_plan"
  ]
}
```

The `tool_trace` field is useful for the hackathon demo and debugging. In a production system, expose only a safe, user-friendly trace or remove it from the public response.

Health check:

```http
GET http://localhost:8000/health
```

Example frontend call:

```javascript
const response = await fetch("http://localhost:8000/agent/query", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    student_id: "S001",
    message: userMessage
  })
});

const data = await response.json();
```

## Six tool contracts

The current file uses local demo dictionaries. Member 2 should replace only the internal data access sections while preserving these public tool signatures and return shapes.

| Tool | Required input | Responsibility | Side effect |
|---|---|---|---|
| `get_attendance` | `student_id`, optional `course_id` | Retrieve current attendance records | None |
| `get_timetable` | optional `course_id`, `days` | Retrieve upcoming classes | None |
| `calculate_attendance` | `student_id`, `course_id`, `target_percentage` | Perform exact recovery math | None |
| `check_policy` | `course_id` | Retrieve minimum percentage and limits | None |
| `create_recovery_plan` | `student_id`, `course_id`, `target_percentage` | Combine data and generate a constrained plan | None |
| `trigger_notification` | `student_id`, `message`, `channel` | Queue or send a reminder | Yes; must be explicitly requested |

A critical integration rule is that **the function names and JSON keys are the API**. Other members may refactor the database, frontend, or notification implementation, but they should not casually rename fields during the hackathon. If a field must change, update the shared contract first and run the integration tests.

## How the other three members connect

### Member 2: data and backend member

Member 2 should implement repository functions or HTTP adapters for attendance, timetable, and policy data. The cleanest first integration is an in-process adapter: replace `_ATTENDANCE`, `_TIMETABLE`, and `_POLICIES` in `agent/tools.py` with calls to Member 2’s repository. The tool functions should continue returning JSON strings with the same logical fields.

If Member 2 runs a separate backend, set environment variables such as `ATTENDANCE_SERVICE_URL` and use `httpx` inside the tool adapter. Do not make the LLM call Member 2’s database directly. The tool layer is the boundary that validates inputs and handles service errors.

### Member 3: notification or policy member

Member 3 should implement the notification endpoint or adapter. The existing `trigger_notification` function first checks `NOTIFICATION_SERVICE_URL`; if it is set, it posts to:

```http
POST {NOTIFICATION_SERVICE_URL}/notifications
Content-Type: application/json
```

Request:

```json
{
  "student_id": "S001",
  "message": "Your attendance recovery reminder is ready.",
  "channel": "in_app"
}
```

Expected response:

```json
{
  "notification_id": "n-123",
  "student_id": "S001",
  "channel": "in_app",
  "status": "queued",
  "message": "Your attendance recovery reminder is ready."
}
```

Until that service exists, the local fallback prints and returns a queued notification result. This makes the agent demonstrable even before the integration is complete.

### Member 4: frontend and presentation member

Member 4 should treat the agent as a normal JSON API. The UI should collect or know the authenticated student ID, send the student message, display `answer`, and optionally render a recovery plan card when the answer contains a plan. The UI should not duplicate attendance calculations; it should display the values returned by the agent or a dedicated backend endpoint.

For the live demo, prepare four buttons or example prompts: “Show my attendance,” “How many classes do I need?”, “Create my recovery plan,” and “Remind me about this plan.” This demonstrates both read-only reasoning and an explicit action tool.

## Final integration procedure

Use one shared Git repository and one integration branch. Each member should commit against a small shared contract document before merging implementation changes.

| Stage | Action | Owner |
|---|---|---|
| 1 | Agree on the JSON request and response shapes in this README | All members |
| 2 | Member 1 runs the agent with demo adapters | Member 1 |
| 3 | Member 2 replaces demo attendance/timetable/policy adapters | Member 2 |
| 4 | Member 3 connects the notification endpoint or keeps the local fallback | Member 3 |
| 5 | Member 4 connects the frontend to `/agent/query` | Member 4 |
| 6 | Run unit tests and API smoke tests on one laptop | All members |
| 7 | Freeze the demo dataset and rehearse the exact user journey | All members |

The recommended demo journey is: a student asks why attendance is low, the agent retrieves the record, calculates the required classes, checks the policy, creates a plan from the timetable, and then sends a reminder only after the student explicitly asks for one.

## Testing strategy

Run the deterministic tests before starting Ollama:

```bash
pytest -q
```

These tests validate the most important business behavior without using an LLM. This is essential because an unavailable model should not prevent the team from testing policy and calculation correctness.

After starting the API and Ollama, run a smoke request:

```bash
curl -X POST http://localhost:8000/agent/query \
  -H "Content-Type: application/json" \
  -d '{"student_id":"S001","message":"Create a recovery plan for CS101 to reach 75 percent"}'
```

The team should test at least the following cases:

| Case | Expected behavior |
|---|---|
| Existing course | Returns authoritative attendance |
| Missing course | Asks for a course ID or reports no record |
| Already above target | Says zero additional classes are needed |
| Recovery exceeds weekly limit | Returns a warning and caps the recommendation |
| No timetable entries | Explains that a plan cannot be scheduled immediately |
| Notification not requested | Does not call `trigger_notification` |
| Notification requested | Returns a queued or sent result |
| Invalid request body | FastAPI returns a validation error |
| Ollama unavailable | Health or integration request reports an execution error while deterministic tests still pass |

## Safety and reliability rules for the demo

The agent must not expose private student data to anyone except the authenticated student or an authorized staff user. In the hackathon version, the frontend can pass a fixed demo student ID, but the final explanation should state that a real deployment would derive the ID from authentication rather than trusting arbitrary client input.

Do not allow the model to change attendance records, alter policy, or send notifications without an explicit user request. Read operations and calculations should be automatic; side-effecting operations should be separately logged and easy to disable. Keep the model’s temperature at zero for predictable tool selection, and log tool errors without storing unnecessary personal data.

## Two viable execution choices

| Approach | Tradeoffs | Cost | Setup complexity |
|---|---|---:|---:|
| One local FastAPI process containing the agent and adapters | Fastest hackathon integration, no network dependency between members, easiest demo; all members must coordinate one repository | Free, except local electricity/hardware | Low |
| Separate local services for agent, data, notifications, and frontend | Better separation of responsibilities and closer to production architecture; more ports, configuration, and failure cases | Free when run on team laptops | Medium to high |

For a short hackathon, begin with the **single-process architecture**, then keep the HTTP contracts so services can be separated later without rewriting the agent graph.

## What to say in the presentation

“Our system uses a local open-source language model only for language understanding and tool selection. It never guesses attendance or policy values. The tools retrieve trusted data and perform deterministic calculations. LangGraph coordinates the loop from user request to tool call to tool result to final answer. Because the model runs through Ollama on our own machine, the prototype uses no paid AI API.”

## References

[1]: https://docs.ollama.com/capabilities/tool-calling "Ollama tool calling documentation"

[2]: https://docs.ollama.com/capabilities/structured-outputs "Ollama structured outputs documentation"

[3]: https://docs.langchain.com/oss/python/langgraph/overview "LangGraph overview documentation"

[4]: https://fastapi.tiangolo.com/tutorial/body/ "FastAPI request body and Pydantic documentation"
