# Demo College Attendance Policy — Hackathon Prototype

> [!NOTE]
> This document contains simulated prototype policies created solely for the AI Attendance Recovery Agent hackathon demonstration. It does not represent official university or college regulations.

## 1. Core Minimum Attendance Requirement
The college mandates an overall minimum attendance requirement of **80.0%** across all academic subjects.
- The 80.0% threshold is calculated on cumulative class attendance across the semester.
- Meeting or exceeding 80.0% overall attendance is required for regular academic standing.

## 2. Equal Subject Importance
All eight (8) curriculum subjects carry **equal importance** and equal weight:
1. Python (CS301)
2. Java (CS302)
3. DBMS (CS303)
4. Computer Networks (CS304)
5. Software Engineering (CS305)
6. Mathematics (CS306)
7. Artificial Intelligence (CS307)
8. Operating Systems (CS308)

There is **no subject-specific weighting, priority, or multiplier**. Every class hour across every subject counts equally toward the student's overall attendance total.

## 3. Period-Wise / Class-Wise Attendance Recording
- Attendance is recorded period-by-period for each scheduled class.
- The academic timetable consists of **eight (8) periods per day**, Monday through Friday.
- Each period is logged with an attendance status of either `Present` or `Absent`.
- The primary source of truth is the cumulative collection of raw period-wise class attendance records.

## 4. Attendance Calculation Concept
Overall attendance percentage is calculated using the standard formula:
`Overall Attendance % = (Total Periods Attended / Total Periods Conducted) * 100`

Subject-wise attendance percentage is similarly calculated from raw class records:
`Subject Attendance % = (Subject Periods Attended / Subject Periods Conducted) * 100`
