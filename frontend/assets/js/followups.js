/**
 * Follow-up Reminders Controller
 */

let activeType = "today";
let curPage = 1;
const limit = 25;

function formatDateTime(dtStr) {
  if (!dtStr) return "-";
  const dt = new Date(dtStr);
  return `${dt.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })} ${dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
}

// Preset helpers
function addMonthsToDate(date, months) {
  const d = new Date(date);
  const currentDay = d.getDate();
  d.setMonth(d.getMonth() + months);
  if (d.getDate() !== currentDay) d.setDate(0);
  return d;
}

function toLocalDatetimeInputString(date) {
  const pad = (n) => String(n).padStart(2, '0');
  const y = date.getFullYear();
  const m = pad(date.getMonth() + 1);
  const d = pad(date.getDate());
  const hh = pad(date.getHours());
  const mm = pad(date.getMinutes());
  return `${y}-${m}-${d}T${hh}:${mm}`;
}

window.setReschedPreset = function(days) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  d.setHours(10, 0, 0, 0);
  document.getElementById("resched-datetime").value = toLocalDatetimeInputString(d);
};

window.setReschedMonthPreset = function(months) {
  const d = addMonthsToDate(new Date(), months);
  d.setHours(10, 0, 0, 0);
  document.getElementById("resched-datetime").value = toLocalDatetimeInputString(d);
};

window.switchFollowupTab = function(type) {
  activeType = type;
  curPage = 1;

  // Update tabs UI
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.type === type);
  });

  // Update page title
  const titles = {
    today: "Today's Follow-up Tasks",
    due_soon: "Approaching Follow-ups (Due Soon Notice Window)",
    upcoming: "Upcoming Scheduled Follow-ups",
    overdue: "Overdue Customer Follow-ups",
    completed: "Completed Follow-up History"
  };
  document.getElementById("page-title").textContent = titles[type] || "Follow-up Reminders";

  loadFollowupsList();
};

async function loadFollowupsList() {
  const tbody = document.getElementById("followups-tbody");
  tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding:32px;">Loading tasks...</td></tr>`;

  try {
    const res = await window.api.get("/api/followups", {
      filter_type: activeType,
      page: curPage,
      per_page: limit
    });

    if (res.advance_days) {
      document.querySelectorAll(".advance-days-lbl").forEach(el => {
        el.textContent = res.advance_days;
      });
    }

    const total = res.total;
    const start = total === 0 ? 0 : (curPage - 1) * limit + 1;
    const end = Math.min(curPage * limit, total);
    document.getElementById("followups-page-info").textContent = `Showing ${start} to ${end} of ${total.toLocaleString()} tasks`;
    document.getElementById("txt-page").textContent = `Page ${curPage} of ${res.total_pages || 1}`;

    document.getElementById("btn-prev").disabled = curPage <= 1;
    document.getElementById("btn-next").disabled = curPage >= res.total_pages;

    if (!res.items || res.items.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="9">
            <div class="empty-state">
              <div class="empty-state-title">No ${activeType === 'due_soon' ? 'Approaching' : activeType} Follow-ups</div>
              <div class="empty-state-text">There are currently no follow-up tasks in this category.</div>
            </div>
          </td>
        </tr>`;
      return;
    }

    tbody.innerHTML = res.items.map(f => {
      const isCompleted = f.status === 'Completed';
      let statusBadge = '<span class="badge badge-pending">Pending</span>';
      if (isCompleted) {
        statusBadge = '<span class="badge badge-completed">Completed</span>';
      } else if (f.is_overdue) {
        statusBadge = `<span class="badge badge-overdue">${f.overdue_text || 'Overdue'}</span>`;
      } else if (f.is_due_soon && f.due_soon_text) {
        statusBadge = f.days_until_due === 0 
          ? '<span class="badge badge-pending" style="font-weight:600;">Due Today</span>'
          : (f.days_until_due === 1 
              ? '<span class="badge badge-duesoon">Due Tomorrow</span>' 
              : `<span class="badge badge-info">${f.due_soon_text}</span>`);
      }

      const phoneLink = f.customer_mobile 
        ? `<a href="tel:${f.customer_mobile}" style="font-family:var(--font-mono); font-weight:500;">${f.customer_mobile}</a>`
        : '<span style="color:#94a3b8;">-</span>';

      return `
        <tr>
          <td>
            <a href="/customer-details.html?id=${f.customer_id}" style="font-weight:600; color:var(--text-primary);">
              ${f.customer_name}
            </a>
          </td>
          <td>${phoneLink}</td>
          <td>${f.customer_company || '-'}</td>
          <td>${f.customer_city || '-'}</td>
          <td style="font-weight:600;">${formatDateTime(f.scheduled_at)}</td>
          <td><span class="badge badge-neutral">${f.priority}</span></td>
          <td>${statusBadge}</td>
          <td style="font-size:12.5px; color:var(--text-secondary); max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
            ${f.notes || '-'}
          </td>
          <td style="text-align:right;">
            ${!isCompleted ? `
              <div style="display:inline-flex; gap:6px;">
                <button class="btn btn-primary btn-sm" onclick="openCompleteModal(${f.id}, '${f.customer_name.replace(/'/g, "\\'")}')">
                  Call & Done
                </button>
                <button class="btn btn-secondary btn-sm" onclick="openReschedModal(${f.id}, '${f.scheduled_at}')">
                  Reschedule
                </button>
                <button class="btn btn-danger btn-sm" onclick="cancelTask(${f.id})">
                  ✕
                </button>
              </div>
            ` : `<span style="color:#10b981; font-weight:600;">Done on ${formatDate(f.completed_at)}</span>`}
          </td>
        </tr>
      `;
    }).join("");

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; color:var(--danger-text); padding:24px;">Failed to load follow-ups: ${err.message}</td></tr>`;
  }
}

window.openCompleteModal = function(id, name) {
  document.getElementById("modal-followup-id").value = id;
  document.getElementById("modal-customer-name").textContent = `Completing task for: ${name}`;
  document.getElementById("modal-notes").value = "";
  document.getElementById("modal-next-action").value = "";
  document.getElementById("modal-next-sched").value = "";
  openModal("callModal");
};

window.openReschedModal = function(id, curScheduled) {
  document.getElementById("resched-id").value = id;
  document.getElementById("resched-reason").value = "";
  if (curScheduled) {
    document.getElementById("resched-datetime").value = toLocalDatetimeInputString(new Date(curScheduled));
  } else {
    window.setReschedPreset(1);
  }
  openModal("rescheduleModal");
};

window.cancelTask = async function(id) {
  if (confirm("Are you sure you want to cancel this follow-up reminder?")) {
    try {
      await window.api.post(`/api/followups/${id}/cancel`);
      showToast("Follow-up cancelled.", "info");
      loadFollowupsList();
    } catch (err) {
      showToast(err.message || "Failed to cancel", "danger");
    }
  }
};

document.addEventListener("DOMContentLoaded", () => {
  const p = new URLSearchParams(window.location.search);
  const requestedType = p.get("type");
  if (requestedType && ["today", "due_soon", "upcoming", "overdue", "completed"].includes(requestedType)) {
    switchFollowupTab(requestedType);
  } else {
    loadFollowupsList();
  }

  // Pagination buttons
  document.getElementById("btn-prev").onclick = () => {
    if (curPage > 1) { curPage--; loadFollowupsList(); }
  };
  document.getElementById("btn-next").onclick = () => {
    curPage++; loadFollowupsList();
  };

  // Complete Form Submit
  document.getElementById("completeCallForm").onsubmit = async (e) => {
    e.preventDefault();
    const id = document.getElementById("modal-followup-id").value;
    const outcome = document.getElementById("modal-outcome").value;
    const notes = document.getElementById("modal-notes").value;
    const nextAction = document.getElementById("modal-next-action").value;
    const nextSched = document.getElementById("modal-next-sched").value;

    try {
      await window.api.post(`/api/followups/${id}/complete`, {
        outcome,
        notes,
        next_action: nextAction,
        schedule_next_followup: nextSched ? new Date(nextSched).toISOString() : null
      });

      showToast("Call logged and task marked as completed!", "success");
      closeModal("callModal");
      loadFollowupsList();
    } catch (err) {
      showToast(err.message || "Failed to complete task", "danger");
    }
  };

  // Reschedule Form Submit
  document.getElementById("rescheduleForm").onsubmit = async (e) => {
    e.preventDefault();
    const id = document.getElementById("resched-id").value;
    const newDt = document.getElementById("resched-datetime").value;
    const reason = document.getElementById("resched-reason").value;

    try {
      await window.api.post(`/api/followups/${id}/reschedule`, {
        new_scheduled_at: new Date(newDt).toISOString(),
        reason
      });

      showToast("Task rescheduled successfully!", "success");
      closeModal("rescheduleModal");
      loadFollowupsList();
    } catch (err) {
      showToast(err.message || "Failed to reschedule", "danger");
    }
  };
});
