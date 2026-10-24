/**
 * Customer Profile & Timeline Controller
 */

const params = new URLSearchParams(window.location.search);
const customerId = params.get("id");
let currentCustomer = null;

function formatDateTime(dtStr) {
  if (!dtStr) return "-";
  const dt = new Date(dtStr);
  return `${dt.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })} ${dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
}

function formatDate(dtStr) {
  if (!dtStr) return "-";
  const dt = new Date(dtStr);
  return dt.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
}

// Preset helpers
function addMonthsToDate(date, months) {
  const d = new Date(date);
  const currentDay = d.getDate();
  d.setMonth(d.getMonth() + months);
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

window.setSchedulePreset = function(days) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  d.setHours(10, 0, 0, 0);
  document.getElementById("sched-date").value = toLocalDatetimeInputString(d);
};

window.setScheduleMonthPreset = function(months) {
  const d = addMonthsToDate(new Date(), months);
  d.setHours(10, 0, 0, 0);
  document.getElementById("sched-date").value = toLocalDatetimeInputString(d);
};

async function loadProfile() {
  if (!customerId) {
    showToast("No customer ID specified.", "danger");
    setTimeout(() => window.location.href = "/customers.html", 1500);
    return;
  }

  try {
    const data = await window.api.get(`/api/customers/${customerId}`);
    currentCustomer = data;

    // Header & Info
    document.getElementById("profile-heading-name").textContent = data.name;
    document.getElementById("info-name").textContent = data.name;
    document.getElementById("info-code").textContent = data.customer_code || `#${data.id}`;

    // Mobile link
    const mobLink = document.getElementById("info-mobile-link");
    if (data.mobile) {
      mobLink.textContent = data.mobile;
      mobLink.href = `tel:${data.mobile}`;
    } else {
      mobLink.textContent = "None";
      mobLink.removeAttribute("href");
    }

    document.getElementById("info-altphone").textContent = data.alternate_phone || "None";
    document.getElementById("info-email").textContent = data.email || "None";
    document.getElementById("info-company").textContent = data.company || "None";
    document.getElementById("info-location").textContent = [data.city, data.state, data.country].filter(Boolean).join(", ") || "-";
    document.getElementById("info-address").textContent = data.address || "-";
    document.getElementById("info-source").textContent = data.source || "Manual Entry";
    document.getElementById("info-last-contacted").textContent = data.last_contacted_at ? formatDateTime(data.last_contacted_at) : "Never";

    // Source File link
    const sourceEl = document.getElementById("info-source-file");
    if (data.source_file) {
      sourceEl.innerHTML = `<a href="/month-files.html?file_id=${data.source_file.file_id}">${data.source_file.filename}</a> (Row ${data.source_file.row_number})`;
    } else {
      sourceEl.textContent = "Manual / None";
    }

    // Status Badge
    const badge = document.getElementById("cust-status-badge");
    badge.textContent = data.status || "New";
    badge.className = `badge ${data.status === 'Converted' ? 'badge-completed' : (data.status === 'Interested' ? 'badge-scheduled' : 'badge-neutral')}`;

    // Custom Fields
    const customContainer = document.getElementById("custom-fields-container");
    const cfKeys = Object.keys(data.custom_fields || {});
    if (cfKeys.length === 0) {
      customContainer.innerHTML = `<div style="font-size:13px; color:var(--text-muted);">No extra custom fields for this record.</div>`;
    } else {
      customContainer.innerHTML = cfKeys.map(k => {
        return `
          <div style="display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px dashed var(--border-color); font-size:13px;">
            <span style="color:var(--text-muted); font-weight:500;">${k}:</span>
            <span style="font-weight:600; color:var(--text-primary);">${data.custom_fields[k]}</span>
          </div>
        `;
      }).join("");
    }

    // Scheduled Follow-ups
    const fTbody = document.getElementById("customer-followups-tbody");
    if (!data.followups || data.followups.length === 0) {
      fTbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:16px; color:var(--text-muted);">No follow-ups scheduled yet.</td></tr>`;
    } else {
      fTbody.innerHTML = data.followups.map(f => {
        const isCompleted = f.status === 'Completed';
        const stBadge = isCompleted ? '<span class="badge badge-completed">Completed</span>' : '<span class="badge badge-pending">Pending</span>';
        return `
          <tr>
            <td style="font-weight:600;">${formatDateTime(f.scheduled_at)}</td>
            <td><span class="badge badge-neutral">${f.priority}</span></td>
            <td>${stBadge}</td>
            <td style="font-size:12.5px; color:var(--text-secondary);">${f.notes || '-'}</td>
            <td style="text-align:right;">
              ${!isCompleted ? `<button class="btn btn-secondary btn-sm" onclick="markFollowupDone(${f.id})">Mark Done</button>` : '<span style="color:#10b981;">✓</span>'}
            </td>
          </tr>
        `;
      }).join("");
    }

    // Call History Timeline
    const timeline = document.getElementById("calls-timeline");
    if (!data.calls || data.calls.length === 0) {
      timeline.innerHTML = `<div style="color:var(--text-muted); font-size:13px; padding:12px 0;">No calls logged for this customer yet. Use the 'Log Call' button above.</div>`;
    } else {
      timeline.innerHTML = data.calls.map(c => {
        const outcomeBadge = c.outcome === 'Converted' ? 'badge-completed' : (c.outcome === 'Interested' ? 'badge-scheduled' : 'badge-neutral');
        return `
          <div class="timeline-item">
            <div class="timeline-dot"></div>
            <div class="timeline-content">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                <span class="badge ${outcomeBadge}">${c.outcome}</span>
                <span style="font-size:11.5px; color:var(--text-muted);">${formatDateTime(c.call_datetime)}</span>
              </div>
              <div style="font-size:13px; color:var(--text-primary); margin-bottom:4px;">
                ${c.notes || 'No call summary provided.'}
              </div>
              ${c.next_action ? `<div style="font-size:12px; color:var(--primary); font-weight:500;">Next action: ${c.next_action}</div>` : ''}
              <div style="font-size:11px; color:var(--text-muted); margin-top:4px;">Logged by: ${c.caller}</div>
            </div>
          </div>
        `;
      }).join("");
    }

  } catch (err) {
    showToast(err.message || "Failed to load customer profile", "danger");
  }
}

