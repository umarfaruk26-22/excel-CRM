# Customer Follow-up CRM

A full-stack, production-ready Customer Relationship Management web application built with **FastAPI**, **MySQL (XAMPP)**, and **Vanilla JavaScript & CSS**.

The system enables businesses to import customer records from varied Excel files (`.xlsx` and `.xls`), map spreadsheet columns dynamically, persist records permanently in MySQL, log calls, and schedule automated follow-up reminders with calendar arithmetic.

---

## Key Features

1. **Smart Multi-Step Excel Import Engine:**
   - Supports modern `.xlsx` (via `openpyxl`) and legacy `.xls` (via `xlrd`).
   - Multi-sheet selection and data preview before committing.
   - Fuzzy column auto-mapping suggestions with manual dropdown overrides.
   - Structured JSON storage for unmapped extra columns (`custom_fields`).
   - Configurable duplicate detection (by Customer ID, normalized 10-digit mobile, or email).
   - Transactional database execution with downloadable row-by-row error reports for rejected data.

2. **Real-Time Follow-up & Reminder Engine:**
   - Automatically surfaces **Today's Due**, **Upcoming**, and **Overdue** follow-ups evaluated directly from MySQL in `Asia/Kolkata` timezone.
   - Presets for *Tomorrow*, *+7 Days*, *+15 Days*, *+1 Month* (with safe calendar month-end arithmetic, e.g. Jan 31 $\to$ Feb 28).
   - Complete audit trail of reschedules and completions in `followup_audit`.

3. **360° Customer Profile & Call History:**
   - Full contact details, source Excel file traceability with row numbers, and custom field tags.
   - One-click safe `tel:` calling links.
   - Call logging with outcomes (`Interested`, `Busy`, `Converted`, `No Answer`, `Not Interested`, etc.), notes, and next actions.
   - Chronological visual timeline of all past touchpoints.

4. **Month-Wise File Explorer:**
   - Browse Excel imports grouped by Year and Month.
   - Inspect individual rows imported from each workbook.
   - Secure download of original uploaded files and error reports.

5. **Visual Reports & Excel Export:**
   - Chart.js visual analytics: Call outcomes breakdown (doughnut chart) and monthly customer acquisition (bar chart).
   - Filtered customer data export to `.xlsx` with formula injection prevention (`=`, `+`, `-`, `@` escaped).

6. **Enterprise Security & Architecture:**
   - Secure admin authentication with `bcrypt` password hashing and JWT sessions (HTTP-only cookies + Bearer tokens).
   - Login rate-limiting / brute-force protection.
   - Unified serving: FastAPI serves both the REST API and the frontend directly at `http://127.0.0.1:8000`, eliminating CORS and `file://` protocol restrictions.

---

## Project Structure

```
excel-data-webapp/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app & static file routes
│   │   ├── core/                    # Config, security (bcrypt/JWT), rate limiter
│   │   ├── db/                      # Database connection & SQLAlchemy models
│   │   ├── schemas/                 # Pydantic v2 validation models
│   │   ├── api/                     # API routers (auth, dashboard, imports, customers, calls, followups, reports)
│   │   ├── services/                # Excel parsing, batch import, customer, followup & report services
│   │   └── utils/                   # Phone/email normalization, date arithmetic helpers
│   ├── requirements.txt             # Locked Python dependencies
│   └── tests/                       # End-to-end automated test suite
├── frontend/
│   ├── index.html                   # Real-time Dashboard
│   ├── login.html                   # Admin Login
│   ├── customers.html               # All Customers Directory
│   ├── customer-details.html        # 360° Customer Profile & Timeline
│   ├── imports.html                 # Excel Import Wizard
│   ├── month-files.html             # Month-wise File Explorer
│   ├── followups.html               # Dedicated Follow-up Tracker
│   ├── call-history.html            # Complete Call Logs
│   ├── reports.html                 # Visual Analytics
│   ├── settings.html                # Application & Matching Settings
│   └── assets/                      # CSS design tokens & modular client scripts
├── database/
│   ├── schema.sql                   # MySQL DDL schema
│   ├── init_db.py                   # Automated database initializer
│   └── seed_admin.py                # Admin creation / reset utility
├── storage/
│   ├── uploads/                     # Server-side stored original Excel files
│   ├── import-errors/               # Downloadable Excel error reports
│   └── exports/                     # Generated Excel export files
└── docs/
    ├── SETUP.md                     # Step-by-step Windows & XAMPP guide
    ├── API.md                       # Full REST API documentation
    └── ACCEPTANCE_TESTS.md          # Automated & manual test verification checklist
```

---

## Quick Start Guide

### 1. Start MySQL in XAMPP
Open XAMPP Control Panel and click **Start** on the **MySQL** module (default port `3306`).

### 2. Setup Virtual Environment & Install Dependencies
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

### 3. Initialize Database & Default Admin
```powershell
python database/init_db.py
python database/seed_admin.py
```
*Default Credentials:*
- **Email:** `admin@crm.local`
- **Password:** `Admin@12345`

### 4. Start Application Server
```powershell
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Open your browser at **`http://127.0.0.1:8000`** and log in!

---

## Running the Automated Test Suite

To verify all endpoints, file uploads, duplicate handling, and date calculations:
```powershell
.\.venv\Scripts\python.exe backend\tests\test_crm_flow.py
```
All 13 core test suites will execute and assert status code 200, row counts, and data integrity.

---

## Documentation Links
- [Step-by-Step Local Setup (Windows & XAMPP)](file:///d:/WEBSITES%20OF%20AYAN%20&%20UMAR/excel%20data%20webapp/docs/SETUP.md)
- [Complete REST API Documentation](file:///d:/WEBSITES%20OF%20AYAN%20&%20UMAR/excel%20data%20webapp/docs/API.md)
- [Acceptance Testing Checklist](file:///d:/WEBSITES%20OF%20AYAN%20&%20UMAR/excel%20data%20webapp/docs/ACCEPTANCE_TESTS.md)
