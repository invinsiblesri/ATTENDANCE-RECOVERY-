# AttendAI — Standalone Frontend Module

This directory contains the **isolated Frontend UI** for AttendAI, developed independently for Member 3's hackathon responsibilities. It is designed to run completely standalone with zero dependencies, and can be merged cleanly with Member 1 (AI Agent), Member 2 (Database/RAG), and Member 4 (Automation) repositories later.

---

## 🎨 UI Design System & Constraints

- **Dominant Focus**: Monday–Saturday Weekly Attendance Timetable (8 Periods/Day).
- **Desktop Dimensions**: Optimized for **1440 × 900 px** with responsive horizontal scrolling on smaller viewports.
- **Attendance Rate**: **80%** (28 Present, 7 Absent, 1 Leave, 12 Upcoming).
- **Minimalist Cells**: Contains ONLY `Subject Name` + subtle `Attendance Status` pill (🟢 Present, 🔴 Absent, 🔵 Upcoming, 🟠 Leave).
- **Subjects**: *Python, Java, DBMS, Computer Networks, AI, Mathematics, Software Engineering, OS*.
- **Today Highlight**: Friday, August 21, 2026.
- **No Clutter**: Zero faculty names, room numbers, complex graphs, or subject-wise cards.

---

## 📁 Directory Structure

```
frontend/
├── index.html           # Main dashboard markup (1440x900 desktop UI)
├── styles.css           # Custom styles, badge themes & clean scrollbars
├── config.js            # Configuration & environment switches
├── app.js               # UI controller & DOM rendering logic
├── services/
│   └── api.js           # Decoupled Data Service layer (Mock + Live API bridge)
└── README.md            # Frontend documentation & merge guide
```

---

## 🚀 How to Run Standalone

Simply open `index.html` in your browser:
- Double-click [`frontend/index.html`](file:///C:/Users/infer/Downloads/attedance%20recover%20agent/frontend/index.html), OR
- Run any local HTTP server: `python -m http.server 3000` inside the `frontend/` directory.

---

## 🔗 How to Merge with Other Team Members (GitHub)

When the 4 members merge their work into a single GitHub repository:

```
root/
├── agent/               # Member 1: Ollama + LangGraph AI Agent
├── database/            # Member 2: SQLite & ChromaDB
├── frontend/            # Member 3: This Frontend Dashboard UI
├── automation/          # Member 4: Automation & Notification Triggers
└── README.md            # Root Project README
```

### Step to Connect Frontend to Backend:
In `frontend/config.js`, change:
```javascript
// Switch from mock data to live backend API
CONFIG.USE_MOCK_DATA = false;
CONFIG.API_BASE_URL = "http://localhost:8000/api";
```
That's it! `services/api.js` will automatically route all calls (`fetchProfile`, `fetchTimetable`, `updatePeriodStatus`) to the live team API.
