/**
 * Dashboard Controller
 */

function formatTime(dtStr) {
  if (!dtStr) return "-";
  const dt = new Date(dtStr);
  return dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatDate(dtStr) {
  if (!dtStr) return "-";
  const dt = new Date(dtStr);
  return dt.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatDateTime(dtStr) {
  if (!dtStr) return "-";
  const dt = new Date(dtStr);
  return `${formatDate(dtStr)} ${formatTime(dtStr)}`;
}

// Calendar arithmetic in JS (Handles 31st January + 1 month -> 28th Feb)
function addMonthsToDate(date, months) {
  const d = new Date(date);
  const currentDay = d.getDate();
  d.setMonth(d.getMonth() + months);
  // If day changed (e.g. Feb 31 -> March 3), reset to last day of previous month
  if (d.getDate() !== currentDay) {
    d.setDate(0);
  }
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

// Preset helpers for Log Call modal
window.setCallNextDatePreset = function(days) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  d.setHours(10, 0, 0, 0); // default 10:00 AM
  document.getElementById("call-next-date").value = toLocalDatetimeInputString(d);
};

window.setCallNextMonthPreset = function(months) {
  const d = addMonthsToDate(new Date(), months);
  d.setHours(10, 0, 0, 0);
  document.getElementById("call-next-date").value = toLocalDatetimeInputString(d);
};

// Preset helpers for Reschedule modal
window.setReschedulePreset = function(days) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  d.setHours(10, 0, 0, 0);
  document.getElementById("reschedule-date").value = toLocalDatetimeInputString(d);
};

window.setRescheduleMonthPreset = function(months) {
  const d = addMonthsToDate(new Date(), months);
  d.setHours(10, 0, 0, 0);
  document.getElementById("reschedule-date").value = toLocalDatetimeInputString(d);
};

// Open Log Call Modal for a customer/followup
window.openLogCallModal = function(customerId, customerName, followupId = null) {
  document.getElementById("call-customer-id").value = customerId;
  document.getElementById("call-followup-id").value = followupId || "";
  document.getElementById("call-customer-name-display").textContent = `Customer: ${customerName}`;
  document.getElementById("call-notes").value = "";
  document.getElementById("call-next-action").value = "";
  document.getElementById("call-next-date").value = "";
  openModal("logCallModal");
};

// Open Reschedule Modal
window.openRescheduleModal = function(followupId, customerName, currentScheduledAt) {
  document.getElementById("reschedule-followup-id").value = followupId;
  document.getElementById("reschedule-customer-display").textContent = `Rescheduling follow-up for: ${customerName}`;
  document.getElementById("reschedule-reason").value = "";
  
  if (currentScheduledAt) {
    const curDate = new Date(currentScheduledAt);
    document.getElementById("reschedule-date").value = toLocalDatetimeInputString(curDate);
  } else {
    window.setReschedulePreset(1);
  }
  openModal("rescheduleModal");
};

// Main Load Function
async function loadDashboardOverview() {
  try {
    const data = await window.api.get("/api/dashboard/overview");
    const stats = data.stats;

    // 1. Populate stats cards
    document.getElementById("stat-total-customers").textContent = stats.total_customers.toLocaleString();
    document.getElementById("stat-today-followups").textContent = stats.today_followups_count.toLocaleString();
    const dueSoonStatEl = document.getElementById("stat-due-soon-followups");
    if (dueSoonStatEl) {
      dueSoonStatEl.textContent = (data.due_soon_count != null ? data.due_soon_count : stats.due_soon_followups_count || 0).toLocaleString();
    }
    document.getElementById("stat-overdue-followups").textContent = stats.overdue_followups_count.toLocaleString();
    document.getElementById("stat-upcoming-followups").textContent = stats.upcoming_followups_count.toLocaleString();
    document.getElementById("stat-completed-calls").textContent = stats.completed_calls_count.toLocaleString();

    if (data.reminder_advance_days) {
      document.querySelectorAll(".advance-days-lbl").forEach(el => {
        el.textContent = data.reminder_advance_days;
      });
    }

    const dueSoonBadge = document.getElementById("due-soon-count-badge");
    if (dueSoonBadge) {
      dueSoonBadge.textContent = `${data.due_soon_count || 0} Approaching`;
    }

    // 2. Render Approaching / Due Soon Reminders Table (5 Days Advance Notice)
    const dueSoonTbody = document.getElementById("due-soon-followups-tbody");
    if (dueSoonTbody) {
      if (!data.due_soon_followups || data.due_soon_followups.length === 0) {
        dueSoonTbody.innerHTML = `
          <tr>
            <td colspan="7">
              <div class="empty-state" style="padding:24px;">
                <div class="empty-state-title" style="font-size:14px;">No Approaching Reminders</div>
                <div class="empty-state-text" style="font-size:12px; margin-bottom:8px;">
                  There are no follow-ups scheduled in the next ${data.reminder_advance_days || 5} days. You are completely on track!
                </div>
              </div>
            </td>
          </tr>`;
      } else {
        dueSoonTbody.innerHTML = data.due_soon_followups.map(f => {
          const priorityBadge = f.priority === 'Urgent' 
            ? '<span class="badge badge-overdue">Urgent</span>'
            : (f.priority === 'High' ? '<span class="badge badge-pending">High</span>' : `<span class="badge badge-neutral">${f.priority}</span>`);
          
          const phoneLink = f.customer_mobile 
            ? `<a href="tel:${f.customer_mobile}" style="font-family:var(--font-mono); color:var(--primary); font-weight:500;">${f.customer_mobile}</a>`
            : '<span style="color:var(--text-muted);">-</span>';

          const noticeBadge = f.due_soon_text 
            ? (f.days_until_due === 0 
                ? '<span class="badge badge-pending" style="font-weight:600;">Due Today</span>' 
                : (f.days_until_due === 1 
                    ? '<span class="badge badge-duesoon">Due Tomorrow</span>' 
                    : `<span class="badge badge-info">${f.due_soon_text}</span>`))
            : '<span class="badge badge-neutral">Approaching</span>';

          return `
            <tr>
              <td>
                <a href="/customer-details.html?id=${f.customer_id}" style="font-weight:600; color:var(--text-primary);">
                  ${f.customer_name}
                </a>
                ${f.customer_company ? `<div style="font-size:11.5px; color:var(--text-muted);">${f.customer_company}</div>` : ''}
              </td>
              <td>${phoneLink}</td>
              <td style="font-weight:500;">${formatDateTime(f.scheduled_at)}</td>
              <td>${noticeBadge}</td>
              <td>${priorityBadge}</td>
              <td style="max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:12.5px; color:var(--text-secondary);">
                ${f.notes || '-'}
              </td>
              <td style="text-align:right;">
                <div style="display:inline-flex; gap:6px;">
                  <button class="btn btn-primary btn-sm" onclick="openLogCallModal(${f.customer_id}, '${f.customer_name.replace(/'/g, "\\'")}', ${f.id})">
                    Call
                  </button>
                  <button class="btn btn-secondary btn-sm" onclick="openRescheduleModal(${f.id}, '${f.customer_name.replace(/'/g, "\\'")}', '${f.scheduled_at}')">
                    Reschedule
                  </button>
                </div>
              </td>
            </tr>
          `;
        }).join("");
      }
    }

    // 2. Render Today's Follow-ups Table
    const todayTbody = document.getElementById("today-followups-tbody");
    if (!data.today_followups || data.today_followups.length === 0) {
      todayTbody.innerHTML = `
        <tr>
          <td colspan="6">
            <div class="empty-state" style="padding:24px;">
              <div class="empty-state-title" style="font-size:14px;">No Follow-ups Due Today!</div>
              <div class="empty-state-text" style="font-size:12px; margin-bottom:8px;">All tasks scheduled for today have been completed or none were scheduled.</div>
            </div>
          </td>
        </tr>`;
    } else {
      todayTbody.innerHTML = data.today_followups.map(f => {
        const priorityBadge = f.priority === 'Urgent' 
          ? '<span class="badge badge-overdue">Urgent</span>'
          : (f.priority === 'High' ? '<span class="badge badge-pending">High</span>' : `<span class="badge badge-neutral">${f.priority}</span>`);
        
        const phoneLink = f.customer_mobile 
          ? `<a href="tel:${f.customer_mobile}" style="font-family:var(--font-mono); color:var(--primary); font-weight:500;">${f.customer_mobile}</a>`
          : '<span style="color:var(--text-muted);">-</span>';

        return `
          <tr>
            <td>
              <a href="/customer-details.html?id=${f.customer_id}" style="font-weight:600; color:var(--text-primary);">
                ${f.customer_name}
              </a>
              ${f.customer_company ? `<div style="font-size:11.5px; color:var(--text-muted);">${f.customer_company}</div>` : ''}
            </td>
            <td>${phoneLink}</td>
            <td style="font-weight:500;">${formatTime(f.scheduled_at)}</td>
            <td>${priorityBadge}</td>
            <td style="max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:12.5px; color:var(--text-secondary);">
              ${f.notes || '-'}
            </td>
            <td style="text-align:right;">
              <div style="display:inline-flex; gap:6px;">
                <button class="btn btn-primary btn-sm" onclick="openLogCallModal(${f.customer_id}, '${f.customer_name.replace(/'/g, "\\'")}', ${f.id})">
                  Call
                </button>
                <button class="btn btn-secondary btn-sm" onclick="openRescheduleModal(${f.id}, '${f.customer_name.replace(/'/g, "\\'")}', '${f.scheduled_at}')">
                  Reschedule
                </button>
              </div>
            </td>
          </tr>
        `;
      }).join("");
    }

    // 3. Render Overdue Tasks List
    const overdueContainer = document.getElementById("overdue-list-container");
    if (!data.overdue_followups || data.overdue_followups.length === 0) {
      overdueContainer.innerHTML = `
        <div class="empty-state" style="padding:20px;">
          <div style="color:var(--success); font-weight:600; font-size:14px; margin-bottom:4px;">No Overdue Calls!</div>
          <div style="font-size:12px; color:var(--text-muted);">All scheduled reminders are up-to-date.</div>
        </div>`;
    } else {
      overdueContainer.innerHTML = data.overdue_followups.map(f => {
        return `
          <div style="padding:10px 0; border-bottom:1px solid var(--border-color); display:flex; justify-content:space-between; align-items:flex-start;">
            <div>
              <a href="/customer-details.html?id=${f.customer_id}" style="font-weight:600; color:var(--text-primary); font-size:13.5px;">
                ${f.customer_name}
              </a>
              <div style="display:flex; align-items:center; gap:8px; margin-top:2px;">
                <span class="badge badge-overdue" style="font-size:11px;">${f.overdue_text || 'Overdue'}</span>
                ${f.customer_mobile ? `<a href="tel:${f.customer_mobile}" style="font-size:12px; font-family:var(--font-mono);">${f.customer_mobile}</a>` : ''}
              </div>
              ${f.notes ? `<div style="font-size:11.5px; color:var(--text-muted); margin-top:4px;">${f.notes}</div>` : ''}
            </div>
            <div style="display:flex; gap:6px; flex-shrink:0;">
              <button class="btn btn-primary btn-sm" onclick="openLogCallModal(${f.customer_id}, '${f.customer_name.replace(/'/g, "\\'")}', ${f.id})">
                Call
              </button>
              <button class="btn btn-secondary btn-sm" onclick="openRescheduleModal(${f.id}, '${f.customer_name.replace(/'/g, "\\'")}', '${f.scheduled_at}')">
                Reschedule
              </button>
            </div>
          </div>
        `;
      }).join("");
    }

    // 4. Render Recent Imports Table
    const recentImportsTbody = document.getElementById("recent-imports-tbody");
    if (!data.recent_imports || data.recent_imports.length === 0) {
      recentImportsTbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:20px; color:var(--text-muted);">No Excel files uploaded yet. <a href="/imports.html">Upload now</a></td></tr>`;
    } else {
      recentImportsTbody.innerHTML = data.recent_imports.map(file => {
        const statusBadge = file.status === 'Completed' 
          ? '<span class="badge badge-completed">Completed</span>'
          : '<span class="badge badge-pending">Partial</span>';
        
        return `
          <tr>
            <td style="font-weight:500;">
              <a href="/month-files.html?file_id=${file.id}">${file.original_filename}</a>
            </td>
            <td>${file.import_month}/${file.import_year}</td>
            <td>${file.imported_rows} rows</td>
            <td>${statusBadge}</td>
          </tr>
        `;
      }).join("");
    }

    // 5. Render Recent Calls Container
    const recentCallsContainer = document.getElementById("recent-calls-container");
    if (!data.recent_calls || data.recent_calls.length === 0) {
      recentCallsContainer.innerHTML = `<div style="text-align:center; padding:20px; color:var(--text-muted);">No calls logged yet.</div>`;
    } else {
      recentCallsContainer.innerHTML = data.recent_calls.map(c => {
        const outcomeBadge = c.outcome === 'Converted'
          ? '<span class="badge badge-completed">Converted</span>'
          : (c.outcome === 'Interested' ? '<span class="badge badge-scheduled">Interested</span>' : `<span class="badge badge-neutral">${c.outcome}</span>`);

        return `
          <div style="padding:10px 0; border-bottom:1px solid var(--border-color); display:flex; justify-content:space-between; align-items:center;">
            <div>
              <div style="font-weight:600; font-size:13px;">
                <a href="/customer-details.html?id=${c.customer_id}">${c.customer_name}</a>
              </div>
              <div style="font-size:12px; color:var(--text-secondary); margin-top:2px;">
                ${c.notes || c.next_action || 'No additional notes'}
              </div>
            </div>
            <div style="text-align:right;">
              ${outcomeBadge}
              <div style="font-size:11px; color:var(--text-muted); margin-top:4px;">${formatDateTime(c.call_datetime)}</div>
            </div>
          </div>
        `;
      }).join("");
    }

  } catch (err) {
    console.error("Failed to load dashboard overview:", err);
    showToast("Failed to load dashboard metrics.", "danger");
  }
}

// Form Handlers
document.addEventListener("DOMContentLoaded", () => {
  loadDashboardOverview();

  // Log Call Form Submit
  const logCallForm = document.getElementById("logCallForm");
  if (logCallForm) {
    logCallForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const customerId = document.getElementById("call-customer-id").value;
      const followupId = document.getElementById("call-followup-id").value;
      const outcome = document.getElementById("call-outcome").value;
      const notes = document.getElementById("call-notes").value;
      const nextAction = document.getElementById("call-next-action").value;
      const nextDate = document.getElementById("call-next-date").value;

      try {
        await window.api.post(`/api/customers/${customerId}/calls`, {
          outcome,
          notes,
          next_action: nextAction,
          followup_id: followupId ? parseInt(followupId) : null,
          schedule_next_followup: nextDate ? new Date(nextDate).toISOString() : null
        });

        showToast("Call logged successfully!", "success");
        closeModal("logCallModal");
        loadDashboardOverview();
      } catch (err) {
        showToast(err.message || "Failed to log call", "danger");
      }
    });
  }

  // Reschedule Form Submit
  const rescheduleForm = document.getElementById("rescheduleForm");
  if (rescheduleForm) {
    rescheduleForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const followupId = document.getElementById("reschedule-followup-id").value;
      const newDate = document.getElementById("reschedule-date").value;
      const reason = document.getElementById("reschedule-reason").value;

      if (!newDate) {
        showToast("Please choose a valid new schedule date", "warning");
        return;
      }

      try {
        await window.api.post(`/api/followups/${followupId}/reschedule`, {
          new_scheduled_at: new Date(newDate).toISOString(),
          reason
        });

        showToast("Follow-up rescheduled successfully!", "success");
        closeModal("rescheduleModal");
        loadDashboardOverview();
      } catch (err) {
        showToast(err.message || "Failed to reschedule", "danger");
      }
    });
  }

  // Add Customer Form Submit
  const addCustomerForm = document.getElementById("addCustomerForm");
  if (addCustomerForm) {
    addCustomerForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const name = document.getElementById("new-cust-name").value.trim();
      const customer_code = document.getElementById("new-cust-code").value.trim();
      const mobile = document.getElementById("new-cust-mobile").value.trim();
      const alternate_phone = document.getElementById("new-cust-altphone").value.trim();
      const email = document.getElementById("new-cust-email").value.trim();
      const company = document.getElementById("new-cust-company").value.trim();
      const city = document.getElementById("new-cust-city").value.trim();
      const state = document.getElementById("new-cust-state").value.trim();
      const address = document.getElementById("new-cust-address").value.trim();

      try {
        await window.api.post("/api/customers", {
          name,
          customer_code: customer_code || null,
          mobile: mobile || null,
          alternate_phone: alternate_phone || null,
          email: email || null,
          company: company || null,
          city: city || null,
          state: state || null,
          address: address || null,
          source: "Manual Entry"
        });

        showToast("Customer added successfully!", "success");
        addCustomerForm.reset();
        closeModal("addCustomerModal");
        loadDashboardOverview();
      } catch (err) {
        showToast(err.message || "Failed to add customer", "danger");
      }
    });
  }
});
