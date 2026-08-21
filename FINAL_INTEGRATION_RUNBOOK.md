# Final Integration Runbook — AI Attendance Recovery Agent

## Current repository state

The remote `main` branch already contains the merged project directories from the team branches, and there are currently no open pull requests. The merged project contains `agent/`, `database/`, `rag/`, `memory/`, `notification/`, `frontend/`, `api/`, `scripts/`, and `tests/`.

The commands below are for Windows PowerShell and should be run from the repository root, meaning the folder that contains `requirements.txt`.

## 1. Get the final main branch

For a fresh local copy:

```powershell
cd "C:\Users\sradh\Desktop"
git clone -b main https://github.com/invinsiblesri/ATTENDANCE-RECOVERY-.git attendance-recovery-final
cd attendance-recovery-final
```

If you already have the repository cloned:

```powershell
cd "C:\Users\sradh\Desktop\attendace recovery\ATTENDANCE-RECOVERY-"
git switch main
git pull --ff-only origin main
```

Verify the project root:

```powershell
Get-ChildItem
```

You should see `agent`, `database`, `rag`, `memory`, `notification`, `frontend`, `scripts`, `tests`, and `requirements.txt`.

## 2. Create the virtual environment and install dependencies

If `.venv` does not exist:

```powershell
py -m venv .venv
```

Install the complete dependency set without activating PowerShell scripts:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

This project uses a local Ollama model, so no paid API key is required.

## 3. Initialize the SQLite database

Run:

```powershell
.\.venv\Scripts\python.exe scripts\init_db.py
```

This creates and seeds the local database under `data/`. It should create demo students, eight subjects, timetable records, attendance history, leave records, and notifications.

## 4. Build the local policy RAG index

Run:

```powershell
.\.venv\Scripts\python.exe scripts\build_rag.py
```

This reads the documents in `rag/documents/` and creates the local ChromaDB index under `data/chroma_db/`. It does not call a paid embedding API.

## 5. Run all backend tests

Run the Member 2 test suite:

```powershell
.\.venv\Scripts\python.exe tests\run_all_tests.py
```

Expected result:

```text
ALL TESTS PASSED! (32 tests executed)
```

Run the Member 1 tests as well:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_tools.py
```

Expected result:

```text
9 passed
```

Also run a syntax check:

```powershell
.\.venv\Scripts\python.exe -m compileall -q agent api database rag memory notification
```

No output means the syntax check passed.

## 6. Verify Ollama

Check that the local model exists:

```powershell
ollama list
```

The output must contain:

```text
qwen3:latest
```

If Ollama is already running, do not run `ollama serve` again. If the list command fails, start Ollama once:

```powershell
ollama serve
```

Keep Ollama running in its own terminal.

## 7. Start the Member 1 agent API

Open a second terminal in the repository root and run:

```powershell
$env:OLLAMA_MODEL="qwen3:latest"
.\.venv\Scripts\python.exe -m uvicorn agent.api:app --reload --port 8000
```

Open the health page:

```text
http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "model": "qwen3:latest",
  "backend_mode": "local-demo-adapter"
}
```

Open the API test page:

```text
http://127.0.0.1:8000/docs
```

In Swagger, test `POST /agent/query` with:

```json
{
  "student_id": "S001",
  "message": "What is my DBMS attendance?"
}
```

## 8. Test the local agent from PowerShell

With Ollama and FastAPI running, open another terminal and run:

```powershell
$body = @{ student_id = "S001"; message = "Can I take leave tomorrow?" } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/agent/query -Method Post -ContentType "application/json" -Body $body
```

The response should contain an answer and a `tool_trace`. The trace should use timetable, attendance, recovery, policy, and memory tools when the relevant data exists.

## 9. Start the frontend

Open another terminal in the repository root and run:

```powershell
.\.venv\Scripts\python.exe -m http.server 5500 --directory frontend
```

Open:

```text
http://127.0.0.1:5500
```

The dashboard currently starts in mock-data mode because `frontend/config.js` contains:

```javascript
USE_MOCK_DATA: true
```

This is useful for a reliable UI demonstration. The dashboard is not yet a live SQLite dashboard merely because the branches were merged.

## 10. Important live-integration gap

Before calling the entire system “fully integrated,” verify that Member 1’s tools use Member 2’s real backend functions rather than the demo dictionaries in `agent/tools.py`.

Run these two commands and compare the results:

```powershell
.\.venv\Scripts\python.exe -c "from api.attendance_api import get_raw_attendance_summary; print(get_raw_attendance_summary('S001'))"
```

```powershell
.\.venv\Scripts\python.exe -c "from agent.tools import get_attendance; print(get_attendance.invoke({'student_id':'S001'}))"
```

If the numbers or subject IDs differ, Member 1 is still using demo data. The remaining integration task is to replace the internal demo adapters in `agent/tools.py` with calls to Member 2’s public functions from `api/attendance_api.py`, while keeping the tool names and return JSON shapes stable.

The important Member 2 functions are:

```python
get_student
get_all_subjects
get_raw_attendance_summary
get_raw_subject_attendance
get_attendance_history
get_timetable
get_upcoming_classes
search_attendance_policy
save_attendance_event
get_attendance_memory
save_notification
```

Do not make the language model access SQLite directly. The correct flow is:

```text
Member 1 tool
    ↓
Member 2 public API facade
    ↓
SQLite / ChromaDB / memory store
```

## 11. Frontend live-mode warning

The frontend configuration currently points to URLs under `/api`, while the Member 1 FastAPI application currently exposes `/health` and `/agent/query`. Therefore, do not set `USE_MOCK_DATA: false` until the team creates matching FastAPI adapter routes or changes `frontend/services/api.js` to call the existing routes.

The safest hackathon order is:

1. Demonstrate the live agent through `http://127.0.0.1:8000/docs`.
2. Demonstrate the dashboard through `http://127.0.0.1:5500` in mock mode.
3. Complete the API adapter wiring.
4. Change `USE_MOCK_DATA` to `false`.
5. Test the dashboard against the real backend.

## 12. Git commands after final integration changes

When all integration changes are complete:

```powershell
git switch main
git pull --ff-only origin main
git status
git add .
git commit -m "Integrate agent, database, RAG, memory, notifications, and frontend"
git push origin main
```

Do not commit `.venv/`, `__pycache__/`, `data/chroma_db/`, or local secrets. Confirm that `.gitignore` excludes them before running `git add .`.

## Completion checklist

| Check | Expected result |
|---|---|
| Main branch | Contains all team directories |
| Dependencies | Installation finishes successfully |
| Database | `scripts/init_db.py` creates `data/` database files |
| RAG | `scripts/build_rag.py` creates the local vector index |
| Member 2 tests | 32 tests pass |
| Member 1 tests | 9 tests pass |
| Ollama | `ollama list` shows `qwen3:latest` |
| Agent API | `/health` reports `qwen3:latest` |
| Agent query | `/docs` successfully executes `POST /agent/query` |
| Frontend | `http://127.0.0.1:5500` opens the dashboard |
| Data source | Agent tools return Member 2 SQLite values, not demo dictionaries |
| Live UI | Frontend calls working backend routes with mock mode disabled |
| Git | Final integration is committed to `main` |

The repository is already structurally merged. The two remaining technical checks for a truly single live product are **wiring Member 1’s tools to Member 2’s public API facade** and **aligning the frontend’s `/api` calls with actual FastAPI routes**.
