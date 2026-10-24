/**
 * Customers Directory & File-wise Data Workspace Controller
 */

let currentPage = 1;
const perPage = 25;
let currentSearch = "";
let currentStatus = "";
let currentCity = "";
let currentFileId = "";
let searchDebounceTimer = null;
let uploadedFilesCache = [];

function formatDateTime(dtStr) {
  if (!dtStr) return "-";
  const dt = new Date(dtStr);
  return dt.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
}

function getStatusBadge(status) {
  switch (status) {
    case "Converted": return '<span class="badge badge-completed">Converted</span>';
    case "Interested": return '<span class="badge badge-scheduled">Interested</span>';
    case "Follow-up Scheduled": return '<span class="badge badge-pending">Scheduled</span>';
    case "Not Interested": return '<span class="badge badge-overdue">Not Interested</span>';
    default: return `<span class="badge badge-neutral">${status || 'New'}</span>`;
  }
}

/**
 * Load list of all uploaded Excel files for dropdown filter and quick tabs
 */
async function loadUploadedFiles() {
  try {
    const res = await window.api.get("/api/imports", { per_page: 100 });
    uploadedFilesCache = res.items || [];

    const selectEl = document.getElementById("filter-excel-file");
    const tabsContainer = document.getElementById("file-quick-tabs");

    if (selectEl) {
      let optionsHtml = '<option value="">📁 All Uploaded Files (Combined)</option>';
      uploadedFilesCache.forEach(f => {
        const isSel = String(f.id) === String(currentFileId);
        optionsHtml += `<option value="${f.id}" ${isSel ? 'selected' : ''}>📄 ${f.original_filename} (${f.imported_rows} rows)</option>`;
      });
      selectEl.innerHTML = optionsHtml;
    }

    if (tabsContainer) {
      let tabsHtml = `
        <button type="button" class="file-tab-btn ${!currentFileId ? 'active' : ''}" data-file-id="" onclick="filterByFile('')" style="border:1px solid ${!currentFileId ? '#2563eb' : '#cbd5e1'}; background:${!currentFileId ? '#2563eb' : '#fff'}; color:${!currentFileId ? '#fff' : '#334155'}; border-radius:20px; padding:5px 14px; font-size:12.5px; font-weight:600; cursor:pointer; white-space:nowrap; transition:all 0.2s;">
          All Customers (Combined)
        </button>
      `;

      uploadedFilesCache.forEach(f => {
        const isActive = String(f.id) === String(currentFileId);
        tabsHtml += `
          <button type="button" class="file-tab-btn ${isActive ? 'active' : ''}" data-file-id="${f.id}" onclick="filterByFile(${f.id})" style="border:1px solid ${isActive ? '#2563eb' : '#cbd5e1'}; background:${isActive ? '#2563eb' : '#fff'}; color:${isActive ? '#fff' : '#334155'}; border-radius:20px; padding:5px 14px; font-size:12.5px; font-weight:600; cursor:pointer; white-space:nowrap; transition:all 0.2s; display:inline-flex; align-items:center; gap:6px;">
            <span>📄 ${f.original_filename}</span>
            <span style="background:${isActive ? 'rgba(255,255,255,0.25)' : '#f1f5f9'}; color:${isActive ? '#fff' : '#475569'}; padding:1px 6px; border-radius:10px; font-size:11px;">${f.imported_rows}</span>
          </button>
        `;
      });

      tabsContainer.innerHTML = tabsHtml;
    }

    updateFileBanner();
  } catch (err) {
    console.error("Failed to load uploaded files list:", err);
  }
}

/**
 * Filter table by selected Excel file
 */
window.filterByFile = function(fileId) {
  currentFileId = fileId ? String(fileId) : "";
  currentPage = 1;

  // Sync select dropdown
  const selectEl = document.getElementById("filter-excel-file");
  if (selectEl) selectEl.value = currentFileId;

  // Sync pills styling
  const tabBtns = document.querySelectorAll(".file-tab-btn");
  tabBtns.forEach(btn => {
    const isThis = String(btn.dataset.fileId || "") === String(currentFileId);
    btn.style.borderColor = isThis ? '#2563eb' : '#cbd5e1';
    btn.style.background = isThis ? '#2563eb' : '#fff';
    btn.style.color = isThis ? '#fff' : '#334155';
    const countBadge = btn.querySelector("span:last-child");
    if (countBadge && btn.dataset.fileId) {
      countBadge.style.background = isThis ? 'rgba(255,255,255,0.25)' : '#f1f5f9';
      countBadge.style.color = isThis ? '#fff' : '#475569';
    }
  });

  // Update URL query string
  const url = new URL(window.location);
  if (currentFileId) {
    url.searchParams.set("file_id", currentFileId);
  } else {
    url.searchParams.delete("file_id");
    url.searchParams.delete("import_file_id");
  }
  window.history.replaceState({}, "", url);

  updateFileBanner();
  loadCustomers();
};

