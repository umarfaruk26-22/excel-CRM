/**
 * Excel Import Wizard Controller
 */

let currentUploadData = null;
let currentStep = 1;

const CRM_FIELDS = [
  { key: "name", label: "Customer Name *", required: true },
  { key: "mobile", label: "Mobile Number", required: false },
  { key: "alternate_phone", label: "Alternate Phone", required: false },
  { key: "email", label: "Email Address", required: false },
  { key: "company", label: "Company / Firm", required: false },
  { key: "customer_code", label: "Customer Code / ID", required: false },
  { key: "city", label: "City", required: false },
  { key: "state", label: "State", required: false },
  { key: "country", label: "Country", required: false },
  { key: "address", label: "Street / Address", required: false },
  { key: "category", label: "Customer Category", required: false },
  { key: "source", label: "Lead Source", required: false },
  { key: "status", label: "Initial Status", required: false }
];

window.goToStep = function(stepNum) {
  currentStep = stepNum;

  // Update nav indicators
  for (let i = 1; i <= 4; i++) {
    const nav = document.getElementById(`step-nav-${i}`);
    const card = document.getElementById(`step-${i}-card`);
    if (nav) {
      nav.classList.remove("active", "completed");
      if (i === stepNum) nav.classList.add("active");
      else if (i < stepNum) nav.classList.add("completed");
    }
    if (card) {
      card.style.display = i === stepNum ? "block" : "none";
    }
  }
};

window.resetImportWizard = function() {
  currentUploadData = null;
  document.getElementById("excel-file-input").value = "";
  document.getElementById("upload-progress-container").style.display = "none";
  goToStep(1);
};

// Handle file upload
async function handleFileUpload(file) {
  if (!file) return;

  const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
  if (ext !== ".xlsx" && ext !== ".xls") {
    showToast("Invalid format. Please select an .xlsx or .xls file.", "danger");
    return;
  }

  const progressContainer = document.getElementById("upload-progress-container");
  const filenameEl = document.getElementById("upload-filename");
  const progressBar = document.getElementById("upload-progress-bar");

  progressContainer.style.display = "block";
  filenameEl.textContent = `Uploading ${file.name}...`;
  progressBar.style.width = "70%";

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await window.api.upload("/api/imports/upload", formData);
    progressBar.style.width = "100%";
    currentUploadData = res;

    showToast("File uploaded and analyzed successfully!", "success");

    // Populate Sheet Select
    const sheetSelect = document.getElementById("sheet-select");
    sheetSelect.innerHTML = res.sheets.map(s => `<option value="${s}" ${s === res.selected_sheet ? 'selected' : ''}>${s}</option>`).join("");

    sheetSelect.onchange = async () => {
      try {
        const previewRes = await window.api.get(`/api/imports/${res.file_id}/preview`, { sheet_name: sheetSelect.value });
        currentUploadData.headers = previewRes.headers;
        currentUploadData.preview_rows = previewRes.preview_rows;
        currentUploadData.suggested_mapping = previewRes.suggested_mapping;
        currentUploadData.selected_sheet = sheetSelect.value;
        renderPreviewTable();
        buildMappingControls();
      } catch (err) {
        showToast(err.message || "Failed to switch sheet", "danger");
      }
    };

    renderPreviewTable();
    buildMappingControls();
    goToStep(2);
  } catch (err) {
    progressContainer.style.display = "none";
    showToast(err.message || "File upload failed.", "danger");
  }
}

// Render Preview Table
function renderPreviewTable() {
  if (!currentUploadData) return;
  const thead = document.getElementById("preview-thead");
  const tbody = document.getElementById("preview-tbody");

  thead.innerHTML = `<tr>${currentUploadData.headers.map(h => `<th>${h}</th>`).join("")}</tr>`;

  if (currentUploadData.preview_rows.length === 0) {
    tbody.innerHTML = `<tr><td colspan="${currentUploadData.headers.length}" style="text-align:center;">No data rows found in this sheet.</td></tr>`;
    return;
  }

  tbody.innerHTML = currentUploadData.preview_rows.map(row => {
    return `<tr>${currentUploadData.headers.map(h => `<td>${row[h] !== null && row[h] !== undefined ? row[h] : '<span style="color:#cbd5e1;">null</span>'}</td>`).join("")}</tr>`;
  }).join("");
}

