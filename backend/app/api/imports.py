import os
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from backend.app.core.config import settings
from backend.app.db.database import get_db
from backend.app.db.models import Admin, ImportFile, ImportFileRecord, Customer
from backend.app.api.auth import get_current_admin
from backend.app.services.excel_service import ExcelService
from backend.app.services.import_service import ImportService
from backend.app.schemas.import_file import ConfirmImportRequest

router = APIRouter(prefix="/api/imports", tags=["Excel Imports"])

ALLOWED_EXTENSIONS = {".xlsx", ".xls"}

@router.post("/upload")
async def upload_excel_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Step 1 & 2 & 3: Uploads Excel file, validates extension, stores safely,
    and returns sheet list, header columns, preview rows, and suggested mappings.
    """
    orig_name = file.filename
    ext = os.path.splitext(orig_name)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension '{ext}'. Only .xlsx and .xls files are supported."
        )

    # Read content to verify size
    contents = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB."
        )

    # Generate secure random stored filename
    stored_name = f"{uuid.uuid4().hex}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{ext}"
    storage_path = os.path.join(settings.UPLOAD_DIR, stored_name)

    with open(storage_path, "wb") as f:
        f.write(contents)

    now = datetime.utcnow()
    # Create preliminary ImportFile record in MySQL
    import_file = ImportFile(
        original_filename=orig_name,
        stored_filename=stored_name,
        storage_path=storage_path,
        uploaded_at=now,
        import_month=now.month,
        import_year=now.year,
        import_status="Pending Configuration",
        created_by=current_admin.id
    )
    db.add(import_file)
    db.commit()
    db.refresh(import_file)

    # Inspect workbook sheets and default preview
    try:
        sheets = ExcelService.get_sheets(storage_path)
        if not sheets:
            raise HTTPException(status_code=400, detail="The Excel workbook does not contain any sheets.")

        first_sheet = sheets[0]
        headers, preview_rows, suggested_mapping = ExcelService.read_sheet_preview(
            storage_path, sheet_name=first_sheet, preview_limit=8
        )

        return {
            "file_id": import_file.id,
            "original_filename": orig_name,
            "stored_filename": stored_name,
            "sheets": sheets,
            "selected_sheet": first_sheet,
            "headers": headers,
            "preview_rows": preview_rows,
            "total_preview_rows": len(preview_rows),
            "suggested_mapping": suggested_mapping
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to inspect Excel workbook: {str(e)}")

@router.get("/{file_id}/preview")
def get_sheet_preview(
    file_id: int,
    sheet_name: str = Query(...),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Returns preview and suggestions for a selected sheet."""
    import_file = db.query(ImportFile).filter(ImportFile.id == file_id).first()
    if not import_file:
        raise HTTPException(status_code=404, detail="Uploaded file record not found.")

    if not os.path.exists(import_file.storage_path):
        raise HTTPException(status_code=404, detail="File not found on server storage.")

    try:
        sheets = ExcelService.get_sheets(import_file.storage_path)
        if sheet_name not in sheets:
            raise HTTPException(status_code=400, detail=f"Sheet '{sheet_name}' does not exist in workbook.")

        headers, preview_rows, suggested_mapping = ExcelService.read_sheet_preview(
            import_file.storage_path, sheet_name=sheet_name, preview_limit=8
        )

        return {
            "file_id": import_file.id,
            "sheets": sheets,
            "selected_sheet": sheet_name,
            "headers": headers,
            "preview_rows": preview_rows,
            "suggested_mapping": suggested_mapping
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read sheet '{sheet_name}': {str(e)}")

@router.post("/confirm")
def confirm_import(
    req: ConfirmImportRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Step 6 & 7: Commits mapped columns and executes transactional batch import.
    """
    import_file = db.query(ImportFile).filter(ImportFile.id == req.file_id).first()
    if not import_file:
        raise HTTPException(status_code=404, detail="Import file record not found.")

    if not os.path.exists(import_file.storage_path):
        raise HTTPException(status_code=404, detail="File missing on disk.")

    # Validation: column_mapping must at least map 'name'
    if not req.column_mapping.get("name"):
        raise HTTPException(status_code=400, detail="Column mapping must at least include 'Customer Name'.")

    try:
        summary = ImportService.process_import(
            db=db,
            import_file=import_file,
            sheet_name=req.sheet_name,
            column_mapping=req.column_mapping,
            custom_field_columns=req.custom_field_columns or [],
            duplicate_handling=req.duplicate_handling,
            data_period_start=req.data_period_start,
            data_period_end=req.data_period_end,
            admin_id=current_admin.id
        )
        return summary
    except Exception as e:
        db.rollback()
        import_file.import_status = "Failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Import execution failed: {str(e)}")

@router.get("")
def list_imports(
    page: int = 1,
    per_page: int = 20,
    month: Optional[int] = None,
    year: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Lists uploaded Excel files with month/year filters and row stats."""
    query = db.query(ImportFile)

    if month:
        query = query.filter(ImportFile.import_month == month)
    if year:
        query = query.filter(ImportFile.import_year == year)
    if status:
        query = query.filter(ImportFile.import_status == status)

    query = query.order_by(desc(ImportFile.uploaded_at))
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    files_list = []
    for f in items:
        files_list.append({
            "id": f.id,
            "original_filename": f.original_filename,
            "uploaded_at": f.uploaded_at,
            "import_month": f.import_month,
            "import_year": f.import_year,
            "worksheet_name": f.worksheet_name,
            "total_rows": f.total_rows,
            "imported_rows": f.imported_rows,
            "updated_rows": f.updated_rows,
            "duplicate_rows": f.duplicate_rows,
            "rejected_rows": f.rejected_rows,
            "import_status": f.import_status,
            "has_error_report": bool(f.error_report_path and os.path.exists(f.error_report_path))
        })

    return {
        "items": files_list,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if total > 0 else 1
    }

@router.get("/{import_id}")
def get_import_details(
    import_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    f = db.query(ImportFile).filter(ImportFile.id == import_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")

    return {
        "id": f.id,
        "original_filename": f.original_filename,
        "uploaded_at": f.uploaded_at,
        "import_month": f.import_month,
        "import_year": f.import_year,
        "worksheet_name": f.worksheet_name,
        "total_rows": f.total_rows,
        "imported_rows": f.imported_rows,
        "updated_rows": f.updated_rows,
        "duplicate_rows": f.duplicate_rows,
        "rejected_rows": f.rejected_rows,
        "import_status": f.import_status,
        "has_error_report": bool(f.error_report_path and os.path.exists(f.error_report_path))
    }

@router.get("/{import_id}/records")
def get_import_records(
    import_id: int,
    page: int = 1,
    per_page: int = 50,
    row_status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Fetches tracked row items for a specific imported file."""
    query = db.query(ImportFileRecord).filter(ImportFileRecord.import_file_id == import_id)
    if row_status:
        query = query.filter(ImportFileRecord.row_status == row_status)

    total = query.count()
    records = query.order_by(ImportFileRecord.source_row_number.asc()).offset((page - 1) * per_page).limit(per_page).all()

    items = []
    for r in records:
        items.append({
            "id": r.id,
            "source_row_number": r.source_row_number,
            "row_status": r.row_status,
            "error_message": r.error_message,
            "customer_id": r.customer_id,
            "customer_name": r.customer.name if r.customer else None,
            "customer_mobile": r.customer.mobile if r.customer else None
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if total > 0 else 1
    }

@router.get("/{import_id}/download")
def download_original_file(
    import_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    f = db.query(ImportFile).filter(ImportFile.id == import_id).first()
    if not f or not os.path.exists(f.storage_path):
        raise HTTPException(status_code=404, detail="File not found on server.")
    return FileResponse(
        path=f.storage_path,
        filename=f.original_filename,
        media_type="application/octet-stream"
    )

@router.get("/{import_id}/errors/download")
def download_error_report(
    import_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    f = db.query(ImportFile).filter(ImportFile.id == import_id).first()
    if not f or not f.error_report_path or not os.path.exists(f.error_report_path):
        raise HTTPException(status_code=404, detail="Error report not found.")
    return FileResponse(
        path=f.error_report_path,
        filename=f"error_report_{f.original_filename}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@router.delete("/{import_id}")
def delete_import_file(
    import_id: int,
    delete_customers: bool = Query(True, description="Whether to also delete customers imported exclusively from this file"),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    f = db.query(ImportFile).filter(ImportFile.id == import_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")

    if delete_customers:
        records = db.query(ImportFileRecord).filter(ImportFileRecord.import_file_id == import_id).all()
        cust_ids = [r.customer_id for r in records if r.customer_id]
        if cust_ids:
            # Delete any calls or followups for these customers first if needed
            db.query(Customer).filter(Customer.id.in_(cust_ids)).delete(synchronize_session=False)

    # Delete disk files if present
    if f.storage_path and os.path.exists(f.storage_path):
        try:
            os.remove(f.storage_path)
        except Exception:
            pass

    if f.error_report_path and os.path.exists(f.error_report_path):
        try:
            os.remove(f.error_report_path)
        except Exception:
            pass

    db.delete(f)
    db.commit()
    return {"message": "File and its records deleted successfully"}

