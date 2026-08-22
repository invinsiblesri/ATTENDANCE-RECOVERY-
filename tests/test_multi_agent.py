from agent.multi_agent import (
    SentinelMonitorAgent,
    RecoveryMathAgent,
    LeaveSimulationAgent,
    PolicyRAGAgent,
    MultiAgentOrchestrator,
    multi_agent_system,
)
from fastapi.testclient import TestClient
from agent.api import app

client = TestClient(app)


def test_sentinel_monitor_agent_detection():
    sentinel = SentinelMonitorAgent()
    res = sentinel.audit_and_alert("S001")
    assert res["agent"] == "SentinelMonitorAgent"
    assert res["student_id"] == "S001"
    assert res["overall_rate"] == 78.75
    assert len(res["critical_subjects"]) >= 1  # DBMS / CN is below 75%


def test_recovery_math_agent_exact_formula():
    math_agent = RecoveryMathAgent()
    # (0.80 * 240 - 189) / 0.20 = 15
    needed = math_agent.calculate_needed_classes(attended=189, conducted=240, target_pct=80.0)
    assert needed == 15

    sol = math_agent.solve_student_recovery("S001", target_percentage=80.0)
    assert sol["overall_classes_needed"] == 15
    assert len(sol["subject_breakdown"]) == 8


def test_leave_simulation_agent():
    leave_agent = LeaveSimulationAgent()
    sim = leave_agent.simulate("S001", day_of_week="Friday")
    assert sim["missed_classes_count"] == 8
    assert sim["projected_percentage"] < sim["current_percentage"]
    assert sim["verdict"] in ["SAFE", "WARNING", "CRITICAL"]


def test_policy_rag_agent():
    policy_agent = PolicyRAGAgent()
    results = policy_agent.query_policy("exam eligibility and condonation")
    assert len(results) >= 1
    assert "source" in results[0]


def test_orchestrator_recovery_query():
    res = multi_agent_system.process_query("S001", "How many classes do I need to attend to get a 80% attendance?")
    assert res["active_agent"] == "🧮 Recovery Calculation Agent"
    assert res["overall_classes_needed"] == 15
    assert "15 consecutive upcoming classes" in res["answer"]
    assert res["action_type"] == "COMMIT_RECOVERY_PLAN"


def test_orchestrator_leave_query():
    res = multi_agent_system.process_query("S001", "Can I take leave on Friday? What is the impact?")
    assert res["active_agent"] == "🏖️ Leave Simulation Agent"
    assert "Planned Leave Day" in res["answer"]
    assert res["action_type"] == "APPLY_LEAVE"


def test_orchestrator_risky_query():
    res = multi_agent_system.process_query("S001", "Which subjects are risky and below 75%?")
    assert res["active_agent"] == "🕵️ Sentinel Monitor Agent"
    assert "Critical Shortage Subjects" in res["answer"]


def test_api_query_with_multi_agent():
    res = client.post(
        "/agent/query",
        json={"student_id": "S001", "message": "How many classes do I need to attend to reach 80%?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "15" in data["answer"]
    assert data["active_agent"] == "🧮 Recovery Calculation Agent"
    assert data["action_type"] == "COMMIT_RECOVERY_PLAN"
