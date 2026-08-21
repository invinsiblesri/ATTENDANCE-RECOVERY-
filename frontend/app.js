/**
 * AttendAI Frontend Application Controller
 * Pure UI Layer - Decoupled from backend via ApiService
 */

(function() {
  "use strict";

  // Application State
  const state = {
    studentId: window.APP_CONFIG?.DEFAULT_STUDENT_ID || "24CS042",
    weekOffset: 0, // 0 = Current Week (Aug 17 – Aug 22, 2026)
    profile: null,
    timetable: null,
    editingCell: null
  };

  const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

  // Initialize Application
  document.addEventListener("DOMContentLoaded", async () => {
    await loadInitialData();
    initEventHandlers();
    initLucide();
  });

  function initLucide() {
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  // Load Data via ApiService Layer
  async function loadInitialData() {
    state.profile = await ApiService.fetchProfile(state.studentId);
    state.timetable = await ApiService.fetchTimetable(state.studentId, state.weekOffset);

    renderProfile();
    renderTimetable();
    updateMetrics();
  }

  // Render Student Profile in Header & Sidebar
  function renderProfile() {
    if (!state.profile) return;
    const p = state.profile;

    document.getElementById("sidebar-student-name").textContent = p.name;
    document.getElementById("sidebar-student-info").textContent = `${p.rollNo} • ${p.semester}`;
    document.getElementById("sidebar-avatar").textContent = p.avatar;

    document.getElementById("header-student-name").textContent = p.name;
    document.getElementById("header-student-dept").textContent = `${p.year} - ${p.department.split('&')[0].trim()}`;
    document.getElementById("header-avatar").textContent = p.avatar;
    document.getElementById("current-date-text").textContent = window.APP_CONFIG?.CURRENT_DATE || "Friday, August 21, 2026";
  }

  // Render 8-Period × 6-Day Timetable Grid
  function renderTimetable() {
    const tbody = document.getElementById("timetable-body");
    if (!tbody || !state.timetable) return;

    const periods = ApiService.PERIOD_DEFINITIONS;
    let html = "";

    periods.forEach((slot, index) => {
      // Morning Break (between Period 2 and 3)
      if (index === 2) {
        html += `
          <tr class="bg-slate-100/60 border-y border-slate-200/80 text-[11px] font-medium text-slate-500">
            <td colspan="7" class="py-1.5 px-4 text-center tracking-wider uppercase text-[10px] font-semibold text-slate-400">
              ☕ Morning Break (10:15 – 10:30 AM)
            </td>
          </tr>
        `;
      }
      // Lunch Break (between Period 4 and 5)
      else if (index === 4) {
        html += `
          <tr class="bg-slate-100/60 border-y border-slate-200/80 text-[11px] font-medium text-slate-500">
            <td colspan="7" class="py-1.5 px-4 text-center tracking-wider uppercase text-[10px] font-semibold text-slate-400">
              🍱 Lunch Break (12:15 – 01:00 PM)
            </td>
          </tr>
        `;
      }

      html += `
        <tr class="hover:bg-slate-50/40 transition-colors">
          <!-- Sticky Period / Time Slot Column -->
          <td class="py-3 px-4 border-r border-slate-200 sticky left-0 bg-white font-medium z-10">
            <div class="font-heading font-bold text-slate-900 text-xs">${slot.label}</div>
            <div class="text-[10px] text-slate-400 font-mono mt-0.5">${slot.time}</div>
          </td>
      `;

      // 6 Days: Monday to Saturday
      DAYS.forEach(day => {
        const daySchedule = state.timetable[day] || [];
        const cell = daySchedule.find(p => p.period === slot.period) || { subject: "Self Study", status: "Upcoming" };
        const isToday = day === "Friday" && state.weekOffset === 0;

        html += `
          <td class="p-2 border-r border-slate-100 ${isToday ? 'bg-blue-50/20' : ''}">
            <div 
              class="timetable-cell rounded-xl p-2.5 border cursor-pointer ${getStatusCardClass(cell.status)} flex flex-col justify-between min-h-[64px]"
              onclick="window.handleCellClick('${day}', ${slot.period}, '${cell.subject}', '${cell.status}')"
              title="Click to view/update attendance for ${cell.subject}"
            >
              <!-- Subject Name -->
              <span class="font-heading font-bold text-xs tracking-tight text-slate-900 truncate">
                ${cell.subject}
              </span>

              <!-- Status Indicator Badge -->
              <div class="mt-1.5">
                ${getStatusPillHTML(cell.status)}
              </div>
            </div>
          </td>
        `;
      });

      html += `</tr>`;
    });

    tbody.innerHTML = html;
    initLucide();
  }

  function getStatusCardClass(status) {
    switch (status) {
      case "Present": return "status-present hover:border-emerald-300";
      case "Absent":  return "status-absent hover:border-rose-300";
      case "Leave":   return "status-leave hover:border-amber-300";
      case "Upcoming":
      default:        return "status-upcoming hover:border-slate-300";
    }
  }

  function getStatusPillHTML(status) {
    switch (status) {
      case "Present":
        return `
          <span class="status-pill status-pill-present">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
            Present
          </span>
        `;
      case "Absent":
        return `
          <span class="status-pill status-pill-absent">
            <span class="w-1.5 h-1.5 rounded-full bg-rose-600"></span>
            Absent
          </span>
        `;
      case "Leave":
        return `
          <span class="status-pill status-pill-leave">
            <span class="w-1.5 h-1.5 rounded-full bg-amber-600"></span>
            Leave
          </span>
        `;
      case "Upcoming":
      default:
        return `
          <span class="status-pill status-pill-upcoming">
            <span class="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
            Upcoming
          </span>
        `;
    }
  }

  // Update Summary Metrics (Overall 80%)
  function updateMetrics() {
    if (!state.timetable) return;
    const metrics = ApiService.calculateMetrics(state.timetable);

    document.getElementById("summary-percentage-value").textContent = `${metrics.rate}%`;
    document.getElementById("summary-percentage-text").textContent = `${metrics.rate}%`;
    document.getElementById("stat-present-count").textContent = metrics.present;
    document.getElementById("stat-absent-count").textContent = metrics.absent;
    document.getElementById("stat-leave-count").textContent = metrics.leave;
    document.getElementById("stat-upcoming-count").textContent = metrics.upcoming;

    const badge = document.getElementById("summary-policy-badge");
    if (metrics.isCompliant) {
      badge.className = "px-2 py-0.5 text-[11px] font-semibold rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200/60 flex items-center gap-1";
      badge.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Above 75% Policy`;
    } else {
      badge.className = "px-2 py-0.5 text-[11px] font-semibold rounded-full bg-rose-50 text-rose-700 border border-rose-200/60 flex items-center gap-1";
      badge.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span> Below 75% (Shortage Risk)`;
    }
  }

  // Week Switching
  function updateWeek(offsetChange) {
    state.weekOffset += offsetChange;
    const weekLabel = document.getElementById("week-date-range");
    const monLabel = document.getElementById("date-label-mon");
    const tueLabel = document.getElementById("date-label-tue");
    const wedLabel = document.getElementById("date-label-wed");
    const thuLabel = document.getElementById("date-label-thu");
    const friLabel = document.getElementById("date-label-fri");
    const satLabel = document.getElementById("date-label-sat");

    if (state.weekOffset === 0) {
      weekLabel.textContent = "August 17 – August 22, 2026";
      monLabel.textContent = "Aug 17";
      tueLabel.textContent = "Aug 18";
      wedLabel.textContent = "Aug 19";
      thuLabel.textContent = "Aug 20";
      friLabel.textContent = "Aug 21";
      satLabel.textContent = "Aug 22";
    } else if (state.weekOffset === -1) {
      weekLabel.textContent = "August 10 – August 15, 2026";
      monLabel.textContent = "Aug 10";
      tueLabel.textContent = "Aug 11";
      wedLabel.textContent = "Aug 12";
      thuLabel.textContent = "Aug 13";
      friLabel.textContent = "Aug 14";
      satLabel.textContent = "Aug 15";
    } else if (state.weekOffset === 1) {
      weekLabel.textContent = "August 24 – August 29, 2026";
      monLabel.textContent = "Aug 24";
      tueLabel.textContent = "Aug 25";
      wedLabel.textContent = "Aug 26";
      thuLabel.textContent = "Aug 27";
      friLabel.textContent = "Aug 28";
      satLabel.textContent = "Aug 29";
    } else {
      weekLabel.textContent = `Week Offset (${state.weekOffset > 0 ? '+' : ''}${state.weekOffset})`;
    }

    renderTimetable();
  }

  // Modal & Event Handlers
  function initEventHandlers() {
    document.getElementById("prev-week-btn").addEventListener("click", () => updateWeek(-1));
    document.getElementById("next-week-btn").addEventListener("click", () => updateWeek(1));
    document.getElementById("today-btn").addEventListener("click", () => {
      state.weekOffset = 0;
      updateWeek(0);
    });

    document.getElementById("close-modal-btn").addEventListener("click", closeModal);

    // Save status from modal
    document.getElementById("save-status-btn").addEventListener("click", async () => {
      if (!state.editingCell) return;
      const { day, period, newStatus, currentStatus } = state.editingCell;
      const targetStatus = newStatus || currentStatus;

      // Update in timetable data
      const schedule = state.timetable[day];
      const slot = schedule.find(p => p.period === period);
      if (slot) {
        slot.status = targetStatus;
      }

      await ApiService.updatePeriodStatus(state.studentId, day, period, targetStatus);
      renderTimetable();
      updateMetrics();
      closeModal();
    });
  }

  // Cell Click Handler (Global attachment for inline onclick)
  window.handleCellClick = function(day, period, subject, currentStatus) {
    state.editingCell = { day, period, subject, currentStatus, newStatus: currentStatus };

    document.getElementById("modal-subject-title").textContent = subject;
    const periodDef = ApiService.PERIOD_DEFINITIONS.find(p => p.period === period);
    document.getElementById("modal-period-subtitle").textContent = `Period ${period} • ${day} • ${periodDef ? periodDef.time : ''}`;

    // Highlight current status
    document.querySelectorAll(".status-btn").forEach(btn => {
      if (btn.getAttribute("data-status") === currentStatus) {
        btn.classList.add("ring-2", "ring-brand-500", "font-bold");
      } else {
        btn.classList.remove("ring-2", "ring-brand-500", "font-bold");
      }

      btn.onclick = () => {
        state.editingCell.newStatus = btn.getAttribute("data-status");
        document.querySelectorAll(".status-btn").forEach(b => b.classList.remove("ring-2", "ring-brand-500", "font-bold"));
        btn.classList.add("ring-2", "ring-brand-500", "font-bold");
      };
    });

    const modal = document.getElementById("period-modal");
    modal.classList.remove("hidden");
    setTimeout(() => modal.classList.add("active"), 10);
  };

  function closeModal() {
    const modal = document.getElementById("period-modal");
    modal.classList.remove("active");
    setTimeout(() => modal.classList.add("hidden"), 150);
  }

})();
