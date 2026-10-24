/**
 * Call History & Completed Work Activity Controller
 * Full-featured filtering and PDF/Excel export.
 */

let curCallPage = 1;
const callLimit = 25;
let callSearch = "";
let callOutcome = "";
let callDatePreset = "";
let callDateFrom = "";
let callDateTo = "";
let callFileId = "";
let searchTimer = null;

function formatDateTime(dtStr) {
  if (!dtStr) return "-";
  const dt = new Date(dtStr);
  return `${dt.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })} ${dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
}

function getOutcomeBadge(outcome) {
  switch (outcome) {
    case "Converted": return '<span class="badge badge-completed">✅ Completed</span>';
    case "Interested": return '<span class="badge badge-scheduled">⭐ Interested</span>';
    case "Call Back Required": return '<span class="badge badge-pending">📅 Call Back</span>';
    case "Not Interested": return '<span class="badge badge-overdue">✕ Not Interested</span>';
    case "Busy": return '<span class="badge badge-neutral">⏳ Busy</span>';
    case "No Answer": return '<span class="badge badge-neutral">📞 No Answer</span>';
    default: return `<span class="badge badge-neutral">${outcome || 'Completed'}</span>`;
  }
}

/**
 * Load uploaded Excel files into the file filter dropdown
 */
async function loadFilesDropdown() {
  try {
    const res = await window.api.get("/api/imports", { per_page: 100 });
    const selectEl = document.getElementById("call-file-filter");
    if (!selectEl) return;

    let opts = '<option value="">📁 All Excel Files</option>';
    (res.items || []).forEach(f => {
      opts += `<option value="${f.id}">📄 ${f.original_filename}</option>`;
    });
    selectEl.innerHTML = opts;
  } catch (err) {
    console.error("Failed to load files list:", err);
  }
}

/**
 * Load Call History & Work Activity Records
 */
async function loadCallHistory() {
  const tbody = document.getElementById("calls-tbody");
  tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; padding:32px;">Loading calls & completed work...</td></tr>`;

  const params = {
    page: curCallPage,
    per_page: callLimit,
    search: callSearch,
    outcome: callOutcome
  };

  if (callDatePreset && callDatePreset !== "custom") {
    params.date_preset = callDatePreset;
  } else if (callDatePreset === "custom") {
    if (callDateFrom) params.date_from = callDateFrom;
    if (callDateTo) params.date_to = callDateTo;
  }

  if (callFileId) {
    params.import_file_id = parseInt(callFileId);
  }

  try {
    const res = await window.api.get("/api/calls", params);

    // Update KPIs
    if (res.stats) {
      document.getElementById("kpi-call-total").textContent = (res.stats.total || 0).toLocaleString();
      document.getElementById("kpi-call-converted").textContent = (res.stats.converted || 0).toLocaleString();
      document.getElementById("kpi-call-interested").textContent = (res.stats.interested || 0).toLocaleString();
      document.getElementById("kpi-call-scheduled").textContent = (res.stats.scheduled || 0).toLocaleString();
    }

    const total = res.total;
    const start = total === 0 ? 0 : (curCallPage - 1) * callLimit + 1;
    const end = Math.min(curCallPage * callLimit, total);
    document.getElementById("call-page-info").textContent = `Showing ${start} to ${end} of ${total.toLocaleString()} records`;
    document.getElementById("call-page-txt").textContent = `Page ${curCallPage} of ${res.total_pages || 1}`;

    document.getElementById("call-prev-btn").disabled = curCallPage <= 1;
    document.getElementById("call-next-btn").disabled = curCallPage >= res.total_pages;

    if (!res.items || res.items.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="10">
            <div class="empty-state">
              <div class="empty-state-title">No Work or Call Records Found</div>
              <div class="empty-state-text">No records match the selected work filters or date range.</div>
            </div>
          </td>
        </tr>`;
      return;
    }

    tbody.innerHTML = res.items.map(c => {
      const phoneLink = c.customer_mobile 
        ? `<a href="tel:${c.customer_mobile}" style="font-family:var(--font-mono); font-weight:500;">${c.customer_mobile}</a>`
        : '<span style="color:#94a3b8;">-</span>';

      const fileBadge = c.source_file && c.source_file !== "Direct"
        ? `<span class="badge" style="background:#e0f2fe; color:#0369a1; font-size:11px;" title="${c.source_file}">📄 ${c.source_file}</span>`
        : `<span class="badge badge-neutral" style="font-size:11px;">Manual</span>`;

      return `
        <tr>
          <td style="font-weight:600;">
            <a href="/customer-details.html?id=${c.customer_id}">${c.customer_name}</a>
          </td>
          <td>${phoneLink}</td>
          <td style="color:var(--text-secondary); max-width:120px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${c.customer_company || ''}">
            ${c.customer_company || '-'}
          </td>
          <td style="font-weight:500; font-size:12.5px;">${formatDateTime(c.call_datetime)}</td>
          <td>${getOutcomeBadge(c.outcome)}</td>
          <td style="font-size:12.5px; color:var(--text-secondary); max-width:220px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${c.notes || ''}">
            ${c.notes || '-'}
          </td>
          <td style="font-size:12.5px; color:var(--primary); font-weight:500;">${c.next_action || '-'}</td>
          <td>${fileBadge}</td>
          <td style="font-size:12px; color:var(--text-muted);">${c.created_by_name || 'Admin'}</td>
          <td style="text-align:right;">
            <a href="/customer-details.html?id=${c.customer_id}" class="btn btn-secondary btn-sm">Profile &rarr;</a>
          </td>
        </tr>
      `;
    }).join("");

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; color:var(--danger-text); padding:24px;">Failed to load calls: ${err.message}</td></tr>`;
  }
}

/**
 * Build URL parameters object for exports
 */
function getExportParams() {
  const params = {};
  if (callSearch) params.search = callSearch;
  if (callOutcome) params.outcome = callOutcome;
  if (callDatePreset && callDatePreset !== "custom") {
    params.date_preset = callDatePreset;
  } else if (callDatePreset === "custom") {
    if (callDateFrom) params.date_from = callDateFrom;
    if (callDateTo) params.date_to = callDateTo;
  }
  if (callFileId) params.import_file_id = callFileId;
  return params;
}

document.addEventListener("DOMContentLoaded", () => {
  loadFilesDropdown();
  loadCallHistory();

  // Search input debounce
  const searchInput = document.getElementById("call-search");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        callSearch = e.target.value.trim();
        curCallPage = 1;
        loadCallHistory();
      }, 350);
    });
  }

  // Quick Outcome Filter Pills
  const outcomeBtns = document.querySelectorAll(".outcome-tab-btn");
  outcomeBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      outcomeBtns.forEach(b => {
        b.style.borderColor = '#cbd5e1';
        b.style.background = '#fff';
        b.style.color = '#334155';
      });
      btn.style.borderColor = '#2563eb';
      btn.style.background = '#2563eb';
      btn.style.color = '#fff';

      callOutcome = btn.dataset.outcome || "";
      document.getElementById("call-outcome-filter").value = callOutcome;
      curCallPage = 1;
      loadCallHistory();
    });
  });

  // Date Preset dropdown change
  const datePresetSelect = document.getElementById("call-date-preset");
  const customDateBox = document.getElementById("custom-date-container");
  if (datePresetSelect) {
    datePresetSelect.addEventListener("change", (e) => {
      callDatePreset = e.target.value;
      if (callDatePreset === "custom") {
        customDateBox.style.display = "inline-flex";
      } else {
        customDateBox.style.display = "none";
        curCallPage = 1;
        loadCallHistory();
      }
    });
  }

  // Filter & Reset buttons
  document.getElementById("call-apply-filter").onclick = () => {
    callOutcome = document.getElementById("call-outcome-filter").value;
    callFileId = document.getElementById("call-file-filter").value;
    callDatePreset = document.getElementById("call-date-preset").value;
    if (callDatePreset === "custom") {
      callDateFrom = document.getElementById("call-date-from").value;
      callDateTo = document.getElementById("call-date-to").value;
    }
    curCallPage = 1;
    loadCallHistory();
  };

  document.getElementById("call-reset-filter").onclick = () => {
    document.getElementById("call-search").value = "";
    document.getElementById("call-outcome-filter").value = "";
    document.getElementById("call-date-preset").value = "";
    document.getElementById("call-file-filter").value = "";
    document.getElementById("call-date-from").value = "";
    document.getElementById("call-date-to").value = "";
    customDateBox.style.display = "none";

    callSearch = "";
    callOutcome = "";
    callDatePreset = "";
    callDateFrom = "";
    callDateTo = "";
    callFileId = "";
    curCallPage = 1;

    // Reset pills
    outcomeBtns.forEach((b, idx) => {
      if (idx === 0) {
        b.style.borderColor = '#2563eb';
        b.style.background = '#2563eb';
        b.style.color = '#fff';
      } else {
        b.style.borderColor = '#cbd5e1';
        b.style.background = '#fff';
        b.style.color = '#334155';
      }
    });

    loadCallHistory();
  };

  // Pagination
  document.getElementById("call-prev-btn").onclick = () => {
    if (curCallPage > 1) { curCallPage--; loadCallHistory(); }
  };

  document.getElementById("call-next-btn").onclick = () => {
    curCallPage++; loadCallHistory();
  };

  // Export to Excel Button
  document.getElementById("export-calls-excel-btn").onclick = async () => {
    try {
      showToast("Preparing Excel report of completed work & calls...", "info");
      const blob = await window.api.get("/api/calls/export/excel", getExportParams());
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `completed_work_report_${new Date().toISOString().slice(0, 10)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      showToast("Excel report downloaded successfully!", "success");
    } catch (err) {
      showToast("Excel export failed: " + err.message, "danger");
    }
  };

  // Export to PDF Button
  document.getElementById("export-calls-pdf-btn").onclick = async () => {
    try {
      showToast("Generating PDF report of completed work & calls...", "info");
      const blob = await window.api.get("/api/calls/export/pdf", getExportParams());
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `completed_work_report_${new Date().toISOString().slice(0, 10)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      showToast("PDF report generated and downloaded successfully!", "success");
    } catch (err) {
      showToast("PDF export failed: " + err.message, "danger");
    }
  };
});
