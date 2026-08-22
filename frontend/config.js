/**
 * AttendAI - 100% Agentic AI Attendance Recovery System
 * Frontend Application Configuration
 */
const CONFIG = {
  // Base URL for backend API (dynamic detection if served from FastAPI or standalone)
  API_BASE_URL: (function() {
    if (typeof window === "undefined") return "http://127.0.0.1:8000";
    if (window.location.origin && window.location.origin.startsWith("http") && window.location.port === "8000") {
      return window.location.origin;
    }
    return "http://127.0.0.1:8000";
  })(),

  // App Metadata & Academic Context
  APP_NAME: "AttendAI",
  APP_VERSION: "2.0.0",
  AGENT_ROLE: "100% Agentic AI Attendance Recovery Engine",
  ACADEMIC_YEAR: "2026–2027",
  CURRENT_CYCLE: "Odd Semester 2026",
  CURRENT_DATE: "Friday, August 21, 2026",
  
  // Policy Standards
  POLICY_SAFE_THRESHOLD: 80.0,      // Official Exam Eligibility Minimum (%)
  POLICY_CONDONATION_MIN: 75.0,    // Dean Condonation Minimum (%)
  POLICY_MAX_RECOVERY_WEEKLY: 3,   // Max recovery classes per week per subject
  
  // Default Seeded Student
  DEFAULT_STUDENT_ID: "S001",

  // 20 Registered Demo Students from SQLite Backend
  STUDENTS: [
    { id: "S001", name: "Aarav Sharma", dept: "Computer Science & Engineering", year: 3, sem: 5, calibrated_rate: 78.75, tag: "Demo Student (Borderline 78.75%)" },
    { id: "S002", name: "Priya Patel", dept: "Computer Science & Engineering", year: 3, sem: 5, calibrated_rate: 94.58, tag: "Safe Tier (94.58%)" },
    { id: "S003", name: "Rohan Iyer", dept: "Computer Science & Engineering", year: 3, sem: 5, calibrated_rate: 89.58, tag: "Safe Tier (89.58%)" },
    { id: "S004", name: "Ananya Gupta", dept: "Computer Science & Engineering", year: 3, sem: 5, calibrated_rate: 92.08, tag: "High Distinction (92.08%)" },
    { id: "S005", name: "Vikram Malhotra", dept: "Computer Science & Engineering", year: 3, sem: 5, calibrated_rate: 86.67, tag: "Safe Tier (86.67%)" },
    { id: "S006", name: "Sneha Reddy", dept: "Computer Science & Engineering", year: 3, sem: 5, calibrated_rate: 83.33, tag: "Safe Tier (83.33%)" },
    { id: "S007", name: "Rahul Verma", dept: "Computer Science & Engineering", year: 3, sem: 5, calibrated_rate: 92.08, tag: "Safe Tier (92.08%)" },
    { id: "S008", name: "Neha Nair", dept: "Computer Science & Engineering", year: 3, sem: 5, calibrated_rate: 88.75, tag: "Safe Tier (88.75%)" },
    { id: "S009", name: "Siddharth Rao", dept: "Computer Science & Engineering", year: 3, sem: 5, calibrated_rate: 79.17, tag: "Borderline (79.17%)" },
    { id: "S010", name: "Pooja Joshi", dept: "Computer Science & Engineering", year: 3, sem: 5, calibrated_rate: 81.25, tag: "Safe Tier (81.25%)" },
    { id: "S011", name: "Karan Mehta", dept: "Computer Science & Engineering", year: 3, sem: 5, calibrated_rate: 74.58, tag: "Shortage Risk (74.58%)" },
    { id: "S012", name: "Divya Deshmukh", dept: "Computer Science & Engineering", year: 3, sem: 5, calibrated_rate: 86.67, tag: "Safe Tier (86.67%)" },
    { id: "S013", name: "Aditya Kulkarni", dept: "Computer Science & Engineering", year: 3, sem: 5, calibrated_rate: 77.50, tag: "Condonation Zone (77.50%)" },
    { id: "S014", name: "Ritu Choudhury", dept: "Computer Science & Engineering", year: 3, sem: 5, calibrated_rate: 90.42, tag: "High Distinction (90.42%)" },
    { id: "S015", name: "Varun Kapoor", dept: "Computer Science & Engineering", year: 3, sem: 5, calibrated_rate: 73.33, tag: "Shortage Risk (73.33%)" },
    { id: "S016", name: "Ishita Sen", dept: "Computer Science & Engineering", year: 3, sem: 5, calibrated_rate: 82.50, tag: "Safe Tier (82.50%)" },
    { id: "S017", name: "Manish Pandey", dept: "Computer Science & Engineering", year: 3, sem: 5, calibrated_rate: 79.58, tag: "Borderline (79.58%)" },
    { id: "S018", name: "Tanvi Bhat", dept: "Computer Science & Engineering", year: 3, sem: 5, calibrated_rate: 87.08, tag: "Safe Tier (87.08%)" },
    { id: "S019", name: "Nikhil Saxena", dept: "Computer Science & Engineering", year: 3, sem: 5, calibrated_rate: 67.50, tag: "Critical Shortage (67.50%)" },
    { id: "S020", name: "Meera Pillai", dept: "Computer Science & Engineering", year: 3, sem: 5, calibrated_rate: 84.17, tag: "Safe Tier (84.17%)" }
  ]
};

// Export for global window attachment
if (typeof window !== "undefined") {
  window.APP_CONFIG = CONFIG;
}