// Build Mapping Dropdowns
function buildMappingControls() {
  if (!currentUploadData) return;

  const container = document.getElementById("mapping-fields-container");
  const customBox = document.getElementById("custom-fields-checkboxes");
  const headers = currentUploadData.headers;
  const suggestions = currentUploadData.suggested_mapping || {};

  container.innerHTML = CRM_FIELDS.map(field => {
    const suggestedHeader = suggestions[field.key] || "";
    const options = [
      `<option value="">-- Ignore / Not in file --</option>`,
      ...headers.map(h => `<option value="${h}" ${h === suggestedHeader ? 'selected' : ''}>${h}</option>`)
    ].join("");

    return `
      <div class="form-group" style="margin-bottom:12px;">
        <label class="form-label" style="font-size:12.5px;">${field.label}</label>
        <select class="form-select mapping-select" data-crm-field="${field.key}" style="padding:7px 10px; font-size:13px;">
          ${options}
        </select>
      </div>
    `;
  }).join("");

  // Custom fields checkboxes (all headers)
  customBox.innerHTML = headers.map(h => {
    return `
      <label style="display:flex; align-items:center; gap:6px; font-size:12px; cursor:pointer;">
        <input type="checkbox" class="custom-field-check" value="${h}">
        <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${h}">${h}</span>
      </label>
    `;
  }).join("");
}

// Execute Import Action
window.executeImport = async function() {
  if (!currentUploadData) return;

  const mappingSelects = document.querySelectorAll(".mapping-select");
  const mapping = {};
  mappingSelects.forEach(sel => {
    const field = sel.dataset.crmField;
    const val = sel.value;
    if (val) {
      mapping[field] = val;
    }
  });

  if (!mapping["name"]) {
    showToast("Please map 'Customer Name' before proceeding with import.", "warning");
    return;
  }

  const customFieldChecks = document.querySelectorAll(".custom-field-check:checked");
  const customCols = Array.from(customFieldChecks).map(c => c.value);

  const duplicateRadio = document.querySelector("input[name='duplicate_handling']:checked");
  const duplicateHandling = duplicateRadio ? duplicateRadio.value : "skip";

  const sheetSelect = document.getElementById("sheet-select");
  const sheetName = sheetSelect.value;

  const commitBtn = document.getElementById("commit-import-btn");
  commitBtn.disabled = true;
  commitBtn.textContent = "Processing batch import into MySQL...";

  try {
    const res = await window.api.post("/api/imports/confirm", {
      file_id: currentUploadData.file_id,
      sheet_name: sheetName,
      column_mapping: mapping,
      custom_field_columns: customCols,
      duplicate_handling: duplicateHandling
    });

    // Populate Step 4 Summary & File Callout
    document.getElementById("summary-total-rows").textContent = res.total_rows.toLocaleString();
    document.getElementById("summary-imported-rows").textContent = res.imported_rows.toLocaleString();
    document.getElementById("summary-updated-rows").textContent = res.updated_rows.toLocaleString();
    document.getElementById("summary-duplicate-rows").textContent = res.duplicate_rows.toLocaleString();
    document.getElementById("summary-rejected-rows").textContent = res.rejected_rows.toLocaleString();

    const filename = res.original_filename || "Uploaded File";
    const fileId = res.import_id;
    const fileUrl = `/customers.html?file_id=${fileId}`;

    const filenameDisplay = document.getElementById("imported-file-name-display");
    if (filenameDisplay) filenameDisplay.textContent = filename;

    const viewBtn = document.getElementById("view-file-data-btn");
    if (viewBtn) viewBtn.href = fileUrl;

    const viewBtn2 = document.getElementById("view-file-data-btn-2");
    if (viewBtn2) viewBtn2.href = fileUrl;

    const statusBadge = document.getElementById("import-status-badge");
    statusBadge.textContent = res.import_status;
    if (res.rejected_rows > 0) {
      statusBadge.className = "badge badge-pending";
      const errSec = document.getElementById("error-report-section");
      errSec.style.display = "block";
      document.getElementById("download-error-btn").href = res.error_report_url || `${window.API_BASE || ''}/api/imports/${res.import_id}/errors/download`;
    } else {
      statusBadge.className = "badge badge-completed";
      document.getElementById("error-report-section").style.display = "none";
    }

    showToast("File data imported successfully! You can now view and edit this file.", "success");
    goToStep(4);
  } catch (err) {
    showToast(err.message || "Failed to commit import", "danger");
  } finally {
    commitBtn.disabled = false;
    commitBtn.textContent = "Start Transactional Import →";
  }
};

// Event Listeners for Drag and Drop
document.addEventListener("DOMContentLoaded", () => {
  const dropzone = document.getElementById("file-dropzone");
  const fileInput = document.getElementById("excel-file-input");

  if (dropzone && fileInput) {
    dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzone.classList.add("drag-over");
    });

    dropzone.addEventListener("dragleave", () => {
      dropzone.classList.remove("drag-over");
    });

    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzone.classList.remove("drag-over");
      if (e.dataTransfer.files.length > 0) {
        handleFileUpload(e.dataTransfer.files[0]);
      }
    });

    fileInput.addEventListener("change", () => {
      if (fileInput.files.length > 0) {
        handleFileUpload(fileInput.files[0]);
      }
    });
  }
});
