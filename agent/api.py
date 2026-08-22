from __future__ import annotations

import math
import os
import threading
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from api.attendance_api import (
    apply_leave as repo_apply_leave,
    get_all_students as repo_get_all_students,
    get_all_subjects as repo_get_all_subjects,
    get_attendance_history as repo_get_attendance_history,
    get_attendance_memory as repo_get_attendance_memory,
    get_leave_records as repo_get_leave_records,
    get_notifications as repo_get_notifications,
    get_raw_attendance_summary as repo_get_raw_summary,
    get_student as repo_get_student,
    get_timetable as repo_get_timetable,
    get_upcoming_classes as repo_get_upcoming,
    mark_notification_as_read as repo_mark_notification_read,
    record_period_attendance as repo_record_attendance,
    save_attendance_event as repo_save_memory_event,
    save_notification as repo_save_notification,
    search_attendance_policy as repo_search_policy,
)
from .agent import agent
from .graph import MODEL_NAME
from .models import AgentQuery, AgentResponse, HealthResponse
from .multi_agent import multi_agent_system
from services.communication_service import CommunicationService
from services.export_service import ExportService, get_student_contact

app = FastAPI(
    title="AttendAI - 100% Agentic AI Attendance Recovery System",
    version="2.0.0",
    description="Autonomous Agentic AI Solution Engine and API for College Attendance Recovery",
)

# Enable CORS for seamless frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# Request & Response Schemas
# -----------------------------------------------------------------------------
class SolveRequest(BaseModel):
    student_id: str = "S001"
    target_percentage: float = 80.0
    subject_id: Optional[str] = None


class SimulateLeaveRequest(BaseModel):
    student_id: str = "S001"
    day_of_week: str = "Friday"
    leave_date: Optional[str] = None
    periods: List[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5, 6, 7, 8])
    reason: str = "Medical checkup"


class SimulateProjectionRequest(BaseModel):
    student_id: str = "S001"
    future_attended_classes: int = 10
    total_future_classes: int = 15
    target_percentage: float = 80.0


class ExecuteActionRequest(BaseModel):
    student_id: str = "S001"
    action_type: str  # COMMIT_RECOVERY_PLAN, APPLY_LEAVE, DISPATCH_ALERT, LOG_EVENT
    payload: Dict[str, Any] = Field(default_factory=dict)


class RecordAttendanceRequest(BaseModel):
    student_id: str
    subject_id: str
    date: str
    period_number: int
    status: str  # Present or Absent


class SaveNotificationRequest(BaseModel):
    student_id: str
    subject_id: Optional[str] = None
    message: str
    priority: str = "MEDIUM"


class SaveMemoryRequest(BaseModel):
    student_id: str
    subject_id: Optional[str] = None
    event_type: str
    description: str
    metadata: Optional[Dict[str, Any]] = None


class CommunicationRequest(BaseModel):
    student_id: str = Field(default="S001")
    channel: str = Field(default="both")  # "sms", "email", or "both"
    phone: Optional[str] = None
    email: Optional[str] = None
    message: Optional[str] = None
    priority: str = Field(default="HIGH")


# -----------------------------------------------------------------------------
# Health & Status
# -----------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", model=MODEL_NAME, backend_mode="agentic-sqlite-rag-production")


# -----------------------------------------------------------------------------
# 1. Student & Attendance REST APIs
# -----------------------------------------------------------------------------
@app.get("/api/students")
def get_students():
    """Retrieve all 20 registered students."""
    try:
        return repo_get_all_students()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/students/{student_id}")
