from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional

from backend.app.db.database import get_db
from backend.app.db.models import Admin, Customer, ImportFileRecord, ImportFile
from backend.app.api.auth import get_current_admin
from backend.app.services.customer_service import CustomerService
from backend.app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerListResponse
from backend.app.services.pdf_service import PDFService
from backend.app.api.settings import get_firm_profile

router = APIRouter(prefix="/api/customers", tags=["Customers"])

@router.get("", response_model=CustomerListResponse)
def list_customers(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    search: Optional[str] = None,
    city: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    import_file_id: Optional[int] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    return CustomerService.get_customers(
        db=db,
        page=page,
        per_page=per_page,
        search=search,
        city=city,
        status=status,
        category=category,
        import_file_id=import_file_id,
        sort_by=sort_by,
        sort_order=sort_order
    )

@router.post("", status_code=status.HTTP_201_CREATED)
def create_customer(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    return CustomerService.create_customer(db=db, data=customer_data)

from backend.app.services.pdf_service import PDFService

@router.get("/export")
def export_customers(
    search: Optional[str] = None,
    city: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    import_file_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Exports filtered customers to an Excel spreadsheet."""
    file_path = CustomerService.export_customers_excel(
        db=db, search=search, city=city, status=status, category=category, import_file_id=import_file_id
    )
    return FileResponse(
        path=file_path,
        filename="customers_export.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@router.get("/export/pdf")
def export_customers_pdf(
    search: Optional[str] = None,
    city: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    import_file_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Exports filtered customers (e.g. Converted, Interested, by File) to a formatted PDF report."""
    res = CustomerService.get_customers(
        db=db, page=1, per_page=5000, search=search, city=city, status=status, category=category, import_file_id=import_file_id
    )
    filter_parts = []
    if status: filter_parts.append(f"Status: {status}")
    if city: filter_parts.append(f"City: {city}")
    if category: filter_parts.append(f"Category: {category}")
    if import_file_id: filter_parts.append(f"File ID: #{import_file_id}")
    if search: filter_parts.append(f"Search: '{search}'")

    summary_str = " | ".join(filter_parts) if filter_parts else "All Customers in Directory"
    pdf_path = PDFService.generate_customers_pdf(res.get("items", []), summary_str, firm_info=get_firm_profile(db))

    return FileResponse(
        path=pdf_path,
        filename="customers_report.pdf",
        media_type="application/pdf"
    )

@router.get("/{customer_id}")
def get_customer_details(
    customer_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    customer = CustomerService.get_customer_by_id(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found.")

    # Call history items
    calls = []
    for c in customer.calls:
        calls.append({
            "id": c.id,
            "call_datetime": c.call_datetime,
            "outcome": c.outcome,
            "notes": c.notes,
            "next_action": c.next_action,
            "caller": c.caller.full_name if c.caller else "Admin",
            "created_at": c.created_at
        })

    # Follow-ups items
    followups = []
    for f in customer.followups:
        followups.append({
            "id": f.id,
            "scheduled_at": f.scheduled_at,
            "status": f.status,
            "priority": f.priority,
            "notes": f.notes,
            "completed_at": f.completed_at,
            "created_at": f.created_at
        })

    # Find source Excel file if imported
    import_rec = db.query(ImportFileRecord).filter(ImportFileRecord.customer_id == customer.id).first()
    source_file_info = None
    if import_rec and import_rec.import_file:
        source_file_info = {
            "file_id": import_rec.import_file_id,
            "filename": import_rec.import_file.original_filename,
            "row_number": import_rec.source_row_number,
            "uploaded_at": import_rec.import_file.uploaded_at
        }

    return {
        "id": customer.id,
        "customer_code": customer.customer_code,
        "name": customer.name,
        "mobile": customer.mobile,
        "normalized_mobile": customer.normalized_mobile,
        "alternate_phone": customer.alternate_phone,
        "email": customer.email,
        "normalized_email": customer.normalized_email,
        "company": customer.company,
        "address": customer.address,
        "city": customer.city,
        "state": customer.state,
        "country": customer.country,
        "category": customer.category,
        "source": customer.source,
        "status": customer.status,
        "custom_fields": customer.custom_fields or {},
        "last_contacted_at": customer.last_contacted_at,
        "created_at": customer.created_at,
        "updated_at": customer.updated_at,
        "source_file": source_file_info,
        "calls": calls,
        "followups": followups
    }

@router.put("/{customer_id}")
def update_customer_details(
    customer_id: int,
    update_data: CustomerUpdate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    cust = CustomerService.update_customer(db, customer_id, update_data)
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found.")
    return {"message": "Customer updated successfully", "customer": cust}

@router.delete("/{customer_id}")
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    cust = db.query(Customer).filter(Customer.id == customer_id).first()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found.")
    
    # Delete associated records
    db.query(ImportFileRecord).filter(ImportFileRecord.customer_id == customer_id).delete(synchronize_session=False)
    db.delete(cust)
    db.commit()
    return {"message": "Customer deleted successfully"}