/**
 * Update the Top Banner showing which file is being viewed
 */
function updateFileBanner() {
  const banner = document.getElementById("active-file-banner");
  if (!banner) return;

  if (!currentFileId) {
    banner.style.display = "none";
    return;
  }

  const f = uploadedFilesCache.find(item => String(item.id) === String(currentFileId));
  if (f) {
    banner.style.display = "block";
    document.getElementById("active-file-title").textContent = f.original_filename;
    document.getElementById("active-file-subtitle").textContent = 
      `Uploaded: ${formatDateTime(f.uploaded_at)} | Total Rows: ${f.total_rows} | Successfully Imported: ${f.imported_rows} rows`;
    
    const stBadge = document.getElementById("active-file-status");
    if (stBadge) {
      stBadge.textContent = f.import_status || 'Completed';
      stBadge.className = f.import_status === 'Completed' ? 'badge badge-completed' : 'badge badge-pending';
    }
  } else {
    banner.style.display = "block";
    document.getElementById("active-file-title").textContent = `Excel File #${currentFileId}`;
    document.getElementById("active-file-subtitle").textContent = "Viewing records from this imported file.";
  }
}

/**
 * Fetch and render customers table
 */
async function loadCustomers() {
  const tbody = document.getElementById("customers-table-body");
  tbody.innerHTML = `<tr><td colspan="11" style="text-align:center; padding:32px;">Loading customers...</td></tr>`;

  const queryParams = {
    page: currentPage,
    per_page: perPage,
    search: currentSearch,
    status: currentStatus,
    city: currentCity
  };

  if (currentFileId) {
    queryParams.import_file_id = parseInt(currentFileId);
  }

  try {
    const res = await window.api.get("/api/customers", queryParams);

    // Pagination info
    const total = res.total;
    const start = total === 0 ? 0 : (currentPage - 1) * perPage + 1;
    const end = Math.min(currentPage * perPage, total);
    document.getElementById("pagination-info").textContent = `Showing ${start} to ${end} of ${total.toLocaleString()} records`;
    document.getElementById("current-page-display").textContent = `Page ${currentPage} of ${res.total_pages || 1}`;

    document.getElementById("prev-page-btn").disabled = currentPage <= 1;
    document.getElementById("next-page-btn").disabled = currentPage >= res.total_pages;

    if (!res.items || res.items.length === 0) {
      const emptyMsg = currentFileId 
        ? `No customers found for this file. Try clearing filters or search.` 
        : `No records match your search criteria or no Excel files have been imported yet.`;

      tbody.innerHTML = `
        <tr>
          <td colspan="11">
            <div class="empty-state">
              <div class="empty-state-title">No Records Found</div>
              <div class="empty-state-text">${emptyMsg}</div>
              <div style="display:flex; gap:10px; justify-content:center; margin-top:12px;">
                <button class="btn btn-primary btn-sm" onclick="openModal('addCustomerModal')">Add Customer Manually</button>
                ${currentFileId ? `<button class="btn btn-secondary btn-sm" onclick="filterByFile('')">Show All Files</button>` : ''}
              </div>
            </div>
          </td>
        </tr>`;
      return;
    }

    tbody.innerHTML = res.items.map(c => {
      const phoneLink = c.mobile 
        ? `<a href="tel:${c.mobile}" style="font-family:var(--font-mono); font-weight:500;">${c.mobile}</a>` 
        : '<span style="color:#94a3b8;">-</span>';

      const emailDisplay = c.email 
        ? `<span style="font-size:12px; color:var(--text-secondary); max-width:140px; display:inline-block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${c.email}">${c.email}</span>` 
        : '<span style="color:#94a3b8;">-</span>';

      const fileBadge = c.import_filename 
        ? `<span class="badge" style="background:#e0f2fe; color:#0369a1; font-size:11px; cursor:pointer; max-width:130px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; display:inline-block;" title="Click to view only ${c.import_filename}" onclick="filterByFile(${c.import_file_id || ''})">📄 ${c.import_filename}</span>`
        : `<span class="badge badge-neutral" style="font-size:11px;">Manual</span>`;

      const safeName = (c.name || '').replace(/'/g, "\\'");

      return `
        <tr>
          <td style="font-family:var(--font-mono); font-size:12px; color:var(--text-muted);">${c.customer_code || `#${c.id}`}</td>
          <td>
            <a href="/customer-details.html?id=${c.id}" style="font-weight:600; color:var(--text-primary);" title="Click to view complete timeline">
              ${c.name || 'Unnamed Customer'}
            </a>
          </td>
          <td>${phoneLink}</td>
          <td>${emailDisplay}</td>
          <td style="max-width:120px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${c.company || ''}">${c.company || '-'}</td>
          <td>${c.city || '-'}</td>
          <td>${getStatusBadge(c.status)}</td>
          <td>${fileBadge}</td>
          <td style="font-size:12px;">${c.next_followup_date ? formatDateTime(c.next_followup_date) : '<span style="color:#94a3b8;">None</span>'}</td>
          <td><span class="badge badge-neutral" style="font-size:11px;">${c.total_calls}</span></td>
          <td style="text-align:right;">
            <div style="display:inline-flex; gap:6px; flex-wrap:nowrap; align-items:center;">
              <button class="btn btn-primary btn-sm" style="padding:4px 9px;" onclick="openQuickCall(${c.id}, '${safeName}')" title="Log Call">
                Call
              </button>
              <a href="/customer-details.html?id=${c.id}" class="btn btn-secondary btn-sm" style="padding:4px 10px; font-weight:600;" title="View Profile & Edit">
                View
              </a>
              <button class="btn btn-danger btn-sm" style="padding:4px 7px;" onclick="deleteCustomerRecord(${c.id}, '${safeName}')" title="Delete Record">
                ✕
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join("");

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="11" style="text-align:center; color:var(--danger-text); padding:24px;">Failed to load customers: ${err.message}</td></tr>`;
  }
}

/**
 * Open Edit Customer Modal with preloaded details
 */
window.openEditCustomer = async function(id) {
  try {
    const cust = await window.api.get(`/api/customers/${id}`);
    if (!cust) return;

    document.getElementById("edit-cust-id").value = cust.id;
    document.getElementById("edit-name").value = cust.name || "";
    document.getElementById("edit-code").value = cust.customer_code || "";
    document.getElementById("edit-mobile").value = cust.mobile || "";
    document.getElementById("edit-altphone").value = cust.alternate_phone || "";
    document.getElementById("edit-email").value = cust.email || "";
    document.getElementById("edit-company").value = cust.company || "";
    document.getElementById("edit-city").value = cust.city || "";
    document.getElementById("edit-state").value = cust.state || "";
    document.getElementById("edit-address").value = cust.address || "";
    document.getElementById("edit-status").value = cust.status || "New";
    document.getElementById("edit-category").value = cust.category || "General";

    document.getElementById("edit-customer-subtitle").textContent = 
      `Customer ID: #${cust.id} ${cust.source_file ? '| From File: ' + cust.source_file.filename : ''}`;

    // Dynamic Excel custom fields
    const customGroup = document.getElementById("edit-custom-fields-group");
    const customContainer = document.getElementById("edit-custom-fields-container");
    const customFields = cust.custom_fields || {};
    const fieldKeys = Object.keys(customFields);

    if (fieldKeys.length > 0) {
      customGroup.style.display = "block";
      customContainer.innerHTML = fieldKeys.map(k => `
        <div class="form-group" style="margin-bottom:6px;">
          <label class="form-label" style="font-size:11.5px;">${k}</label>
          <input type="text" class="form-control edit-custom-field-input" data-custom-key="${k}" value="${customFields[k] !== null ? customFields[k] : ''}" style="font-size:12.5px; padding:6px 8px;">
        </div>
      `).join("");
    } else {
      customGroup.style.display = "none";
      customContainer.innerHTML = "";
    }

    openModal("editCustomerModal");
  } catch (err) {
    showToast("Failed to load customer details: " + err.message, "danger");
  }
};

/**
 * Delete a customer record
 */
window.deleteCustomerRecord = async function(id, name) {
  if (!confirm(`Are you sure you want to permanently delete "${name}"?`)) {
    return;
  }

  try {
    await window.api.delete(`/api/customers/${id}`);
    showToast(`Customer "${name}" deleted successfully.`, "success");
    loadCustomers();
  } catch (err) {
    showToast("Failed to delete customer: " + err.message, "danger");
  }
};

/**
 * Open Quick Call Modal
 */
window.openQuickCall = function(id, name) {
  document.getElementById("call-customer-id").value = id;
  document.getElementById("call-customer-name-display").textContent = `Logging call for: ${name}`;
  document.getElementById("call-notes").value = "";
  document.getElementById("call-next-action").value = "";
  document.getElementById("call-next-date").value = "";
  openModal("logCallModal");
};

/**
 * Setup Event Listeners
 */
document.addEventListener("DOMContentLoaded", () => {
  // Check URL parameters for file_id or import_file_id
  const urlParams = new URLSearchParams(window.location.search);
  const fid = urlParams.get("file_id") || urlParams.get("import_file_id");
  if (fid) {
    currentFileId = String(fid);
  }

  // Load uploaded files list and initial customers
  loadUploadedFiles();
  loadCustomers();

  // Excel File dropdown change
  const fileSelect = document.getElementById("filter-excel-file");
  if (fileSelect) {
    fileSelect.addEventListener("change", (e) => {
      filterByFile(e.target.value);
    });
  }

  // Clear file filter button
  const clearFileBtn = document.getElementById("clear-file-filter-btn");
  if (clearFileBtn) {
    clearFileBtn.addEventListener("click", () => {
      filterByFile("");
    });
  }

  // Export specific file Excel button
  const exportFileBtn = document.getElementById("export-this-file-btn");
  if (exportFileBtn) {
    exportFileBtn.addEventListener("click", async () => {
      try {
        showToast("Preparing Excel export for this file...", "info");
        const blob = await window.api.get("/api/customers/export", {
          import_file_id: currentFileId,
          search: currentSearch,
          status: currentStatus,
          city: currentCity
        });

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `file_${currentFileId}_records_${new Date().toISOString().slice(0, 10)}.xlsx`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast("File Excel data exported successfully!", "success");
      } catch (err) {
        showToast("Export failed: " + err.message, "danger");
      }
    });
  }

  // Export specific file PDF button
  const exportFilePdfBtn = document.getElementById("export-this-file-pdf-btn");
  if (exportFilePdfBtn) {
    exportFilePdfBtn.addEventListener("click", async () => {
      try {
        showToast("Generating PDF report for this file...", "info");
        const blob = await window.api.get("/api/customers/export/pdf", {
          import_file_id: currentFileId,
          search: currentSearch,
          status: currentStatus,
          city: currentCity
        });

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `file_${currentFileId}_report_${new Date().toISOString().slice(0, 10)}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast("File PDF report downloaded successfully!", "success");
      } catch (err) {
        showToast("PDF Export failed: " + err.message, "danger");
      }
    });
  }

  // Search Input Debounce
  const searchInput = document.getElementById("customer-search-input");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      clearTimeout(searchDebounceTimer);
      searchDebounceTimer = setTimeout(() => {
        currentSearch = e.target.value.trim();
        currentPage = 1;
        loadCustomers();
      }, 350);
    });
  }

  // Filter apply & reset
  document.getElementById("apply-filter-btn").addEventListener("click", () => {
    currentStatus = document.getElementById("filter-status").value;
    currentCity = document.getElementById("filter-city").value.trim();
    currentPage = 1;
    loadCustomers();
  });

  document.getElementById("reset-filter-btn").addEventListener("click", () => {
    document.getElementById("filter-status").value = "";
    document.getElementById("filter-city").value = "";
    document.getElementById("customer-search-input").value = "";
    currentStatus = "";
    currentCity = "";
    currentSearch = "";
    currentPage = 1;
    loadCustomers();
  });

  // Pagination Handlers
  document.getElementById("prev-page-btn").addEventListener("click", () => {
    if (currentPage > 1) {
      currentPage--;
      loadCustomers();
    }
  });

  document.getElementById("next-page-btn").addEventListener("click", () => {
    currentPage++;
    loadCustomers();
  });

  // Export All to Excel Trigger
  document.getElementById("export-excel-btn").addEventListener("click", async () => {
    try {
      showToast("Preparing Excel export...", "info");
      const blob = await window.api.get("/api/customers/export", {
        search: currentSearch,
        status: currentStatus,
        city: currentCity,
        import_file_id: currentFileId || undefined
      });

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `customers_export_${new Date().toISOString().slice(0, 10)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      showToast("Customers exported to Excel successfully!", "success");
    } catch (err) {
      showToast("Export failed: " + err.message, "danger");
    }
  });

  // Export to PDF Report Trigger
  const exportPdfBtn = document.getElementById("export-pdf-btn");
  if (exportPdfBtn) {
    exportPdfBtn.addEventListener("click", async () => {
      try {
        showToast("Generating PDF customer report...", "info");
        const blob = await window.api.get("/api/customers/export/pdf", {
          search: currentSearch,
          status: currentStatus,
          city: currentCity,
          import_file_id: currentFileId || undefined
        });

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `customers_report_${new Date().toISOString().slice(0, 10)}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast("PDF report generated and downloaded successfully!", "success");
      } catch (err) {
        showToast("PDF Export failed: " + err.message, "danger");
      }
    });
  }

  // Edit Customer Form Submit
  const editCustomerForm = document.getElementById("editCustomerForm");
  if (editCustomerForm) {
    editCustomerForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const customerId = document.getElementById("edit-cust-id").value;
      const saveBtn = document.getElementById("save-edit-btn");
      saveBtn.disabled = true;
      saveBtn.textContent = "Saving...";

      try {
        const payload = {
          name: document.getElementById("edit-name").value.trim(),
          customer_code: document.getElementById("edit-code").value.trim() || null,
          mobile: document.getElementById("edit-mobile").value.trim(),
          alternate_phone: document.getElementById("edit-altphone").value.trim() || null,
          email: document.getElementById("edit-email").value.trim() || null,
          company: document.getElementById("edit-company").value.trim() || null,
          city: document.getElementById("edit-city").value.trim() || null,
          state: document.getElementById("edit-state").value.trim() || null,
          address: document.getElementById("edit-address").value.trim() || null,
          status: document.getElementById("edit-status").value,
          category: document.getElementById("edit-category").value.trim() || "General"
        };

        // Custom fields values
        const customInputs = document.querySelectorAll(".edit-custom-field-input");
        if (customInputs.length > 0) {
          const cf = {};
          customInputs.forEach(inp => {
            cf[inp.dataset.customKey] = inp.value;
          });
          payload.custom_fields = cf;
        }

        await window.api.put(`/api/customers/${customerId}`, payload);
        showToast("Customer details updated successfully!", "success");
        closeModal("editCustomerModal");
        loadCustomers();
      } catch (err) {
        showToast(err.message || "Failed to update customer", "danger");
      } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = "Save Changes";
      }
    });
  }

  // Add Customer Form Submit
  const addCustomerForm = document.getElementById("addCustomerForm");
  if (addCustomerForm) {
    addCustomerForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await window.api.post("/api/customers", {
          name: document.getElementById("add-name").value.trim(),
          customer_code: document.getElementById("add-code").value.trim() || null,
          mobile: document.getElementById("add-mobile").value.trim(),
          email: document.getElementById("add-email").value.trim() || null,
          company: document.getElementById("add-company").value.trim() || null,
          city: document.getElementById("add-city").value.trim() || null,
          address: document.getElementById("add-address").value.trim() || null,
          source: currentFileId ? `File #${currentFileId}` : "Manual Entry"
        });

        showToast("Customer created successfully!", "success");
        addCustomerForm.reset();
        closeModal("addCustomerModal");
        loadCustomers();
      } catch (err) {
        showToast(err.message || "Failed to create customer", "danger");
      }
    });
  }

  // Quick Log Call Form Submit
  const logCallForm = document.getElementById("logCallForm");
  if (logCallForm) {
    logCallForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const customerId = document.getElementById("call-customer-id").value;
      const outcome = document.getElementById("call-outcome").value;
      const notes = document.getElementById("call-notes").value;
      const nextAction = document.getElementById("call-next-action").value;
      const nextDate = document.getElementById("call-next-date").value;

      try {
        await window.api.post(`/api/customers/${customerId}/calls`, {
          outcome,
          notes,
          next_action: nextAction,
          schedule_next_followup: nextDate ? new Date(nextDate).toISOString() : null
        });

        showToast("Call logged successfully!", "success");
        closeModal("logCallModal");
        loadCustomers();
      } catch (err) {
        showToast(err.message || "Failed to log call", "danger");
      }
    });
  }
});