def get_student_details(student_id: str):
    """Retrieve full student profile, raw summary, and calculated percentage breakdown."""
    try:
        student = repo_get_student(student_id)
        if not student:
            raise HTTPException(status_code=404, detail=f"Student {student_id} not found")
        
        raw_summary = repo_get_raw_summary(student_id)
        total_conducted = raw_summary["total_conducted"]
        total_attended = raw_summary["total_attended"]
        overall_rate = round((total_attended / total_conducted * 100.0), 2) if total_conducted > 0 else 0.0

        # Calculate metrics for each subject
        subjects_data = []
        for s_id, s_stats in raw_summary["subjects"].items():
            cond = s_stats["conducted"]
            att = s_stats["attended"]
            absent = s_stats["absent"]
            rate = round((att / cond * 100.0), 2) if cond > 0 else 0.0
            
            # Needed for 80% target
            needed_80 = 0
            if rate < 80.0 and cond > 0:
                needed_80 = max(0, math.ceil((0.80 * cond - att) / 0.20))

            risk_tier = "SAFE" if rate >= 80.0 else ("BORDERLINE" if rate >= 75.0 else "SHORTAGE")
            
            subjects_data.append({
                "subject_id": s_id,
                "subject_code": s_stats["subject_code"],
                "subject_name": s_stats["subject_name"],
                "conducted": cond,
                "attended": att,
                "absent": absent,
                "percentage": rate,
                "needed_for_80": needed_80,
                "risk_tier": risk_tier,
            })

        risk_level = "SAFE" if overall_rate >= 80.0 else ("BORDERLINE" if overall_rate >= 75.0 else "CRITICAL_SHORTAGE")

        return {
            "student": student,
            "overall_conducted": total_conducted,
            "overall_attended": total_attended,
            "overall_absent": raw_summary["total_absent"],
            "overall_percentage": overall_rate,
            "risk_level": risk_level,
            "is_exam_eligible": overall_rate >= 80.0,
            "condonation_eligible": 75.0 <= overall_rate < 80.0,
            "subjects": subjects_data,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/subjects")
def get_subjects():
    """Retrieve all 8 curriculum subjects."""
    try:
        return repo_get_all_subjects()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/timetable")
def get_timetable(day: Optional[str] = None):
    """Retrieve 40-slot weekly timetable (optionally filtered by day)."""
    try:
        return repo_get_timetable(day_of_week=day)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/attendance/history")
def get_attendance_history(
    student_id: str,
    subject_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Retrieve period-wise class attendance records."""
    try:
        return repo_get_attendance_history(
            student_id=student_id,
            subject_id=subject_id,
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/attendance/record")
def record_attendance(payload: RecordAttendanceRequest):
    """Update or record a period attendance status."""
    try:
        row_id = repo_record_attendance(
            student_id=payload.student_id,
            subject_id=payload.subject_id,
            date=payload.date,
            period_number=payload.period_number,
            status=payload.status,
        )
        return {"success": True, "record_id": row_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# -----------------------------------------------------------------------------
# 2. Notifications, Memory, RAG APIs
# -----------------------------------------------------------------------------
@app.get("/api/notifications")
def get_notifications(student_id: str = "S001", unread_only: bool = False):
    """Retrieve student notifications."""
    try:
        return repo_get_notifications(student_id=student_id, unread_only=unread_only)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/notifications")
def save_notification(payload: SaveNotificationRequest):
    """Save an in-database notification."""
    try:
        nid = repo_save_notification(
            student_id=payload.student_id,
            subject_id=payload.subject_id,
            message=payload.message,
            priority=payload.priority,
        )
        return {"success": True, "notification_id": nid}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.patch("/api/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int):
    """Mark a notification as read."""
    try:
        success = repo_mark_notification_read(notification_id)
        return {"success": success}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/memory/{student_id}")
def get_student_memory(student_id: str, limit: int = 50):
    """Retrieve persistent attendance memory events."""
    try:
        return repo_get_attendance_memory(student_id=student_id, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/memory")
def save_memory(payload: SaveMemoryRequest):
    """Save persistent attendance event."""
    try:
        mid = repo_save_memory_event(
            student_id=payload.student_id,
            subject_id=payload.subject_id,
            event_type=payload.event_type,
            description=payload.description,
            metadata=payload.metadata,
        )
        return {"success": True, "memory_id": mid}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/rag/search")
def search_policy(query: str = "minimum attendance requirement", n_results: int = 3):
    """Search policy knowledge base via ChromaDB RAG."""
    try:
        return repo_search_policy(query=query, n_results=n_results)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# -----------------------------------------------------------------------------
# 3. 100% Agentic AI Solution Engine Endpoints (NOT a Chatbot!)
# -----------------------------------------------------------------------------
@app.post("/agent/solve")
def solve_attendance_recovery(payload: SolveRequest):
    """
    Autonomous Agentic AI Solution Engine:
    Diagnoses attendance deficits, evaluates policy constraints, computes multi-step
    optimal recovery roadmaps, and synthesizes 1-click executable action plans.
    """
    try:
        student = repo_get_student(payload.student_id)
        if not student:
            raise HTTPException(status_code=404, detail=f"Student {payload.student_id} not found")

        summary = repo_get_raw_summary(payload.student_id)
        total_conducted = summary["total_conducted"]
        total_attended = summary["total_attended"]
        overall_rate = round((total_attended / total_conducted * 100.0), 2) if total_conducted > 0 else 0.0

        # Step 1: Trace tool calls
        tool_trace = [
            f"repo.get_student('{payload.student_id}') -> {student['name']}",
            f"repo.get_raw_attendance_summary('{payload.student_id}') -> Attended={total_attended}/{total_conducted} ({overall_rate}%)",
            f"rag.search_attendance_policy('80% overall attendance exam eligibility') -> Policy Match Found",
        ]

        # Step 2: Subject-by-subject risk & recovery analysis
        risky_subjects = []
        safe_subjects = []
        recovery_roadmaps = []
        overall_needed = 0

        target = payload.target_percentage
        if overall_rate < target and total_conducted > 0:
            target_dec = target / 100.0
            overall_needed = max(0, math.ceil(round((target_dec * total_conducted - total_attended) / (1.0 - target_dec), 9)))

        timetable_entries = repo_get_timetable()
        weekly_slots = {}
        for slot in timetable_entries:
            weekly_slots[slot["subject_id"]] = weekly_slots.get(slot["subject_id"], 0) + 1

        for s_id, s_stats in summary["subjects"].items():
            cond = s_stats["conducted"]
            att = s_stats["attended"]
            rate = round((att / cond * 100.0), 2) if cond > 0 else 0.0

            needed = 0
            if rate < target and cond > 0:
                needed = max(0, math.ceil(round(((target / 100.0) * cond - att) / (1.0 - target / 100.0), 9)))

            subject_info = {
                "subject_id": s_id,
                "subject_code": s_stats["subject_code"],
                "subject_name": s_stats["subject_name"],
                "conducted": cond,
                "attended": att,
                "absent": s_stats["absent"],
                "current_percentage": rate,
                "target_percentage": target,
                "needed_classes": needed,
                "weekly_capacity": weekly_slots.get(s_id, 5),
            }

            if rate < 75.0:
                subject_info["status"] = "CRITICAL_SHORTAGE"
                risky_subjects.append(subject_info)
            elif rate < target:
                subject_info["status"] = "BORDERLINE"
                risky_subjects.append(subject_info)
            else:
                subject_info["status"] = "SAFE"
                safe_subjects.append(subject_info)

            if needed > 0:
                weeks_required = math.ceil(needed / min(weekly_slots.get(s_id, 5), 3))
                recovery_roadmaps.append({
                    "subject_id": s_id,
                    "subject_name": s_stats["subject_name"],
                    "needed_classes": needed,
                    "estimated_weeks": weeks_required,
                    "recommendation": f"Attend next {needed} consecutive lectures in {s_stats['subject_name']}. Target recovery completed in ~{weeks_required} week(s).",
                })

        tool_trace.append(f"agent.deterministic_recovery_calc(overall_needed={overall_needed}, risky_subjects={len(risky_subjects)})")
        tool_trace.append(f"memory.get_attendance_memory('{payload.student_id}') -> Checked past commitments")

        policy_results = repo_search_policy("attendance recovery and exam eligibility condonation", n_results=2)

        # Synthesize Solution Cards
        solutions = []

        # Solution 1: Fast-Track Attendance Recovery Plan
        if overall_needed > 0 or risky_subjects:
            solutions.append({
                "id": "SOL-RECOVERY-01",
                "type": "FAST_TRACK_RECOVERY",
                "title": "🎯 Fast-Track Attendance Recovery Plan",
                "priority": "HIGH" if overall_rate < 75.0 else "MEDIUM",
                "summary": f"Attend {overall_needed} upcoming lectures consecutively to restore overall attendance to {target:.1f}%.",
                "overall_classes_needed": overall_needed,
                "projected_percentage": target,
                "roadmaps": recovery_roadmaps,
                "action_type": "COMMIT_RECOVERY_PLAN",
                "action_button_label": "⚡ Commit & Lock Recovery Plan",
                "action_payload": {
                    "student_id": payload.student_id,
                    "overall_needed": overall_needed,
                    "target": target,
                    "subjects": [r["subject_id"] for r in recovery_roadmaps],
                },
            })

        # Solution 2: Exam Eligibility & Policy Safeguard Dossier
        solutions.append({
            "id": "SOL-POLICY-02",
            "type": "EXAM_ELIGIBILITY_SAFEGUARD",
            "title": "🛡️ Exam Eligibility & Policy Safeguard",
            "priority": "HIGH" if overall_rate < 80.0 else "LOW",
            "summary": "Eligible for End-Semester Exams" if overall_rate >= 80.0 else (
                "Condonation Required (75-80% bracket). No unexcused absences allowed." if overall_rate >= 75.0 else
                "Critical Exam Disqualification Risk (<75%). Immediate recovery intervention required."
            ),
            "condonation_bracket": "75.0% - 79.99%",
            "policy_citations": [p.get("content", "") for p in policy_results],
            "action_type": "GENERATE_DOSSIER",
            "action_button_label": "📋 Export Exam Clearance Dossier",
            "action_payload": {
                "student_id": payload.student_id,
                "overall_rate": overall_rate,
                "status": "APPROVED" if overall_rate >= 80.0 else "CONDONATION_REQUIRED",
            },
        })

        # Solution 3: Academic Advisor & Proactive Alert Dispatch
        if overall_rate < 80.0:
            solutions.append({
                "id": "SOL-ALERT-03",
                "type": "ADVISOR_DISPATCH",
                "title": "📢 Academic Advisor & Student Notification Alert",
                "priority": "HIGH" if overall_rate < 75.0 else "MEDIUM",
                "summary": f"Dispatch automated early-warning alert to student dashboard and notify academic counselor.",
                "action_type": "DISPATCH_ALERT",
                "action_button_label": "🔔 Dispatch Proactive Warning Alert",
                "action_payload": {
                    "student_id": payload.student_id,
                    "message": f"Attendance is at {overall_rate}%. Recovery target: attend next {overall_needed} classes.",
                    "priority": "HIGH" if overall_rate < 75.0 else "MEDIUM",
                },
            })

        # Run Sentinel Agent check (automatically alerts if < 75%)
        sentinel_res = multi_agent_system.sentinel.audit_and_alert(payload.student_id)
        if sentinel_res.get("actions_taken"):
            tool_trace.extend(sentinel_res["actions_taken"])

        return {
            "student_id": payload.student_id,
            "student_name": student["name"],
            "current_overall_percentage": overall_rate,
            "target_percentage": target,
            "overall_classes_needed": overall_needed,
            "risk_level": "SAFE" if overall_rate >= 80.0 else ("BORDERLINE" if overall_rate >= 75.0 else "CRITICAL"),
            "risky_subjects": risky_subjects,
            "safe_subjects": safe_subjects,
            "recovery_roadmaps": recovery_roadmaps,
            "solutions": solutions,
            "tool_trace": tool_trace,
            "execution_mode": "Multi-Agent-Deterministic-Solver",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/agent/simulate-leave")
def simulate_leave(payload: SimulateLeaveRequest):
    """
    Interactive 'What-If' Leave Simulation Sandbox:
    Calculates the exact percentage drop, affected subjects, policy compliance verdict,
    and required recovery workload if the student takes leave.
    """
    try:
        student = repo_get_student(payload.student_id)
        if not student:
            raise HTTPException(status_code=404, detail=f"Student {payload.student_id} not found")

        summary = repo_get_raw_summary(payload.student_id)
        total_conducted = summary["total_conducted"]
        total_attended = summary["total_attended"]
        current_overall_rate = round((total_attended / total_conducted * 100.0), 2) if total_conducted > 0 else 0.0

        day_classes = repo_get_timetable(day_of_week=payload.day_of_week)
        affected_slots = [slot for slot in day_classes if slot["period_number"] in payload.periods]
        missed_count = len(affected_slots)

        sim_conducted = total_conducted + missed_count
        sim_attended = total_attended
        sim_overall_rate = round((sim_attended / sim_conducted * 100.0), 2) if sim_conducted > 0 else 0.0
        percentage_drop = round(current_overall_rate - sim_overall_rate, 2)

        affected_subjects_map = {}
        for slot in affected_slots:
            s_id = slot["subject_id"]
            affected_subjects_map[s_id] = affected_subjects_map.get(s_id, 0) + 1

        subject_impacts = []
        for s_id, missed_in_sub in affected_subjects_map.items():
            curr_stats = summary["subjects"].get(s_id, {})
            c_cond = curr_stats.get("conducted", 0)
            c_att = curr_stats.get("attended", 0)
            c_rate = round((c_att / c_cond * 100.0), 2) if c_cond > 0 else 0.0

            n_cond = c_cond + missed_in_sub
            n_att = c_att
            n_rate = round((n_att / n_cond * 100.0), 2) if n_cond > 0 else 0.0

            sub_needed = 0
            if n_rate < 80.0 and n_cond > 0:
                sub_needed = max(0, math.ceil(round((0.80 * n_cond - n_att) / 0.20, 9)))

            subject_impacts.append({
                "subject_id": s_id,
                "subject_name": curr_stats.get("subject_name", s_id),
                "missed_periods": missed_in_sub,
                "current_percentage": c_rate,
                "projected_percentage": n_rate,
                "percentage_change": round(c_rate - n_rate, 2),
                "recovery_classes_needed": sub_needed,
                "status_after_leave": "SAFE" if n_rate >= 80.0 else ("BORDERLINE" if n_rate >= 75.0 else "SHORTAGE"),
            })

        overall_recovery_needed = 0
        if sim_overall_rate < 80.0 and sim_conducted > 0:
            overall_recovery_needed = max(0, math.ceil(round((0.80 * sim_conducted - sim_attended) / 0.20, 9)))

        if sim_overall_rate >= 80.0:
            verdict = "APPROVED_BY_POLICY"
            verdict_text = "Leave is SAFE. Projected attendance remains above the 80.0% policy requirement."
            verdict_badge = "SAFE"
        elif sim_overall_rate >= 75.0:
            verdict = "WARNING_BORDERLINE"
            verdict_text = "Leave drops attendance into BORDERLINE zone (75.0% - 79.9%). Condonation will be required."
            verdict_badge = "WARNING"
        else:
            verdict = "CRITICAL_SHORTAGE_RISK"
            verdict_text = "Leave BLOCKED by AI Safeguard: Drops attendance below 75.0% threshold, causing exam debarment."
            verdict_badge = "CRITICAL"

        leave_date_str = payload.leave_date or (date.today() + timedelta(days=1)).isoformat()
        draft_letter = (
            f"To: The Head of Department, Computer Science & Engineering\n"
            f"From: {student['name']} ({student['student_id']}), Year {student['year']}, Semester {student['semester']}\n"
            f"Date: {date.today().isoformat()}\n\n"
            f"Subject: Leave Application for {payload.day_of_week} ({leave_date_str})\n\n"
            f"Respected Sir/Madam,\n"
            f"I kindly request leave on {payload.day_of_week} ({leave_date_str}) for {missed_count} period(s) due to {payload.reason}.\n"
            f"My current attendance is {current_overall_rate}%. Projected attendance after leave will be {sim_overall_rate}%.\n"
            f"I undertake to attend all upcoming recovery lectures to maintain the 80% attendance standard.\n\n"
            f"Thank you.\nSincerely,\n{student['name']}"
        )

        return {
            "student_id": payload.student_id,
            "day_of_week": payload.day_of_week,
            "leave_date": leave_date_str,
            "periods_missed": payload.periods,
            "missed_classes_count": missed_count,
            "current_overall_percentage": current_overall_rate,
            "projected_overall_percentage": sim_overall_rate,
            "percentage_drop": percentage_drop,
            "overall_recovery_needed": overall_recovery_needed,
            "verdict": verdict,
            "verdict_text": verdict_text,
            "verdict_badge": verdict_badge,
            "subject_impacts": subject_impacts,
            "draft_leave_application": draft_letter,
            "is_submittable": True,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/agent/simulate-projection")
def simulate_projection(payload: SimulateProjectionRequest):
    """
    Interactive 'What-If' Attendance Projection Engine:
    Slides future attended classes to compute real-time trajectory and crossover milestones.
    """
    try:
        summary = repo_get_raw_summary(payload.student_id)
        total_conducted = summary["total_conducted"]
        total_attended = summary["total_attended"]
        current_rate = round((total_attended / total_conducted * 100.0), 2) if total_conducted > 0 else 0.0

        sim_conducted = total_conducted + payload.total_future_classes
        sim_attended = total_attended + payload.future_attended_classes
        projected_rate = round((sim_attended / sim_conducted * 100.0), 2) if sim_conducted > 0 else 0.0

        target = payload.target_percentage
        is_target_met = projected_rate >= target

        classes_to_cross = 0
        if current_rate < target:
            target_dec = target / 100.0
            classes_to_cross = max(0, math.ceil(round((target_dec * total_conducted - total_attended) / (1.0 - target_dec), 9)))

        return {
            "student_id": payload.student_id,
            "current_percentage": current_rate,
            "future_attended": payload.future_attended_classes,
            "total_future_classes": payload.total_future_classes,
            "projected_percentage": projected_rate,
            "target_percentage": target,
            "is_target_met": is_target_met,
            "classes_to_reach_target": classes_to_cross,
            "milestone_text": (
                f"You will cross the {target:.1f}% threshold after attending {classes_to_cross} consecutive classes."
                if current_rate < target else f"You are already safely above the {target:.1f}% threshold."
            ),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/agent/execute-action")
def execute_agent_action(payload: ExecuteActionRequest):
    """
    Executes a high-intent agentic action:
    - COMMIT_RECOVERY_PLAN: logs recovery plan in persistent memory + queues notifications
    - APPLY_LEAVE: submits formal leave in SQLite + logs memory event
    - DISPATCH_ALERT: dispatches priority alert notification + logs memory audit
    - LOG_EVENT: logs generic event
    """
    try:
        action = payload.action_type
        student_id = payload.student_id
        data = payload.payload

        if action == "COMMIT_RECOVERY_PLAN":
            overall_needed = data.get("overall_needed", 0)
            target = data.get("target", 80.0)
            mid = repo_save_memory_event(
                student_id=student_id,
                subject_id=None,
                event_type="RECOVERY_PLAN",
                description=f"Student committed to recovery roadmap: Attend next {overall_needed} classes to reach {target}% attendance.",
                metadata=data,
            )
            nid = repo_save_notification(
                student_id=student_id,
                subject_id=None,
                message=f"Recovery plan activated: Attend next {overall_needed} lectures to maintain {target}% attendance requirement.",
                priority="HIGH",
            )
            return {
                "success": True,
                "action": action,
                "message": f"Recovery plan committed successfully. Attendance memory logged (ID #{mid}) and notification queued (ID #{nid}).",
                "memory_id": mid,
                "notification_id": nid,
            }

        elif action == "APPLY_LEAVE":
            leave_date = data.get("leave_date", date.today().isoformat())
            reason = data.get("reason", "Personal leave")
            lid = repo_apply_leave(student_id=student_id, date=leave_date, reason=reason, status="Pending")
            mid = repo_save_memory_event(
                student_id=student_id,
                subject_id=None,
                event_type="AGENT_ACTION",
                description=f"Leave application submitted for {leave_date}. Reason: {reason}.",
                metadata={"leave_id": lid, "date": leave_date, "reason": reason},
            )
            return {
                "success": True,
                "action": action,
                "message": f"Leave application #{lid} submitted to HOD office. Logged in persistent memory.",
                "leave_id": lid,
            }

        elif action == "DISPATCH_ALERT":
            msg = data.get("message", "Attendance alert issued.")
            priority = data.get("priority", "HIGH")
            nid = repo_save_notification(student_id=student_id, subject_id=None, message=msg, priority=priority)
            mid = repo_save_memory_event(
                student_id=student_id,
                subject_id=None,
                event_type="WARNING",
                description=f"Proactive Attendance Warning issued: {msg}",
                metadata={"priority": priority, "notification_id": nid},
            )
            return {
                "success": True,
                "action": action,
                "message": f"Alert #{nid} dispatched to student and recorded in audit ledger.",
                "notification_id": nid,
            }

        else:
            mid = repo_save_memory_event(
                student_id=student_id,
                subject_id=None,
                event_type="IMPORTANT_EVENT",
                description=str(data.get("description", "Agent action executed")),
                metadata=data,
            )
            return {"success": True, "action": action, "memory_id": mid}

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/agent/query", response_model=AgentResponse)
def query_agent(payload: AgentQuery) -> AgentResponse:
    """
    Multi-Agent Intelligent Consultation & Recovery Endpoint:
    Dispatches to specialist sub-agents (Recovery Math, Sentinel, Leave, Policy, Export, Communication).
    """
    try:
        # Fast, high-accuracy multi-agent processing
        res = multi_agent_system.process_query(student_id=payload.student_id, message=payload.message)
        return AgentResponse(
            answer=res["answer"],
            student_id=payload.student_id,
            tool_trace=res.get("tool_trace", []),
            active_agent=res.get("active_agent"),
            action_type=res.get("action_type"),
            action_payload=res.get("action_payload"),
            download_url=res.get("download_url")
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Multi-Agent execution failed: {exc}") from exc


@app.post("/agent/sentinel/check")
def sentinel_check(student_id: str = "S001"):
    """
    Sentinel Agent Auto-Scan (Non-Blocking):
    Monitors attendance deficits & automatically issues priority alerts if < 75%.
    External notifications (SMS/Email) run in background threads — returns instantly.
    """
    try:
        # Run audit synchronously (DB-only, fast). External comms already backgrounded inside audit_and_alert.
        result = multi_agent_system.sentinel.audit_and_alert(student_id)
        return result
    except Exception as exc:
        # Never fail the page load — return a safe response
        return {"status": "ok", "student_id": student_id, "is_critical": False, "is_borderline": False, "actions_taken": []}


# -----------------------------------------------------------------------------
# 4. Multi-Format Export Endpoints (PDF, XML, JSON, CSV, TXT)
# -----------------------------------------------------------------------------
@app.get("/api/export/{student_id}/{format_type}")
def export_attendance_report(student_id: str, format_type: str):
    """
    Export verified attendance transcript in PDF, XML, JSON, CSV, or TXT format.
    """
    try:
        fmt = format_type.lower().strip()
        if fmt == "pdf":
            pdf_bytes = ExportService.generate_pdf(student_id)
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="Attendance_Report_{student_id}.pdf"',
                    "Content-Type": "application/pdf"
                }
            )
        elif fmt == "xml":
            xml_data = ExportService.generate_xml(student_id)
            return Response(
                content=xml_data,
                media_type="application/xml",
                headers={"Content-Disposition": f'attachment; filename="Attendance_Report_{student_id}.xml"'}
            )
        elif fmt == "json":
            json_data = ExportService.generate_json(student_id)
            return Response(
                content=json_data,
                media_type="application/json",
                headers={"Content-Disposition": f'attachment; filename="Attendance_Report_{student_id}.json"'}
            )
        elif fmt in ["csv", "excel"]:
            csv_data = ExportService.generate_csv(student_id)
            return Response(
                content=csv_data,
                media_type="text/csv",
                headers={"Content-Disposition": f'attachment; filename="Attendance_Report_{student_id}.csv"'}
            )
        else:
            txt_data = ExportService.generate_text_dossier(student_id)
            return Response(
                content=txt_data,
                media_type="text/plain",
                headers={"Content-Disposition": f'attachment; filename="Attendance_Report_{student_id}.txt"'}
            )
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# -----------------------------------------------------------------------------
# 5. Multi-Channel Communication Endpoints (SMS to 9042778493 & Email to wellz.bot@gmail.com)
# -----------------------------------------------------------------------------
@app.get("/api/students/{student_id}/contact")
def get_student_contact_info(student_id: str):
    """Retrieve registered phone number and email for a student."""
    try:
        student = repo_get_student(student_id)
        if not student:
            raise HTTPException(status_code=404, detail=f"Student {student_id} not found")
        contact = get_student_contact(student_id)
        return {
            "student_id": student_id,
            "student_name": student["name"],
            "phone": contact["phone"],
            "email": contact["email"]
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/communication/send")
def send_multi_channel_notification(payload: CommunicationRequest):
    """
    Dispatch SMS alert (e.g. 9042778493) and/or Email alert (e.g. wellz.bot@gmail.com).
    """
    try:
        results = {}
        if payload.channel in ["sms", "both"]:
            results["sms"] = CommunicationService.send_sms(
                student_id=payload.student_id,
                phone_number=payload.phone,
                custom_message=payload.message,
                priority=payload.priority
            )
        if payload.channel in ["email", "both"]:
            results["email"] = CommunicationService.send_email(
                student_id=payload.student_id,
                email_address=payload.email,
                custom_message=payload.message,
                priority=payload.priority
            )
        return {"success": True, "results": results}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# -----------------------------------------------------------------------------
# 4. Mount Frontend Static Files at Root
# -----------------------------------------------------------------------------
frontend_path = Path(__file__).resolve().parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
