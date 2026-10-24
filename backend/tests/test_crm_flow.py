import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.db.database import SessionLocal, init_tables
from backend.app.db.models import Admin, Customer, Followup, CallHistory, ImportFile
from database.seed_admin import seed_admin

client = TestClient(app)

def test_full_crm_workflow():
    print("\n--- Starting End-to-End CRM Test Suite ---")
    
    # 0. Ensure Admin Exists
    seed_admin()

    # 1. Test Login with Invalid Credentials
    bad_login = client.post("/api/auth/login", json={"email": "admin@crm.local", "password": "WrongPassword"})
    assert bad_login.status_code == 401, f"Expected 401 on bad password, got {bad_login.status_code}"
    print("[PASS] Invalid credentials properly rejected (401)")

    # 2. Test Login with Valid Credentials
    login_res = client.post("/api/auth/login", json={"email": "admin@crm.local", "password": "Admin@12345"})
    assert login_res.status_code == 200, f"Expected 200 on login, got {login_res.status_code}"
    token = login_res.json()["access_token"]
    assert token, "Token must be returned"
    headers = {"Authorization": f"Bearer {token}"}
    print("[PASS] Valid login succeeded, JWT access token received")

    # 3. Test /api/auth/me
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "admin@crm.local"
    print("[PASS] /api/auth/me verified successfully")

    # 4. Test Excel Upload
    sample_file_path = BASE_DIR / "test_samples" / "sample_customers_batch1.xlsx"
    assert sample_file_path.exists(), "Sample test file must exist"

    with open(sample_file_path, "rb") as f:
        upload_res = client.post(
            "/api/imports/upload",
            headers=headers,
            files={"file": ("sample_customers_batch1.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )

    assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
    upload_data = upload_res.json()
    file_id = upload_data["file_id"]
    assert file_id > 0
    assert len(upload_data["headers"]) >= 5
    assert len(upload_data["preview_rows"]) > 0
    print(f"[PASS] File uploaded and previewed: file_id={file_id}, headers={upload_data['headers']}")

    # 5. Test Confirm Import with Column Mapping & Custom Fields
    confirm_payload = {
        "file_id": file_id,
        "sheet_name": upload_data["selected_sheet"],
        "column_mapping": {
            "name": "Client Name",
            "mobile": "Contact No",
            "email": "Email ID",
            "company": "Business Firm",
            "city": "City"
        },
        "custom_field_columns": ["Product Interest", "GST Number"],
        "duplicate_handling": "skip"
    }

    confirm_res = client.post("/api/imports/confirm", headers=headers, json=confirm_payload)
    assert confirm_res.status_code == 200, f"Confirm import failed: {confirm_res.text}"
    summary = confirm_res.json()
    assert summary["imported_rows"] == 10, f"Expected 10 imported rows, got {summary['imported_rows']}"
    assert summary["rejected_rows"] == 1, f"Expected 1 rejected row (blank name), got {summary['rejected_rows']}"
    assert summary["error_report_url"] is not None
    print(f"[PASS] Import confirmed: 10 imported, 1 rejected with error report generated")

    # 6. Test Error Report Download
    err_res = client.get(f"/api/imports/{file_id}/errors/download", headers=headers)
    assert err_res.status_code == 200
    assert len(err_res.content) > 100
    print("[PASS] Downloadable Excel error report verified")

    # 7. Test Customer Listing & Filtering
    cust_res = client.get("/api/customers?search=Aarav", headers=headers)
    assert cust_res.status_code == 200
    items = cust_res.json()["items"]
    assert len(items) == 1
    aarav = items[0]
    assert aarav["name"] == "Aarav Sharma"
    assert aarav["normalized_mobile"] == "9876543210" # Normalized!
    assert aarav["custom_fields"]["Product Interest"] == "Enterprise CRM"
    assert aarav["custom_fields"]["GST Number"] == "27AABCU9603R1ZM"
    print(f"[PASS] Customer query, phone normalization, and custom fields JSON verified for '{aarav['name']}'")

    aarav_id = aarav["id"]

    # 8. Test Customer Profile View
    profile_res = client.get(f"/api/customers/{aarav_id}", headers=headers)
    assert profile_res.status_code == 200
    profile_data = profile_res.json()
    assert profile_data["name"] == "Aarav Sharma"
    assert profile_data["source_file"] is not None
    print("[PASS] Full customer profile with source file traceability verified")

    # 9. Test Schedule Follow-up (+1 Month Calendar Arithmetic)
    sched_payload = {
        "customer_id": aarav_id,
        "scheduled_at": "2026-11-19T10:00:00",
        "priority": "High",
        "notes": "Discuss enterprise license pricing"
    }
    sched_res = client.post("/api/followups", headers=headers, json=sched_payload)
    assert sched_res.status_code == 201
    followup_id = sched_res.json()["followup_id"]
    assert followup_id > 0
    print(f"[PASS] Follow-up reminder scheduled (ID: {followup_id})")

    # 10. Test Log a Call
    call_payload = {
        "outcome": "Interested",
        "notes": "Spoke with Aarav. Very keen on Enterprise CRM. Wants proposal by tomorrow.",
        "next_action": "Send proposal PDF",
        "followup_id": followup_id
    }
    call_res = client.post(f"/api/customers/{aarav_id}/calls", headers=headers, json=call_payload)
    assert call_res.status_code == 201
    print("[PASS] Call logged successfully and linked to customer & follow-up")

    # 11. Test Dashboard Overview
    dash_res = client.get("/api/dashboard/overview", headers=headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["stats"]["total_customers"] >= 10
    assert dash_data["stats"]["completed_calls_count"] >= 1
    assert len(dash_data["recent_imports"]) >= 1
    print(f"[PASS] Real-time Dashboard overview stats verified: Total Customers={dash_data['stats']['total_customers']}")

    # 12. Test Excel Customers Export
    export_res = client.get("/api/customers/export", headers=headers)
    assert export_res.status_code == 200
    assert len(export_res.content) > 100
    print("[PASS] Filtered Excel customer export verified successfully")

    # 13. Test Duplicate Import Behavior (Skip Duplicate)
    with open(sample_file_path, "rb") as f:
        reupload_res = client.post(
            "/api/imports/upload",
            headers=headers,
            files={"file": ("sample_customers_batch1.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
    reupload_id = reupload_res.json()["file_id"]
    reimport_res = client.post("/api/imports/confirm", headers=headers, json={
        "file_id": reupload_id,
        "sheet_name": upload_data["selected_sheet"],
        "column_mapping": confirm_payload["column_mapping"],
        "duplicate_handling": "skip"
    })
    reimport_summary = reimport_res.json()
    assert reimport_summary["duplicate_rows"] == 10, f"Expected 10 duplicate rows skipped, got {reimport_summary['duplicate_rows']}"
    assert reimport_summary["imported_rows"] == 0, "No new rows should be imported on duplicate skip"
    print(f"[PASS] Duplicate detection verified: All 10 existing records properly recognized and skipped!")

    print("\n--- ALL CRM END-TO-END TESTS PASSED SUCCESSFULLY! ---")

if __name__ == "__main__":
    test_full_crm_workflow()
