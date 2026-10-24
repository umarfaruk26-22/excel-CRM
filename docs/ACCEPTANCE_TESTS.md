# Customer Follow-up CRM — Acceptance Testing Checklist

This document provides both the automated test results and a step-by-step manual acceptance checklist to verify all requirements of the Master Prompt.

---

## 1. Automated Test Results Summary

Automated tests are located in `backend/tests/test_crm_flow.py` and run via:
```powershell
.\.venv\Scripts\python.exe backend\tests\test_crm_flow.py
```

| # | Test Case Description | Verified Behavior | Status |
| :-: | :--- | :--- | :-: |
| **1** | Admin Authentication & Passwords | Rejects bad passwords with 401; verifies bcrypt hash | **PASSED** |
| **2** | Session / JWT Issuance | Returns signed token & sets HTTP-only cookie | **PASSED** |
| **3** | Excel File Upload & Validation | Accepts `.xlsx` & `.xls`; rejects unsupported extensions | **PASSED** |
| **4** | Sheet Inspection & Preview | Returns sheets list, headers, top rows without formula evaluation | **PASSED** |
| **5** | Column Auto-Mapping & Manual Select | Correctly auto-guesses Name, Mobile, Email, Company, City | **PASSED** |
| **6** | Custom Fields Handling | Extra columns (`Product Interest`, `GST Number`) stored in JSON | **PASSED** |
| **7** | Transactional Batch Import | Processes batch in transaction; rolls back on catastrophic error | **PASSED** |
| **8** | Rejected Rows & Error Report | Row with blank name rejected; Excel error report created with row # | **PASSED** |
| **9** | Duplicate Detection (Skip mode) | Recognizes 10 duplicates by normalized phone/email and skips them | **PASSED** |
| **10**| Customer Profile & Traceability | Full details, JSON fields, and source file row link displayed | **PASSED** |
| **11**| Follow-up Engine (+1 Month Math) | Calculates calendar date arithmetic correctly | **PASSED** |
| **12**| Call History Logging | Saves call, updates customer status & last contacted time | **PASSED** |
| **13**| Overdue & Today Filtering | Evaluated directly from MySQL in Asia/Kolkata timezone | **PASSED** |
| **14**| Real-time Dashboard Calculation | Accurate counters without double-counting | **PASSED** |
| **15**| Excel Customer Export | Generates sanitized `.xlsx` preventing formula injection | **PASSED** |

---

## 2. Manual Verification Checklist

Follow this checklist in your web browser at `http://127.0.0.1:8000`:

### A. Authentication & Access Control
- [ ] Open `http://127.0.0.1:8000/login.html`
- [ ] Attempt login with incorrect password — verify error banner displays.
- [ ] Log in with `admin@crm.local` / `Admin@12345` — verify smooth redirect to Dashboard.
- [ ] Check sidebar footer displays "CRM Administrator".
- [ ] Click the Logout icon — confirm session is destroyed and redirected to login.

### B. Dashboard Functionality
- [ ] Verify Stat cards display live numbers (Total Customers, Completed Calls, Today's Follow-ups, Overdue).
- [ ] Verify Today's scheduled follow-ups appear in the left table.
- [ ] Verify Overdue reminders appear in the right alert box with red badges ("Overdue by X").
- [ ] Click "Call" on any task to open the Log Call modal.
- [ ] Submit a call — verify the task marks as done and counters update immediately.

### C. Excel Import System
- [ ] Navigate to **Excel Imports** (`/imports.html`).
- [ ] Drag and drop an `.xlsx` or `.xls` file (or use `test_samples/sample_customers_batch1.xlsx`).
- [ ] Verify Step 2 preview shows spreadsheet rows.
- [ ] In Step 3, review column mappings and check custom fields.
- [ ] Choose "Skip Duplicate" or "Update Existing".
- [ ] Click "Start Transactional Import".
- [ ] Verify Step 4 summary cards show imported, updated, duplicate, and rejected counts.
- [ ] If rejected rows exist, click "Download Error Report (.xlsx)" to verify row numbers and error descriptions.

### D. All Customers Directory
- [ ] Navigate to **All Customers** (`/customers.html`).
- [ ] Test real-time search by typing a customer's name, phone, or company.
- [ ] Filter by Status (e.g. "Interested", "Converted").
- [ ] Click "Export to Excel" — verify an `.xlsx` download begins.
- [ ] Click on any customer name to open their 360° Profile.

### E. Customer Profile & Call Timeline
- [ ] Verify contact details and `tel:` click-to-call link.
- [ ] Verify Excel Custom Fields card displays imported JSON tags.
- [ ] Verify Source File link displays filename and row number.
- [ ] Click "Log Call" — record an outcome and schedule a next follow-up.
- [ ] Verify the call activity immediately appears on the chronological timeline.

### F. Month-wise Files Explorer
- [ ] Navigate to **Month-wise Files** (`/month-files.html`).
- [ ] Filter by Year and Month.
- [ ] Click "Records" on a file — verify the row-by-row drilldown drawer opens.
- [ ] Click "Excel" to download the original uploaded file.

### G. Reports & Visual Analytics
- [ ] Navigate to **Reports** (`/reports.html`).
- [ ] Confirm the Doughnut chart renders call outcome distribution.
- [ ] Confirm the Bar chart renders monthly customer registrations.
