from __future__ import annotations

from datetime import date, time
from typing import Any, Literal

from pydantic import BaseModel, Field


class Student(BaseModel):
    student_id: str
    name: str
    email: str | None = None
    department: str | None = None
    semester: int | None = None


class Subject(BaseModel):
    subject_id: str
    subject_name: str
    minimum_attendance: float = Field(default=75.0, ge=0, le=100)
    weekly_recovery_limit: int = Field(default=3, ge=0)


class AttendanceHistoryRecord(BaseModel):
    student_id: str
    subject_id: str
    period: str
    conducted: int = Field(ge=0)
    attended: int = Field(ge=0)
    percentage: float = Field(ge=0, le=100)


class MemoryEvent(BaseModel):
    memory_id: str
    student_id: str
    event_type: str
    payload: dict[str, Any]
    created_at: str


class AttendanceRecord(BaseModel):
    student_id: str
    course_id: str
    course_name: str
    present_classes: int = Field(ge=0)
    total_classes: int = Field(ge=0)
    attendance_percentage: float = Field(ge=0, le=100)
    last_updated: date | None = None


class TimetableEntry(BaseModel):
    course_id: str
    course_name: str
    class_date: date
    start_time: time
    end_time: time
    room: str | None = None
    is_attended: bool = False


class PolicyResult(BaseModel):
    course_id: str
    minimum_percentage: float = Field(default=75.0, ge=0, le=100)
    maximum_recovery_classes_per_week: int = Field(default=3, ge=0)
    recovery_allowed: bool = True
    notes: list[str] = Field(default_factory=list)


class AttendanceCalculation(BaseModel):
    student_id: str
    course_id: str
    current_present: int = Field(ge=0)
    current_total: int = Field(ge=0)
    current_percentage: float = Field(ge=0, le=100)
    target_percentage: float = Field(ge=0, le=100)
    additional_classes_needed: int = Field(ge=0)
    projected_percentage: float = Field(ge=0, le=100)
    mathematically_possible: bool


class RecoveryPlan(BaseModel):
    student_id: str
    course_id: str
    course_name: str
    current_percentage: float
    target_percentage: float
    additional_classes_needed: int
    recommended_classes: list[TimetableEntry] = Field(default_factory=list)
    weekly_limit: int
    recovery_allowed: bool
    warnings: list[str] = Field(default_factory=list)


class NotificationResult(BaseModel):
    notification_id: str
    student_id: str
    priority: Literal["LOW", "MEDIUM", "HIGH"]
    status: Literal["QUEUED", "READ", "DISMISSED"]
    message: str


class AgentQuery(BaseModel):
    student_id: str = Field(min_length=1)
    message: str = Field(min_length=1)


class AgentResponse(BaseModel):
    answer: str
    student_id: str
    tool_trace: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: Literal["ok"]
    model: str
    backend_mode: str