window.markFollowupDone = async function(followupId) {
  if (confirm("Mark this follow-up as completed?")) {
    try {
      await window.api.post(`/api/followups/${followupId}/complete`, {
        outcome: "Interested",
        notes: "Marked done directly from customer profile."
      });
      showToast("Follow-up marked completed!", "success");
      loadProfile();
    } catch (err) {
      showToast(err.message || "Failed to complete", "danger");
    }
  }
};

document.addEventListener("DOMContentLoaded", () => {
  loadProfile();

  // Open modals
  document.getElementById("btn-open-call").onclick = () => openModal("logCallModal");
  document.getElementById("btn-open-schedule").onclick = () => {
    window.setSchedulePreset(1);
    openModal("scheduleModal");
  };
  document.getElementById("btn-open-edit").onclick = () => {
    if (!currentCustomer) return;
    document.getElementById("edit-name").value = currentCustomer.name || "";
    document.getElementById("edit-code").value = currentCustomer.customer_code || "";
    document.getElementById("edit-mobile").value = currentCustomer.mobile || "";
    document.getElementById("edit-altphone").value = currentCustomer.alternate_phone || "";
    document.getElementById("edit-email").value = currentCustomer.email || "";
    document.getElementById("edit-company").value = currentCustomer.company || "";
    document.getElementById("edit-city").value = currentCustomer.city || "";
    document.getElementById("edit-state").value = currentCustomer.state || "";
    document.getElementById("edit-address").value = currentCustomer.address || "";
    document.getElementById("edit-status").value = currentCustomer.status || "New";
    if (document.getElementById("edit-category")) {
      document.getElementById("edit-category").value = currentCustomer.category || "General";
    }

    // Dynamic custom fields
    const customFieldsGroup = document.getElementById("edit-custom-fields-group");
    const customFieldsContainer = document.getElementById("edit-custom-fields-container");
    if (customFieldsGroup && customFieldsContainer) {
      if (currentCustomer.custom_fields && Object.keys(currentCustomer.custom_fields).length > 0) {
        customFieldsGroup.style.display = "block";
        customFieldsContainer.innerHTML = Object.keys(currentCustomer.custom_fields).map(key => `
          <div class="form-group" style="margin-bottom:8px;">
            <label class="form-label" style="font-size:12px;">${key}</label>
            <input type="text" class="form-control form-control-sm edit-custom-field-input" data-key="${key}" value="${currentCustomer.custom_fields[key] || ''}">
          </div>
        `).join("");
      } else {
        customFieldsGroup.style.display = "none";
        customFieldsContainer.innerHTML = "";
      }
    }

    openModal("editCustomerModal");
  };

  // Submit Edit Customer
  document.getElementById("editCustomerForm").onsubmit = async (e) => {
    e.preventDefault();
    try {
      // Gather custom fields
      let updatedCustomFields = currentCustomer.custom_fields ? { ...currentCustomer.custom_fields } : {};
      const customInputs = document.querySelectorAll(".edit-custom-field-input");
      customInputs.forEach(input => {
        const key = input.getAttribute("data-key");
        if (key) {
          updatedCustomFields[key] = input.value.trim();
        }
      });

      await window.api.put(`/api/customers/${customerId}`, {
        name: document.getElementById("edit-name").value.trim(),
        customer_code: document.getElementById("edit-code").value.trim() || null,
        mobile: document.getElementById("edit-mobile").value.trim() || null,
        alternate_phone: document.getElementById("edit-altphone").value.trim() || null,
        email: document.getElementById("edit-email").value.trim() || null,
        company: document.getElementById("edit-company").value.trim() || null,
        city: document.getElementById("edit-city").value.trim() || null,
        state: document.getElementById("edit-state").value.trim() || null,
        address: document.getElementById("edit-address").value.trim() || null,
        category: document.getElementById("edit-category") ? document.getElementById("edit-category").value.trim() : "General",
        status: document.getElementById("edit-status").value,
        custom_fields: Object.keys(updatedCustomFields).length > 0 ? updatedCustomFields : null
      });

      showToast("Customer updated successfully!", "success");
      closeModal("editCustomerModal");
      loadProfile();
    } catch (err) {
      showToast(err.message || "Failed to update customer", "danger");
    }
  };

  // Submit Schedule Follow-up
  document.getElementById("scheduleForm").onsubmit = async (e) => {
    e.preventDefault();
    const schedDate = document.getElementById("sched-date").value;
    const priority = document.getElementById("sched-priority").value;
    const notes = document.getElementById("sched-notes").value;

    try {
      await window.api.post("/api/followups", {
        customer_id: parseInt(customerId),
        scheduled_at: new Date(schedDate).toISOString(),
        priority,
        notes
      });

      showToast("Follow-up scheduled!", "success");
      closeModal("scheduleModal");
      loadProfile();
    } catch (err) {
      showToast(err.message || "Failed to schedule", "danger");
    }
  };

  // Submit Log Call
  document.getElementById("logCallForm").onsubmit = async (e) => {
    e.preventDefault();
    const outcome = document.getElementById("call-outcome").value;
    const notes = document.getElementById("call-notes").value;
    const nextAction = document.getElementById("call-next-action").value;

    try {
      await window.api.post(`/api/customers/${customerId}/calls`, {
        outcome,
        notes,
        next_action: nextAction
      });

      showToast("Call logged successfully!", "success");
      closeModal("logCallModal");
      loadProfile();
    } catch (err) {
      showToast(err.message || "Failed to log call", "danger");
    }
  };
});
