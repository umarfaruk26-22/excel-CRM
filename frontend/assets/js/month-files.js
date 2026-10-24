/**
 * Month-wise Files & Record Explorer Controller
 */

function formatDate(dtStr) {
  if (!dtStr) return "-";
  const dt = new Date(dtStr);
  return dt.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
}

let currentDrilldownFileId = null;

async function loadFiles() {
  const yearVal = document.getElementById("filter-year").value;
  const monthVal = document.getElementById("filter-month").value;

  const params = {};
  if (yearVal) params.year = parseInt(yearVal);
  if (monthVal) params.month = parseInt(monthVal);

  const tbody = document.getElementById("files-table-body");
  tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; padding:32px;">Loading files...</td></tr>`;

  try {
    const res = await window.api.get("/api/imports", params);

    if (!res.items || res.items.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="10">
            <div class="empty-state">
              <div class="empty-state-title">No Excel Files Found</div>
              <div class="empty-state-text">No files match the selected month/year filter.</div>
              <a href="/imports.html" class="btn btn-primary btn-sm">Import Excel Now</a>
            </div>
          </td>
        </tr>`;
      return;
    }

    tbody.innerHTML = res.items.map(f => {
      const isCompleted = f.import_status === 'Completed';
      const statusBadge = isCompleted 
        ? '<span class="badge badge-completed">Completed</span>'
        : '<span class="badge badge-pending">Partial / Errors</span>';

      const safeName = (f.original_filename || '').replace(/'/g, "\\'");

      return `
        <tr>
          <td style="font-weight:600; color:var(--text-primary);">
            <div style="display:flex; align-items:center; gap:8px;">
              <span style="font-size:16px;">📄</span>
              <span>${f.original_filename}</span>
            </div>
          </td>
          <td>${formatDate(f.uploaded_at)}</td>
          <td>${f.import_month}/${f.import_year}</td>
          <td>${f.worksheet_name || 'Sheet1'}</td>
          <td style="font-weight:600;">${f.total_rows.toLocaleString()}</td>
          <td style="color:var(--success); font-weight:600;">${f.imported_rows.toLocaleString()}</td>
          <td style="color:var(--primary); font-weight:600;">${f.updated_rows.toLocaleString()}</td>
          <td style="color:var(--warning-text);">${f.duplicate_rows.toLocaleString()}</td>
          <td>${statusBadge}</td>
          <td style="text-align:right; vertical-align:middle;">
            <div style="display:inline-flex; flex-direction:column; gap:5px; width:215px; box-sizing:border-box; margin-left:auto;">
              <!-- Line 1: Primary Action (Hero Button) -->
              <a href="/customers.html?file_id=${f.id}" class="btn btn-primary btn-sm" style="font-weight:600; padding:5px 10px; font-size:12px; display:flex; align-items:center; justify-content:center; gap:6px; width:100%; box-sizing:border-box; text-decoration:none;" title="Open and edit records for this file">
                <span>📂</span> Open & Edit Data
              </a>

              <!-- Line 2: Balanced Tools Toolbar -->
              <div style="display:flex; gap:4px; width:100%; align-items:center; box-sizing:border-box;">
                <button class="btn btn-secondary btn-sm" style="padding:4px 6px; font-size:11.5px; flex:1; text-align:center; white-space:nowrap;" onclick="inspectRecords(${f.id}, '${safeName}')" title="Quick Preview">
                  Preview
                </button>
                <a href="${window.API_BASE || ''}/api/imports/${f.id}/download" class="btn btn-secondary btn-sm" style="padding:4px 6px; font-size:11.5px; flex:1; text-align:center; white-space:nowrap; color:var(--text-secondary);" title="Download Original Excel">
                  Excel
                </a>
                ${f.has_error_report ? `
                  <a href="${window.API_BASE || ''}/api/imports/${f.id}/errors/download" class="btn btn-secondary btn-sm" style="padding:4px 6px; font-size:11.5px; flex:1; text-align:center; white-space:nowrap; color:#b91c1c; border-color:#fca5a5; background:#fff1f2;" title="Download Error Report">
                    Errors
                  </a>
                ` : ''}
                <button class="btn btn-secondary btn-sm" style="padding:4px 8px; font-size:12px; color:#dc2626; border-color:#fecaca;" onclick="deleteFileRecord(${f.id}, '${safeName}')" title="Delete File and its records">
                  🗑️
                </button>
              </div>
            </div>
          </td>
        </tr>
      `;
    }).join("");

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; color:var(--danger-text); padding:24px;">Failed to load files: ${err.message}</td></tr>`;
  }
}

/**
 * Delete an entire imported file
 */
window.deleteFileRecord = async function(importId, filename) {
  if (!confirm(`Are you sure you want to delete "${filename}" and its customer records? This action cannot be undone.`)) {
    return;
  }

  try {
    await window.api.delete(`/api/imports/${importId}`);
    showToast(`File "${filename}" deleted successfully.`, "success");
    loadFiles();
    closeDrilldown();
  } catch (err) {
    showToast("Failed to delete file: " + err.message, "danger");
  }
};

/**
 * Preview / Inspect records of a file in the drilldown section
 */
window.inspectRecords = async function(importId, filename) {
  currentDrilldownFileId = importId;
  const card = document.getElementById("drilldown-card");
  const title = document.getElementById("drilldown-title");
  const tbody = document.getElementById("drilldown-tbody");
  const fullEditorBtn = document.getElementById("drilldown-full-editor-btn");

  card.style.display = "block";
  title.textContent = `Records Preview: ${filename}`;
  if (fullEditorBtn) {
    fullEditorBtn.href = `/customers.html?file_id=${importId}`;
  }
  tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:24px;">Loading tracked row records...</td></tr>`;

  card.scrollIntoView({ behavior: 'smooth' });

  try {
    const res = await window.api.get(`/api/imports/${importId}/records`, { per_page: 100 });
    if (!res.items || res.items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:24px; color:var(--text-muted);">No records found for this import.</td></tr>`;
      return;
    }

    tbody.innerHTML = res.items.map(r => {
      let stBadge = '<span class="badge badge-completed">Imported</span>';
      if (r.row_status === 'Updated') stBadge = '<span class="badge badge-scheduled">Updated</span>';
      else if (r.row_status === 'Duplicate_Skipped') stBadge = '<span class="badge badge-pending">Duplicate Skipped</span>';
      else if (r.row_status === 'Rejected') stBadge = '<span class="badge badge-overdue">Rejected</span>';

      return `
        <tr>
          <td style="font-family:var(--font-mono); font-size:12px;">Row ${r.source_row_number}</td>
          <td style="font-weight:600;">${r.customer_name || 'N/A'}</td>
          <td style="font-family:var(--font-mono); font-size:12.5px;">${r.customer_mobile || '-'}</td>
          <td>${stBadge}</td>
          <td style="font-size:12px; color:${r.error_message ? 'var(--danger-text)' : 'var(--text-muted)'};">${r.error_message || '-'}</td>
          <td style="text-align:right;">
            <div style="display:inline-flex; gap:6px;">
              ${r.customer_id ? `
                <a href="/customer-details.html?id=${r.customer_id}" class="btn btn-secondary btn-sm" style="font-weight:600;" title="View & Edit Customer Details">
                  View &rarr;
                </a>
              ` : '-'}
            </div>
          </td>
        </tr>
      `;
    }).join("");

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--danger-text); padding:20px;">Failed to load records: ${err.message}</td></tr>`;
  }
};

