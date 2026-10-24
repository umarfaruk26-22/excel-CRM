# Customer Follow-up CRM — REST API Reference

All endpoints are hosted under `http://127.0.0.1:8000/api`. Interactive OpenAPI documentation is also accessible at `http://127.0.0.1:8000/docs`.

---

## 1. Authentication (`/api/auth`)

### `POST /api/auth/login`
Authenticates administrator credentials and returns a signed JWT access token while setting an HTTP-only session cookie.
- **Rate Limit:** 5 attempts per 5 minutes per client IP.
- **Request Body:**
  ```json
  {
    "email": "admin@crm.local",
    "password": "Admin@12345"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "expires_in": 86400,
    "admin": {
      "id": 1,
      "email": "admin@crm.local",
      "full_name": "CRM Administrator",
      "is_active": true
    }
  }
  ```

### `POST /api/auth/logout`
Clears the `access_token` session cookie.

### `GET /api/auth/me`
Returns current authenticated administrator profile.

---

## 2. Dashboard (`/api/dashboard`)

### `GET /api/dashboard/stats`
Returns aggregated real-time metric counts:
- `total_customers`, `total_files`, `today_followups_count`, `upcoming_followups_count`, `overdue_followups_count`, `completed_calls_count`, `pending_followups_count`.

### `GET /api/dashboard/overview`
Returns complete dashboard payload in a single round-trip: stats, today's follow-ups, overdue follow-ups, upcoming reminders, recent imports, and recent calls.

---

## 3. Excel Imports (`/api/imports`)

### `POST /api/imports/upload`
Uploads an `.xlsx` or `.xls` file (multipart form data). Validates extension and file size (max 25MB). Returns sheet names, headers, top 8 preview rows, and suggested field mappings.

### `GET /api/imports/{file_id}/preview?sheet_name=Sheet1`
Reads preview and suggestions for a specific sheet.

### `POST /api/imports/confirm`
Executes transactional batch import into MySQL with duplicate handling.
- **Request Body:**
  ```json
  {
    "file_id": 1,
    "sheet_name": "Sheet1",
    "column_mapping": {
      "name": "Customer Name",
      "mobile": "Mobile Number",
      "email": "Email ID",
      "company": "Company Name",
      "city": "City"
    },
    "custom_field_columns": ["GST Number", "Product Interest"],
    "duplicate_handling": "skip"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "import_id": 1,
    "original_filename": "leads_october.xlsx",
    "total_rows": 50,
    "imported_rows": 48,
    "updated_rows": 0,
    "duplicate_rows": 2,
    "rejected_rows": 0,
    "import_status": "Completed",
    "error_report_url": null
  }
  ```

### `GET /api/imports`
Lists all uploaded files with query filters: `month`, `year`, `status`, `page`, `per_page`.

### `GET /api/imports/{import_id}/records`
Returns individual row records from a specific import file.

### `GET /api/imports/{import_id}/download`
Downloads original uploaded Excel workbook.

### `GET /api/imports/{import_id}/errors/download`
Downloads Excel spreadsheet of validation errors (with row numbers).

---

## 4. Customers (`/api/customers`)

### `GET /api/customers`
Paginated, filtered customer listing.
- **Query Parameters:** `page`, `per_page`, `search`, `city`, `status`, `category`, `import_file_id`, `sort_by`, `sort_order`.

### `POST /api/customers`
Creates a single customer manually.

### `GET /api/customers/{customer_id}`
Returns full 360° profile, including custom fields JSON, source Excel file information, call history timeline, and scheduled follow-ups.

### `PUT /api/customers/{customer_id}`
Updates customer details.

### `GET /api/customers/export`
Exports filtered customers to an `.xlsx` file with formula injection sanitization.

---

## 5. Calls & Follow-ups

### `POST /api/customers/{customer_id}/calls`
Logs a call interaction. Automatically updates `last_contacted_at` and customer status. Optionally marks an existing follow-up as completed and schedules a next follow-up.
- **Outcomes:** `Interested`, `Busy`, `Converted`, `No Answer`, `Not Interested`, `Call Back Required`, `Wrong Number`, `Other`.

### `GET /api/calls`
Lists all logged calls across the CRM with search and outcome filters.

### `GET /api/followups?filter_type={today|upcoming|overdue|completed|all}`
Returns follow-up reminders.

### `POST /api/followups`
Schedules a new follow-up.

### `POST /api/followups/{id}/reschedule`
Reschedules follow-up and logs entry in `followup_audit`.

### `POST /api/followups/{id}/complete`
Marks follow-up completed and logs call outcome.

### `POST /api/followups/{id}/cancel`
Cancels follow-up with reason.

---

## 6. Reports (`/api/reports`)

### `GET /api/reports/summary`
KPI summary numbers.

### `GET /api/reports/outcomes`
Aggregated counts grouped by call outcome.

### `GET /api/reports/growth`
Customer registrations grouped by year and month.
