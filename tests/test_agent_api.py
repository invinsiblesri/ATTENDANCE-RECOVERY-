from fastapi.testclient import TestClient
from agent.api import app

client = TestClient(app)


def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"


def test_get_all_students():
    res = client.get("/api/students")
    assert res.status_code == 200
    students = res.json()
    assert len(students) == 20
    assert students[0]["student_id"] == "S001"


def test_get_student_s001_details():
    res = client.get("/api/students/S001")
    assert res.status_code == 200
    data = res.json()
    assert data["student"]["student_id"] == "S001"
    assert data["overall_conducted"] == 240
    assert data["overall_attended"] == 189
    assert round(data["overall_percentage"], 2) == 78.75
    assert len(data["subjects"]) == 8


def test_agent_solve_recovery():
    res = client.post("/agent/solve", json={"student_id": "S001", "target_percentage": 80.0})
    assert res.status_code == 200
    data = res.json()
    assert data["student_id"] == "S001"
    assert data["current_overall_percentage"] == 78.75
    assert data["overall_classes_needed"] == 15  # (0.80*240 - 189) / 0.20 = 15
    assert len(data["solutions"]) >= 2
    assert len(data["tool_trace"]) >= 4


def test_simulate_leave():
    res = client.post(
        "/agent/simulate-leave",
        json={
            "student_id": "S001",
            "day_of_week": "Friday",
            "periods": [1, 2, 3, 4, 5, 6, 7, 8],
            "reason": "Family wedding",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["missed_classes_count"] == 8
    assert data["projected_overall_percentage"] < 78.75
    assert "draft_leave_application" in data
    assert data["verdict_badge"] in ["SAFE", "WARNING", "CRITICAL"]


def test_simulate_projection():
    res = client.post(
        "/agent/simulate-projection",
        json={
            "student_id": "S001",
            "future_attended_classes": 10,
            "total_future_classes": 12,
            "target_percentage": 80.0,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["projected_percentage"] > 0
    assert "milestone_text" in data


def test_execute_agent_action():
    res = client.post(
        "/agent/execute-action",
        json={
            "student_id": "S001",
            "action_type": "COMMIT_RECOVERY_PLAN",
            "payload": {"overall_needed": 6, "target": 80.0},
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "memory_id" in data
