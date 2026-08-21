(function () {
  "use strict";

  const state = { studentId: window.APP_CONFIG.DEFAULT_STUDENT_ID, dashboard: null, pendingGoal: null };
  const $ = (id) => document.getElementById(id);

  document.addEventListener("DOMContentLoaded", async () => {
    bindEvents();
    await refreshWorkspace();
    renderIcons();
  });

  function renderIcons() { if (window.lucide) window.lucide.createIcons(); }

  function initials(name) { return name.split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase(); }
  function riskClass(risk) { return `risk-${String(risk || "LOW").toLowerCase()}`; }
  function toast(message, kind = "success") { const node = $("toast"); node.textContent = message; node.className = `toast ${kind}`; setTimeout(() => node.classList.add("hidden"), 3200); }

  async function refreshWorkspace() {
    try {
      const [health, dashboard] = await Promise.all([ApiService.getHealth(), ApiService.getDashboard(state.studentId)]);
      state.dashboard = dashboard;
      $("backend-status").textContent = `${health.model} connected`;
      renderDashboard(dashboard);
    } catch (error) {
      $("backend-status").textContent = "Backend offline";
      toast(`Unable to load live evidence: ${error.message}`, "error");
    }
  }

  function renderDashboard(data) {
    const student = data.student;
    $("student-name").textContent = student.name;
    $("student-meta").textContent = `${student.student_id} · Year ${student.year} · Sem ${student.semester}`;
    $("student-avatar").textContent = initials(student.name);
    $("overall-percentage").textContent = `${data.overall.percentage}%`;
    $("overall-detail").textContent = `${data.overall.attended} attended from ${data.overall.conducted} conducted classes`;
    const policy = $("overall-risk");
    policy.textContent = data.overall.risk === "HIGH" ? "RECOVERY NEEDED" : data.overall.risk === "MEDIUM" ? "WATCH CLOSELY" : "ON TRACK";
    policy.className = `policy-badge ${riskClass(data.overall.risk)}`;
    const high = data.subjects.filter((subject) => subject.risk === "HIGH");
    $("high-risk-count").textContent = high.length;
    $("unread-count").textContent = data.notifications.length;
    const selector = $("subject-select");
    selector.innerHTML = data.subjects.map((subject) => `<option value="${subject.subject_id}">${subject.subject_name} · ${subject.percentage}%</option>`).join("");
    selector.value = high[0]?.subject_id || data.subjects[0]?.subject_id || "";
    renderSubjects(data.subjects);
    renderNotifications(data.notifications);
  }

  function renderSubjects(subjects) {
    $("subject-board").innerHTML = subjects.map((subject) => `
      <article class="subject-card ${riskClass(subject.risk)}">
        <div><span class="risk-label">${subject.risk} RISK</span><h3>${subject.subject_name}</h3><p>${subject.subject_code} · ${subject.attended}/${subject.conducted} classes</p></div>
        <div class="subject-score"><strong>${subject.percentage}%</strong><span>attendance</span></div>
        <div class="subject-bar"><span style="width:${Math.min(subject.percentage, 100)}%"></span></div>
      </article>
    `).join("");
  }

  function renderNotifications(notifications) {
    const container = $("notification-list");
    if (!notifications.length) { container.innerHTML = `<div class="empty-state">No unread actions. Confirm a recovery reminder to create one.</div>`; return; }
    container.innerHTML = notifications.map((notification) => `
      <article class="notification ${String(notification.priority).toLowerCase()}">
        <div class="notification-icon"><i data-lucide="bell-ring"></i></div>
        <div><span>${notification.priority} PRIORITY${notification.subject_name ? ` · ${notification.subject_name}` : ""}</span><p>${notification.message}</p></div>
        <button data-read="${notification.notification_id}">Mark read</button>
      </article>
    `).join("");
    container.querySelectorAll("[data-read]").forEach((button) => button.addEventListener("click", async () => {
      await ApiService.markNotificationRead(button.dataset.read);
      await refreshNotifications();
    }));
    renderIcons();
  }

  async function refreshNotifications() {
    try { const payload = await ApiService.getNotifications(state.studentId); renderNotifications(payload.notifications.filter((item) => !item.is_read)); $("unread-count").textContent = payload.notifications.filter((item) => !item.is_read).length; } catch (error) { toast(error.message, "error"); }
  }

  async function runGoal(goal, confirmed = false) {
    const subjectId = $("subject-select").value;
    state.pendingGoal = { goal, subjectId };
    setWorking(goal);
    try {
      const result = await ApiService.runGoal({ studentId: state.studentId, goal, subjectId, confirmed });
      renderAgentResult(result);
      if (result.goal_status === "COMPLETED") {
        await refreshWorkspace();
      }
    } catch (error) {
      $("agent-state").className = "console-state blocked";
      $("agent-state").innerHTML = `<span></span> BLOCKED`;
      $("agent-answer").textContent = `The agent could not complete this goal: ${error.message}`;
      toast(error.message, "error");
    }
  }

  function setWorking(goal) {
    $("agent-title").textContent = `Running ${goal} workflow`;
    $("agent-state").className = "console-state working";
    $("agent-state").innerHTML = `<span></span> GATHERING EVIDENCE`;
    $("agent-decision").textContent = "The agent is selecting trusted tools and waiting for their results before deciding.";
    $("agent-answer").textContent = "Working through the evidence path…";
    $("tool-trace").innerHTML = `<p>Tool trace will appear after the evidence path completes.</p>`;
    $("evidence-list").innerHTML = `<p>Waiting for SQLite, RAG, timetable, or memory evidence.</p>`;
    $("confirm-zone").classList.add("hidden");
  }

  function renderAgentResult(result) {
    $("agent-title").textContent = result.goal === "leave" ? "Leave impact assessment" : result.goal === "recovery" ? "Recovery plan created" : result.goal === "notification" ? "Recovery reminder workflow" : result.goal === "risk" ? "Attendance risk assessment" : "Agent outcome";
    const stateNode = $("agent-state");
    const confirmation = result.goal_status === "NEEDS_CONFIRMATION";
    stateNode.className = `console-state ${confirmation ? "waiting" : "complete"}`;
    stateNode.innerHTML = `<span></span> ${confirmation ? "CONFIRM ACTION" : "DECISION COMPLETE"}`;
    $("agent-decision").textContent = result.decision || "The agent completed the goal using trusted tools.";
    $("agent-answer").textContent = result.answer;
    $("tool-trace").innerHTML = (result.tool_trace || []).map((tool, index) => `<span>${String(index + 1).padStart(2, "0")} <strong>${tool}</strong></span>`).join("") || "<p>No tools reported.</p>";
    const evidence = result.evidence || [];
    $("evidence-list").innerHTML = evidence.length ? evidence.map((item) => `<article>${renderEvidence(item)}</article>`).join("") : "<p>No additional evidence returned.</p>";
    const confirmationNode = $("confirm-zone");
    if (confirmation) confirmationNode.classList.remove("hidden"); else confirmationNode.classList.add("hidden");
    renderIcons();
  }

  function renderEvidence(item) {
    if (item.subject && item.percentage !== undefined) return `<strong>${item.subject}</strong><span>${item.percentage}% attendance · ${item.risk || `${item.classes_needed ?? 0} classes to recover`}</span>`;
    if (item.course_name && item.required_additional_classes !== undefined) return `<strong>${item.course_name}</strong><span>${item.required_additional_classes} class(es) required to reach ${item.target_percentage}%</span>`;
    if (item.previous_memory_events !== undefined) return `<strong>Persistent memory</strong><span>${item.previous_memory_events} prior attendance events inspected</span>`;
    return `<strong>Verified record</strong><span>${JSON.stringify(item)}</span>`;
  }

  function bindEvents() {
    document.querySelectorAll("[data-goal]").forEach((button) => button.addEventListener("click", () => runGoal(button.dataset.goal)));
    $("refresh-button").addEventListener("click", refreshWorkspace);
    $("refresh-notifications").addEventListener("click", refreshNotifications);
    $("confirm-action-button").addEventListener("click", () => { if (state.pendingGoal) runGoal(state.pendingGoal.goal, true); });
  }
})();
