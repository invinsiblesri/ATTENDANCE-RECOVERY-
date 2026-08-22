import os
import sys
import time
import subprocess
import uvicorn


def free_port(port=8000):
    """Automatically terminates any existing orphan process occupying the specified port."""
    current_pid = os.getpid()
    try:
        output = subprocess.check_output(
            f"netstat -ano | findstr :{port}",
            shell=True,
            text=True,
            stderr=subprocess.DEVNULL
        )
        pids = set()
        for line in output.strip().split("\n"):
            parts = line.strip().split()
            if len(parts) >= 5 and ("LISTENING" in parts or f":{port}" in parts[1]):
                try:
                    pid = int(parts[-1])
                    if pid != current_pid and pid != 0:
                        pids.add(pid)
                except ValueError:
                    continue

        for pid in pids:
            print(f"  [Auto-Recovery] Clearing existing process (PID {pid}) on port {port}...")
            subprocess.run(
                f"taskkill /F /PID {pid}",
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        if pids:
            time.sleep(1)
    except Exception:
        pass


if __name__ == "__main__":
    print("=" * 65)
    print("  AttendAI - 100% Agentic AI Attendance Recovery System")
    print("  Initializing server environment on http://localhost:8000 ...")
    print("=" * 65)
    
    # Auto-release port 8000 to avoid Errno 10048 socket collision
    free_port(8000)
    
    print("  [OK] Port 8000 ready. Starting FastAPI Multi-Agent Engine...")
    print("  Open your browser at: http://localhost:8000")
    print("=" * 65)

    uvicorn.run("agent.api:app", host="0.0.0.0", port=8000, reload=False, workers=1)
