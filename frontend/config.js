/**
 * AttendAI Frontend Configuration
 * 
 * For team GitHub merge:
 * - When running standalone (frontend only): USE_MOCK_DATA = true
 * - When merging with Member 1, 2, and 4: Set USE_MOCK_DATA = false and configure API_BASE_URL
 */
const CONFIG = {
  // Toggle between local mock service and live team backend API
  USE_MOCK_DATA: true,

  // Root endpoint for backend API when team branches are merged
  API_BASE_URL: "http://localhost:8000/api",

  // App Metadata
  APP_NAME: "AttendAI",
  ACADEMIC_YEAR: "2026–2027",
  SEMESTER: "Semester 5",
  CURRENT_DATE: "Friday, August 21, 2026",
  MIN_REQUIRED_ATTENDANCE: 75.0, // College policy minimum (%)
  DEFAULT_STUDENT_ID: "24CS042"
};

// Export for global window attachment
if (typeof window !== "undefined") {
  window.APP_CONFIG = CONFIG;
}
