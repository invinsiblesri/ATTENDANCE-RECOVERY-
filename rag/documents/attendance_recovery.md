# Demo College Attendance Policy — Hackathon Prototype

> [!NOTE]
> This document contains simulated prototype policies created solely for the AI Attendance Recovery Agent hackathon demonstration. It does not represent official university or college regulations.

## 1. Concept of Attendance Recovery
When a student's overall attendance drops below the required **80.0% threshold**, the student must engage in attendance recovery.
- Attendance recovery is the process of improving cumulative attendance by consistently attending upcoming scheduled classes.

## 2. Recovery Mechanism: Attending Upcoming Timetable Classes
Because all 8 subjects are equally weighted and held according to the 8-period daily schedule:
- Every future class attended adds 1 to both `Total Periods Attended` and `Total Periods Conducted`.
- To recover attendance back to 80.0% or higher, a student must attend consecutive upcoming classes without unexcused absences until the ratio reaches or exceeds 0.80.

## 3. Recovery Planning Guidance
- Students are advised to monitor their attendance history and upcoming daily timetable.
- The AI Attendance Recovery Agent assists by reviewing raw attendance totals and identifying the upcoming class schedule so the student can plan their attendance recovery roadmap.
