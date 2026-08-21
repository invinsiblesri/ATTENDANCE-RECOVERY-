/**
 * AttendAI - Data Service Layer (Decoupled Interface)
 * 
 * Provides unified async functions for fetching timetable, profile, and attendance metrics.
 * Operates seamlessly in offline Mock Mode or Live API Mode.
 */

const ApiService = (function() {
  
  // Clean, realistic Mock Database for Frontend Development
  const MOCK_PROFILE = {
    id: "24CS042",
    name: "Alex Morgan",
    department: "Computer Science & Engineering",
    year: "Year 3",
    semester: "Semester 5",
    rollNo: "24CS042",
    avatar: "AM",
    overallRate: 80.0
  };

  // Period slots definition (8 periods with breaks)
  const PERIOD_DEFINITIONS = [
    { period: 1, label: "Period 1", time: "08:30 – 09:20 AM" },
    { period: 2, label: "Period 2", time: "09:25 – 10:15 AM" },
    // Morning Break: 10:15 – 10:30 AM
    { period: 3, label: "Period 3", time: "10:30 – 11:20 AM" },
    { period: 4, label: "Period 4", time: "11:25 – 12:15 PM" },
    // Lunch Break: 12:15 – 01:00 PM
    { period: 5, label: "Period 5", time: "01:00 – 01:50 PM" },
    { period: 6, label: "Period 6", time: "01:55 – 02:45 PM" },
    { period: 7, label: "Period 7", time: "02:55 – 03:45 PM" },
    { period: 8, label: "Period 8", time: "03:50 – 04:40 PM" }
  ];

  // 8-Period × 6-Day Timetable: Exactly 28 Present, 7 Absent, 1 Leave, 12 Upcoming (80.0% rate)
  const MOCK_TIMETABLE = {
    Monday: [
      { period: 1, subject: "Python", status: "Present" },
      { period: 2, subject: "Java", status: "Present" },
      { period: 3, subject: "DBMS", status: "Absent" },
      { period: 4, subject: "Computer Networks", status: "Present" },
      { period: 5, subject: "AI", status: "Present" },
      { period: 6, subject: "Mathematics", status: "Present" },
      { period: 7, subject: "Software Engineering", status: "Absent" },
      { period: 8, subject: "OS", status: "Present" }
    ],
    Tuesday: [
      { period: 1, subject: "OS", status: "Present" },
      { period: 2, subject: "Mathematics", status: "Present" },
      { period: 3, subject: "Python", status: "Present" },
      { period: 4, subject: "Java", status: "Present" },
      { period: 5, subject: "DBMS", status: "Absent" },
      { period: 6, subject: "Computer Networks", status: "Present" },
      { period: 7, subject: "AI", status: "Present" },
      { period: 8, subject: "Software Engineering", status: "Present" }
    ],
    Wednesday: [
      { period: 1, subject: "Software Engineering", status: "Present" },
      { period: 2, subject: "AI", status: "Present" },
      { period: 3, subject: "Java", status: "Present" },
      { period: 4, subject: "DBMS", status: "Leave" },
      { period: 5, subject: "Mathematics", status: "Present" },
      { period: 6, subject: "Python", status: "Present" },
      { period: 7, subject: "OS", status: "Absent" },
      { period: 8, subject: "Computer Networks", status: "Present" }
    ],
    Thursday: [
      { period: 1, subject: "Computer Networks", status: "Present" },
      { period: 2, subject: "OS", status: "Present" },
      { period: 3, subject: "Python", status: "Present" },
      { period: 4, subject: "AI", status: "Present" },
      { period: 5, subject: "Software Engineering", status: "Absent" },
      { period: 6, subject: "Java", status: "Present" },
      { period: 7, subject: "Mathematics", status: "Absent" },
      { period: 8, subject: "DBMS", status: "Present" }
    ],
    Friday: [
      { period: 1, subject: "Mathematics", status: "Present" },
      { period: 2, subject: "DBMS", status: "Absent" }, // Marked absent today
      { period: 3, subject: "Python", status: "Present" },
      { period: 4, subject: "Java", status: "Present" },
      { period: 5, subject: "AI", status: "Upcoming" },
      { period: 6, subject: "Software Engineering", status: "Upcoming" },
      { period: 7, subject: "OS", status: "Upcoming" },
      { period: 8, subject: "Computer Networks", status: "Upcoming" }
    ],
    Saturday: [
      { period: 1, subject: "AI", status: "Upcoming" },
      { period: 2, subject: "Software Engineering", status: "Upcoming" },
      { period: 3, subject: "DBMS", status: "Upcoming" },
      { period: 4, subject: "Python", status: "Upcoming" },
      { period: 5, subject: "Java", status: "Upcoming" },
      { period: 6, subject: "Computer Networks", status: "Upcoming" },
      { period: 7, subject: "OS", status: "Upcoming" },
      { period: 8, subject: "Mathematics", status: "Upcoming" }
    ]
  };

  // 1. Fetch Student Profile
  async function fetchProfile(studentId = "24CS042") {
    if (window.APP_CONFIG && !window.APP_CONFIG.USE_MOCK_DATA) {
      try {
        const res = await fetch(`${window.APP_CONFIG.API_BASE_URL}/students/${studentId}`);
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn("Failed to fetch live profile, falling back to mock:", e);
      }
    }
    return Promise.resolve(MOCK_PROFILE);
  }

  // 2. Fetch Weekly Timetable
  async function fetchTimetable(studentId = "24CS042", weekOffset = 0) {
    if (window.APP_CONFIG && !window.APP_CONFIG.USE_MOCK_DATA) {
      try {
        const res = await fetch(`${window.APP_CONFIG.API_BASE_URL}/timetable?student_id=${studentId}&week=${weekOffset}`);
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn("Failed to fetch live timetable, falling back to mock:", e);
      }
    }
    return Promise.resolve(JSON.parse(JSON.stringify(MOCK_TIMETABLE)));
  }

  // 3. Update Period Attendance Status (For Interactive Demonstrations)
  async function updatePeriodStatus(studentId, day, period, status) {
    if (window.APP_CONFIG && !window.APP_CONFIG.USE_MOCK_DATA) {
      try {
        const res = await fetch(`${window.APP_CONFIG.API_BASE_URL}/attendance/update`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ student_id: studentId, day, period, status })
        });
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn("Failed live update, updating local state only:", e);
      }
    }
    return Promise.resolve({ success: true, studentId, day, period, status });
  }

  // 4. Calculate Attendance Statistics
  function calculateMetrics(timetable) {
    let present = 0, absent = 0, leave = 0, upcoming = 0;
    const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

    days.forEach(d => {
      (timetable[d] || []).forEach(slot => {
        if (slot.status === "Present") present++;
        else if (slot.status === "Absent") absent++;
        else if (slot.status === "Leave") leave++;
        else if (slot.status === "Upcoming") upcoming++;
      });
    });

    const conducted = present + absent;
    const rate = conducted > 0 ? Math.round((present / conducted) * 100) : 80.0;

    return {
      rate: rate,
      present: present,
      absent: absent,
      leave: leave,
      upcoming: upcoming,
      isCompliant: rate >= (window.APP_CONFIG?.MIN_REQUIRED_ATTENDANCE || 75.0)
    };
  }

  return {
    PERIOD_DEFINITIONS,
    fetchProfile,
    fetchTimetable,
    updatePeriodStatus,
    calculateMetrics
  };
})();

// Attach to window
if (typeof window !== "undefined") {
  window.ApiService = ApiService;
}
