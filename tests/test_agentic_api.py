import unittest

from fastapi.testclient import TestClient

from agent.api import app
from database.connection import DatabaseManager
from database.seed import seed_database


class TestAgenticApi(unittest.TestCase):
    """Verify that the product exposes evidence-led operations, not a text-only chatbot."""

    @classmethod
    def setUpClass(cls):
        seed_database(DatabaseManager())
        cls.client = TestClient(app)

    def test_dashboard_exposes_real_attendance_evidence(self):
        response = self.client.get("/dashboard/S001")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["student"]["student_id"], "S001")
        self.assertEqual(len(body["subjects"]), 8)
        self.assertIn("percentage", body["overall"])

    def test_risk_goal_returns_decision_evidence_and_tool_trace(self):
        response = self.client.post("/agent/query", json={
            "student_id": "S001",
            "goal": "risk",
            "message": "Analyze the attendance risk.",
        })
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["goal"], "risk")
        self.assertEqual(body["goal_status"], "COMPLETED")
        self.assertTrue(body["evidence"])
        self.assertIn("get_attendance", body["tool_trace"])
        self.assertEqual(body["action"]["type"], "RISK_ASSESSMENT")

    def test_notification_goal_requires_confirmation_before_side_effect(self):
        pending = self.client.post("/agent/query", json={
            "student_id": "S001",
            "goal": "notification",
            "subject_id": "SUB003",
            "message": "Prepare a recovery reminder.",
        })
        self.assertEqual(pending.status_code, 200)
        self.assertEqual(pending.json()["goal_status"], "NEEDS_CONFIRMATION")
        self.assertEqual(pending.json()["action"]["status"], "PENDING_CONFIRMATION")

        confirmed = self.client.post("/agent/query", json={
            "student_id": "S001",
            "goal": "notification",
            "subject_id": "SUB003",
            "confirmed": True,
            "message": "Confirm the recovery reminder.",
        })
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(confirmed.json()["goal_status"], "COMPLETED")
        self.assertEqual(confirmed.json()["action"]["type"], "NOTIFICATION_SAVED")


if __name__ == "__main__":
    unittest.main()
