import os
import hashlib
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.core.config import settings
from backend.app.db.models import Customer, ImportFile, ImportFileRecord
from backend.app.utils.validators import normalize_phone, normalize_email, sanitize_for_excel

class ImportService:
    @staticmethod
    def process_import(
        db: Session,
        import_file: ImportFile,
        sheet_name: str,
        column_mapping: Dict[str, str], # CRM field -> Excel column
        custom_field_columns: List[str],
        duplicate_handling: str = "skip", # skip | update | import_new
        data_period_start: Optional[date] = None,
        data_period_end: Optional[date] = None,
        admin_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Executes transactional Excel data import into MySQL.
        """
        file_path = import_file.storage_path
        ext = os.path.splitext(file_path)[1].lower()
        engine = "openpyxl" if ext == ".xlsx" else "xlrd"

        df = pd.read_excel(file_path, sheet_name=sheet_name, engine=engine)

        total_rows = len(df)
        imported_rows = 0
        updated_rows = 0
        duplicate_rows = 0
        rejected_rows = 0
        error_records = []

        # Invert mapping: Excel Col -> CRM Field
        rev_mapping = {col: field for field, col in column_mapping.items() if col}

        # Update import_file metadata
        import_file.worksheet_name = sheet_name
        import_file.total_rows = total_rows
        import_file.data_period_start = data_period_start
        import_file.data_period_end = data_period_end
        import_file.created_by = admin_id
        import_file.import_status = "In Progress"
        db.commit()

        # Pre-cache existing customers by code, mobile, email for fast in-memory lookup during batch
        existing_by_code = {}
        existing_by_mobile = {}
        existing_by_email = {}

        customers = db.query(Customer).filter(Customer.archived_at.is_(None)).all()
        for c in customers:
            if c.customer_code:
                existing_by_code[c.customer_code.strip().lower()] = c
            if c.normalized_mobile:
                existing_by_mobile[c.normalized_mobile] = c
            if c.normalized_email:
                existing_by_email[c.normalized_email] = c

        records_to_add = []

        for idx, row in df.iterrows():
            row_num = idx + 2 # 1-based, header is row 1
            raw_row_data = {}
            for col in df.columns:
                raw_row_data[str(col).strip()] = None if pd.isna(row[col]) else row[col]

            # Check if entirely blank row
            if all(v is None or str(v).strip() == "" for v in raw_row_data.values()):
                continue

            # Extract mapped CRM fields
            crm_data = {}
            for field, col_name in column_mapping.items():
                if col_name and col_name in raw_row_data:
                    val = raw_row_data[col_name]
                    crm_data[field] = str(val).strip() if val is not None and not pd.isna(val) else None
                else:
                    crm_data[field] = None

            # Collect custom fields
            custom_fields_dict = {}
            for custom_col in (custom_field_columns or []):
                if custom_col in raw_row_data and raw_row_data[custom_col] is not None:
                    custom_fields_dict[custom_col] = str(raw_row_data[custom_col])

            # Validation: Name is strictly required
            name = crm_data.get("name")
            if not name or name.lower() in ["nan", "none", "null", "-", ""]:
                rejected_rows += 1
                err_msg = "Customer name is missing or invalid"
                error_records.append({
                    "Row Number": row_num,
                    "Customer Name": name or "BLANK",
                    "Mobile": crm_data.get("mobile") or "",
                    "Email": crm_data.get("email") or "",
                    "Error Details": err_msg
                })
                records_to_add.append(ImportFileRecord(
                    import_file_id=import_file.id,
                    customer_id=None,
                    source_row_number=row_num,
                    row_status="Rejected",
                    error_message=err_msg
                ))
                continue

            # Normalize mobile and email
            raw_mobile = crm_data.get("mobile")
            norm_mobile = normalize_phone(raw_mobile)
            raw_email = crm_data.get("email")
            norm_email = normalize_email(raw_email)
            cust_code = crm_data.get("customer_code")
            code_key = cust_code.strip().lower() if cust_code else None

            # Duplicate Detection
            matched_customer = None
            if code_key and code_key in existing_by_code:
                matched_customer = existing_by_code[code_key]
            elif norm_mobile and norm_mobile in existing_by_mobile:
                matched_customer = existing_by_mobile[norm_mobile]
            elif norm_email and norm_email in existing_by_email:
                matched_customer = existing_by_email[norm_email]

            # Handle duplicate according to strategy
            if matched_customer and duplicate_handling != "import_new":
                if duplicate_handling == "skip":
                    duplicate_rows += 1
                    records_to_add.append(ImportFileRecord(
                        import_file_id=import_file.id,
                        customer_id=matched_customer.id,
                        source_row_number=row_num,
                        row_status="Duplicate_Skipped",
                        error_message="Skipped as existing duplicate"
                    ))
                    continue
                elif duplicate_handling == "update":
                    # Update fields if new non-empty values provided
                    if name: matched_customer.name = name
                    if raw_mobile: 
                        matched_customer.mobile = raw_mobile
                        matched_customer.normalized_mobile = norm_mobile
                    if raw_email: 
                        matched_customer.email = raw_email
                        matched_customer.normalized_email = norm_email
                    if crm_data.get("alternate_phone"): matched_customer.alternate_phone = crm_data.get("alternate_phone")
                    if crm_data.get("company"): matched_customer.company = crm_data.get("company")
                    if crm_data.get("address"): matched_customer.address = crm_data.get("address")
                    if crm_data.get("city"): matched_customer.city = crm_data.get("city")
                    if crm_data.get("state"): matched_customer.state = crm_data.get("state")
                    if crm_data.get("country"): matched_customer.country = crm_data.get("country")
                    if crm_data.get("category"): matched_customer.category = crm_data.get("category")

                    # Merge custom fields
                    if custom_fields_dict:
                        existing_cf = matched_customer.custom_fields or {}
                        existing_cf.update(custom_fields_dict)
                        matched_customer.custom_fields = existing_cf

                    updated_rows += 1
                    records_to_add.append(ImportFileRecord(
                        import_file_id=import_file.id,
                        customer_id=matched_customer.id,
                        source_row_number=row_num,
                        row_status="Updated"
                    ))
                    continue

            # Create New Customer
            new_customer = Customer(
                customer_code=cust_code or None,
                name=name,
                mobile=raw_mobile or None,
                normalized_mobile=norm_mobile,
                alternate_phone=crm_data.get("alternate_phone") or None,
                email=raw_email or None,
                normalized_email=norm_email,
                company=crm_data.get("company") or None,
                address=crm_data.get("address") or None,
                city=crm_data.get("city") or None,
                state=crm_data.get("state") or None,
                country=crm_data.get("country") or "India",
                category=crm_data.get("category") or "General",
                source=f"Import: {import_file.original_filename}",
                status=crm_data.get("status") or "New",
                custom_fields=custom_fields_dict if custom_fields_dict else None
            )
            db.add(new_customer)
            db.flush() # Populate new_customer.id

            # Update in-memory caches
            if code_key: existing_by_code[code_key] = new_customer
            if norm_mobile: existing_by_mobile[norm_mobile] = new_customer
            if norm_email: existing_by_email[norm_email] = new_customer

            imported_rows += 1
            records_to_add.append(ImportFileRecord(
                import_file_id=import_file.id,
                customer_id=new_customer.id,
                source_row_number=row_num,
                row_status="Imported"
            ))

        # Add all tracking records
        db.add_all(records_to_add)

        # Generate error report if there are any rejected records
        error_report_rel_path = None
        if error_records:
            err_df = pd.DataFrame(error_records)
            err_filename = f"error_report_import_{import_file.id}.xlsx"
            err_full_path = os.path.join(settings.ERROR_REPORT_DIR, err_filename)
            err_df.to_excel(err_full_path, index=False)
            error_report_rel_path = f"/api/imports/{import_file.id}/errors/download"
            import_file.error_report_path = err_full_path

        # Update final stats
        import_file.imported_rows = imported_rows
        import_file.updated_rows = updated_rows
        import_file.duplicate_rows = duplicate_rows
        import_file.rejected_rows = rejected_rows
        import_file.import_status = "Completed" if rejected_rows == 0 else "Completed with Errors"

        db.commit()

        return {
            "import_id": import_file.id,
            "original_filename": import_file.original_filename,
            "uploaded_at": import_file.uploaded_at,
            "total_rows": total_rows,
            "imported_rows": imported_rows,
            "updated_rows": updated_rows,
            "duplicate_rows": duplicate_rows,
            "rejected_rows": rejected_rows,
            "import_status": import_file.import_status,
            "error_report_url": error_report_rel_path
        }