window.closeDrilldown = function() {
  document.getElementById("drilldown-card").style.display = "none";
  currentDrilldownFileId = null;
};

/**
 * Open Customer Edit Modal
 */
window.openEditModal = async function(id) {
  try {
    const cust = await window.api.get(`/api/customers/${id}`);
    if (!cust) return;

    document.getElementById("edit-cust-id").value = cust.id;
    document.getElementById("edit-name").value = cust.name || "";
    document.getElementById("edit-code").value = cust.customer_code || "";
    document.getElementById("edit-mobile").value = cust.mobile || "";
    document.getElementById("edit-email").value = cust.email || "";
    document.getElementById("edit-company").value = cust.company || "";
    document.getElementById("edit-city").value = cust.city || "";
    document.getElementById("edit-status").value = cust.status || "New";
    document.getElementById("edit-category").value = cust.category || "General";
    document.getElementById("edit-address").value = cust.address || "";

    openModal("editCustomerModal");
  } catch (err) {
    showToast("Failed to load customer details: " + err.message, "danger");
  }
};

document.addEventListener("DOMContentLoaded", () => {
  loadFiles();
  document.getElementById("apply-filter").onclick = () => loadFiles();

  const p = new URLSearchParams(window.location.search);
  const fileId = p.get("file_id");
  if (fileId) {
    inspectRecords(fileId, `File #${fileId}`);
  }

  // Handle Edit Customer submit
  const editCustomerForm = document.getElementById("editCustomerForm");
  if (editCustomerForm) {
    editCustomerForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const customerId = document.getElementById("edit-cust-id").value;
      const saveBtn = document.getElementById("save-edit-btn");
      saveBtn.disabled = true;
      saveBtn.textContent = "Saving...";

      try {
        await window.api.put(`/api/customers/${customerId}`, {
          name: document.getElementById("edit-name").value.trim(),
          customer_code: document.getElementById("edit-code").value.trim() || null,
          mobile: document.getElementById("edit-mobile").value.trim(),
          email: document.getElementById("edit-email").value.trim() || null,
          company: document.getElementById("edit-company").value.trim() || null,
          city: document.getElementById("edit-city").value.trim() || null,
          status: document.getElementById("edit-status").value,
          category: document.getElementById("edit-category").value.trim() || "General",
          address: document.getElementById("edit-address").value.trim() || null
        });

        showToast("Customer details updated successfully!", "success");
        closeModal("editCustomerModal");
        if (currentDrilldownFileId) {
          inspectRecords(currentDrilldownFileId, `File #${currentDrilldownFileId}`);
        }
      } catch (err) {
        showToast(err.message || "Failed to update customer", "danger");
      } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = "Save Changes";
      }
    });
  }
});
