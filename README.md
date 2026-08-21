# AttendAI — Modern College Student Attendance Dashboard

**AttendAI** is an AI-powered college attendance management and recovery platform designed for hackathons and academic SaaS deployments. It provides a clean, minimal desktop interface centered around a **weekly 8-period attendance timetable** (Monday–Saturday).

---

## 🚀 Quickstart

Open the frontend dashboard directly in your browser:
- **[`frontend/index.html`](file:///C:/Users/infer/Downloads/attedance%20recover%20agent/frontend/index.html)**

---

## 🎨 Key Features & Design System

1. **Focused Weekly 8-Period Timetable (1440 × 900 px)**
   - **6 Days**: Monday to Saturday.
   - **8 Periods**: Period 1 (08:30 AM) through Period 8 (04:40 PM) with morning and lunch break intervals.
   - **Minimal Cells**: Strictly contains **Subject Name** + **Subtle Status Indicator**.
   - **Subjects**: *Python, Java, DBMS, Computer Networks, AI, Mathematics, Software Engineering, OS*.
   - **Subtle Status Indicators**:
     - 🟢 **Present** (Emerald soft tint & dot)
     - 🔴 **Absent** (Rose soft tint & dot)
     - 🔵 **Upcoming** (Slate neutral tint & dot)
     - 🟠 **Leave** (Amber soft tint & dot)
   - **Current Day Highlight**: Friday, August 21, 2026 is highlighted as **TODAY**.

2. **Compact Attendance Summary**
   - **Overall Attendance: 80%** with policy threshold badge (*Above 75% Policy*).
   - Quick counters: 28 Present, 7 Absent, 1 Leave, 12 Upcoming (\( \frac{28}{28 + 7} = \mathbf{80.0\%} \)).
   - Strictly zero clutter — no large charts, complex graphs, or subject-wise cards.

3. **Decoupled Architecture for GitHub Merging**
   - Pure frontend in `frontend/` with a decoupled `services/api.js` data layer and `config.js` environment toggle.

---

## 📁 Repository Structure

```
attedance recover agent/
├── frontend/                    # Standalone Frontend Module (Member 3)
│   ├── index.html               # 1440x900 desktop attendance dashboard
│   ├── styles.css               # Clean SaaS styling tokens & badge themes
│   ├── config.js                # Environment config & mock switch
│   ├── app.js                   # UI controller & DOM rendering logic
│   ├── services/
│   │   └── api.js               # Decoupled Data Service layer
│   └── README.md                # Frontend documentation
├── TEAM_INTEGRATION_GUIDE.md    # Integration contracts for Member 1, 2, and 4
└── README.md                    # Root project documentation
```
