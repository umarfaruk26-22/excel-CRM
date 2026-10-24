# Customer Follow-up CRM — Local Setup Guide (Windows & XAMPP)

This guide walks you through setting up and running the **Customer Follow-up CRM** locally on Windows using Python, FastAPI, and MySQL with XAMPP.

---

## 1. Prerequisites

- **Python 3.10+** (Tested and verified on Python 3.14.6)
- **XAMPP for Windows** (With Apache and MySQL modules)
- Modern Web Browser (Chrome, Edge, Firefox, Brave)

---

## 2. Step-by-Step Setup

### Step 1: Start MySQL in XAMPP
1. Open the **XAMPP Control Panel**.
2. Click **Start** next to the **MySQL** module.
3. Ensure MySQL shows as active on port `3306`.
4. *(Optional)* Click **Admin** next to MySQL or open `http://localhost/phpmyadmin` in your browser.

> [!NOTE]
> The application will automatically create the database `customer_followup_crm` on first startup if it does not already exist.

---

### Step 2: Configure Virtual Environment & Install Dependencies
Open PowerShell or Command Prompt inside the project directory:

```powershell
cd "d:\WEBSITES OF AYAN & UMAR\excel data webapp"

# Create Python virtual environment
python -m venv .venv

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1
# (Or in CMD: .\.venv\Scripts\activate.bat)

# Install required dependencies
pip install -r backend\requirements.txt
```

---

### Step 3: Configure Environment Variables
Verify or edit `backend/.env`. A ready-to-run template is configured for local XAMPP:

```env
APP_NAME="Customer Follow-up CRM"
APP_ENV=development
SECRET_KEY=crm-secret-prod-token-94f83b2847a9e102f91c95e29c1b3f94
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
TIMEZONE=Asia/Kolkata

# MySQL Credentials (Default XAMPP: user 'root' with empty password)
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=customer_followup_crm

# File Upload Settings
MAX_UPLOAD_SIZE_MB=25
```

---

### Step 4: Initialize MySQL Database & Seed Default Admin
Run the automated database initializer and admin account creator:

```powershell
# Initializes customer_followup_crm database and all 8 normalized tables
python database/init_db.py

# Creates default administrator account
python database/seed_admin.py
```

**Default Admin Credentials:**
- **Email:** `admin@crm.local`
- **Password:** `Admin@12345`

To create a custom administrator:
```powershell
python database/seed_admin.py --email your_email@company.com --password YourSecretPassword --name "Your Name"
```

---

### Step 5: Start the Full-Stack Web Application
Start Uvicorn with auto-reload:

```powershell
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Once started, open your web browser and navigate to:
**`http://127.0.0.1:8000`**

Log in using `admin@crm.local` and `Admin@12345`.

---

## 3. Core Workflows Guide

### 1. Excel File Import Wizard (`/imports.html`)
- Supports `.xlsx` and legacy `.xls` formats.
- Drag & drop your Excel file.
- Inspect sheet preview and customize column mapping.
- Extra columns (e.g. GST Number, Product Interest) are automatically stored in the `custom_fields` JSON column.
- Select duplicate handling: *Skip Duplicate* (Recommended), *Update Existing*, or *Import as Separate Record*.
- If any row has missing required customer names, valid rows are still imported and a downloadable row-by-row error spreadsheet is generated.

### 2. Follow-up Reminders Engine (`/followups.html` & Dashboard)
- Reminders are stored permanently in MySQL.
- Evaluates **Today's Due**, **Upcoming**, and **Overdue** status based on actual current timestamp and `Asia/Kolkata` timezone.
- Provides quick scheduling buttons: *Tomorrow*, *+7 Days*, *+15 Days*, *+1 Month* (with safe month-end calendar arithmetic).
- Clicking *Reschedule* logs an audit trail in `followup_audit`.

### 3. One-Click Phone Calls & Call Logging
- Click on any phone number to launch the device's default dialer (`tel:` link).
- Click **Log Call** to record call outcomes (`Interested`, `Busy`, `Converted`, `No Answer`, `Not Interested`, etc.).
- Automatically updates customer's last contacted timestamp and allows scheduling the next follow-up in one submit.

### 4. Month-Wise Files Explorer (`/month-files.html`)
- Groups uploaded Excel files by upload month and year.
- Click **Records** to view every individual row imported from a file.
- Click **Excel** to download the original uploaded workbook.
- Click **Errors** to download the row error report.

---

## 4. Troubleshooting

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| `Can't connect to MySQL server on '127.0.0.1:3306'` | MySQL is not started in XAMPP | Open XAMPP Control Panel and click **Start** next to MySQL. |
| `Access denied for user 'root'@'localhost'` | MySQL root password is not empty | If you have a custom root password in phpMyAdmin, update `DB_PASSWORD` in `backend/.env`. |
| Port 8000 already in use | Another process running on port 8000 | Run `python -m uvicorn backend.app.main:app --port 8080` instead. |
| `email-validator is not installed` | Missing optional dependency | Run `pip install -r backend/requirements.txt` which includes `email-validator`. |
