const ApiService = (() => {
  const baseUrl = () => window.APP_CONFIG?.API_BASE_URL || "http://127.0.0.1:8000";

  async function request(path, options = {}) {
    const response = await fetch(`${baseUrl()}${path}`, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    if (!response.ok) {
      let detail = `Request failed with ${response.status}`;
      try {
        const body = await response.json();
        detail = body.detail || detail;
      } catch (_) {}
      throw new Error(detail);
    }
    return response.json();
  }

  return {
    getHealth: () => request("/health"),
    getDashboard: (studentId) => request(`/dashboard/${encodeURIComponent(studentId)}`),
    getNotifications: (studentId) => request(`/notifications/${encodeURIComponent(studentId)}`),
    markNotificationRead: (notificationId) => request(`/notifications/${notificationId}/read`, { method: "POST" }),
    runGoal: ({ studentId, goal, subjectId, confirmed = false }) => request("/agent/query", {
      method: "POST",
      body: JSON.stringify({
        student_id: studentId,
        goal,
        subject_id: subjectId || null,
        confirmed,
        message: `Run the ${goal} workflow for this student.`,
      }),
    }),
  };
})();

window.ApiService = ApiService;
