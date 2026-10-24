import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from backend.app.core.config import settings
from backend.app.db.database import get_db
from backend.app.db.models import Admin, Customer, CallHistory, Followup, ImportFileRecord
from backend.app.api.auth import get_current_admin
from backend.app.schemas.call import CallCreate, CallListResponse
from backend.app.utils.date_utils import get_current_datetime
from backend.app.utils.validators import sanitize_for_excel
from backend.app.services.pdf_service import PDFService
from backend.app.api.settings import get_firm_profile

router = APIRouter(tags=["Calls"])

def build_calls_query(
    db: Session,
    outcome: Optional[str] = None,
    search: Optional[str] = None,
    date_preset: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    import_file_id: Optional[int] = None
):
    query = db.query(CallHistory).join(Customer, Customer.id == CallHistory.customer_id)

    if outcome and outcome.strip():
        query = query.filter(CallHistory.outcome == outcome.strip())

    if search and search.strip():
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Customer.name.ilike(s),
                Customer.mobile.ilike(s),
                Customer.company.ilike(s),
                CallHistory.notes.ilike(s),
                CallHistory.next_action.ilike(s)
            )
        )

    if import_file_id:
        query = query.join(ImportFileRecord, ImportFileRecord.customer_id == Customer.id)\
                     .filter(ImportFileRecord.import_file_id == import_file_id)\
                     .distinct()

    now = datetime.now()
    if date_preset == "today":
        start_of_day = datetime(now.year, now.month, now.day, 0, 0, 0)
        query = query.filter(CallHistory.call_datetime >= start_of_day)
    elif date_preset == "yesterday":
        yesterday = now - timedelta(days=1)
        start_yd = datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0)
        end_yd = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59)
        query = query.filter(CallHistory.call_datetime >= start_yd, CallHistory.call_datetime <= end_yd)
    elif date_preset == "week":
        start_week = now - timedelta(days=7)
        query = query.filter(CallHistory.call_datetime >= start_week)
    elif date_preset == "month":
        start_month = datetime(now.year, now.month, 1, 0, 0, 0)
        query = query.filter(CallHistory.call_datetime >= start_month)
    else:
        if date_from and date_from.strip():
            try:
                df = datetime.fromisoformat(date_from.strip())
                query = query.filter(CallHistory.call_datetime >= df)
            except Exception:
                pass
        if date_to and date_to.strip():
            try:
                dt = datetime.fromisoformat(date_to.strip())
                if len(date_to.strip()) <= 10:
                    dt = datetime(dt.year, dt.month, dt.day, 23, 59, 59)
                query = query.filter(CallHistory.call_datetime <= dt)
            except Exception:
                pass

    return query

@router.post("/api/customers/{customer_id}/calls", status_code=status.HTTP_201_CREATED)
def log_customer_call(
    customer_id: int,
    call_data: CallCreate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.archived_at.is_(None)).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found.")

    call_time = call_data.call_datetime or get_current_datetime()

    # 1. Create Call Record
    call = CallHistory(
        customer_id=customer.id,
        followup_id=call_data.followup_id,
        call_datetime=call_time,
        outcome=call_data.outcome,
        notes=call_data.notes,
        next_action=call_data.next_action,
        created_by=current_admin.id
    )
    db.add(call)

    # 2. Update Customer's last contacted and status
    customer.last_contacted_at = call_time
    if call_data.outcome == "Converted":
        customer.status = "Converted"
    elif call_data.outcome == "Not Interested":
        customer.status = "Not Interested"
    elif call_data.outcome in ["Interested", "Call Back Required"]:
        customer.status = "Interested"

    # 3. If linked to an existing pending followup, mark that followup completed
    if call_data.followup_id:
        existing_f = db.query(Followup).filter(Followup.id == call_data.followup_id).first()
        if existing_f and existing_f.status == "Pending":
            existing_f.status = "Completed"
            existing_f.completed_at = call_time

    # 4. If next follow-up is scheduled
    if call_data.schedule_next_followup:
        next_followup = Followup(
            customer_id=customer.id,
            scheduled_at=call_data.schedule_next_followup,
            status="Pending",
            priority=call_data.next_followup_priority or "Medium",
            notes=call_data.next_followup_notes or f"Follow-up scheduled after call: {call_data.outcome}",
            created_by=current_admin.id
        )
        db.add(next_followup)

    db.commit()
    db.refresh(call)

    return {"message": "Call logged successfully", "call_id": call.id}

@router.get("/api/customers/{customer_id}/calls")
def get_customer_calls(
    customer_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found.")

    calls = db.query(CallHistory).filter(CallHistory.customer_id == customer_id)\
              .order_by(CallHistory.call_datetime.desc()).all()

    items = []
    for c in calls:
        items.append({
            "id": c.id,
            "call_datetime": c.call_datetime,
            "outcome": c.outcome,
            "notes": c.notes,
            "next_action": c.next_action,
            "caller": c.caller.full_name if c.caller else "Admin"
        })
    return items

@router.get("/api/calls", response_model=CallListResponse)
def list_all_calls(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    outcome: Optional[str] = None,
    search: Optional[str] = None,
    date_preset: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    import_file_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    query = build_calls_query(
        db=db,
        outcome=outcome,
        search=search,
        date_preset=date_preset,
        date_from=date_from,
        date_to=date_to,
        import_file_id=import_file_id
    )

    query = query.order_by(CallHistory.call_datetime.desc())
    total = query.count()
    calls = query.offset((page - 1) * per_page).limit(per_page).all()

    items = []
    for c in calls:
        cust = c.customer
        prim_rec = next((r for r in cust.import_records if r.import_file), None) if (cust and cust.import_records) else None
        fname = prim_rec.import_file.original_filename if (prim_rec and prim_rec.import_file) else None

        items.append({
            "id": c.id,
            "customer_id": c.customer_id,
            "customer_name": cust.name if cust else "Unknown",
            "customer_mobile": cust.mobile if cust else "",
            "customer_company": cust.company if cust else "",
            "source_file": fname or (cust.source if cust else "Direct"),
            "followup_id": c.followup_id,
            "call_datetime": c.call_datetime,
            "outcome": c.outcome,
            "notes": c.notes,
            "next_action": c.next_action,
            "created_by_name": c.caller.full_name if c.caller else "Admin",
            "created_at": c.created_at
        })

    # Stats calculation
    converted_cnt = db.query(CallHistory).filter(CallHistory.outcome == "Converted").count()
    interested_cnt = db.query(CallHistory).filter(CallHistory.outcome == "Interested").count()
    scheduled_cnt = db.query(CallHistory).filter(CallHistory.outcome == "Call Back Required").count()

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if total > 0 else 1,
        "stats": {
            "total": total,
            "converted": converted_cnt,
            "interested": interested_cnt,
            "scheduled": scheduled_cnt,
            "other": total - (converted_cnt + interested_cnt + scheduled_cnt)
        }
    }

@router.get("/api/calls/export/excel")
def export_calls_excel(
    outcome: Optional[str] = None,
    search: Optional[str] = None,
    date_preset: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    import_file_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Exports filtered calls and work activities to Excel."""
    query = build_calls_query(
        db=db,
        outcome=outcome,
        search=search,
        date_preset=date_preset,
        date_from=date_from,
        date_to=date_to,
        import_file_id=import_file_id
    )
    calls = query.order_by(CallHistory.call_datetime.desc()).limit(10000).all()

    rows = []
    for c in calls:
        cust = c.customer
        prim_rec = next((r for r in cust.import_records if r.import_file), None) if (cust and cust.import_records) else None
        fname = prim_rec.import_file.original_filename if (prim_rec and prim_rec.import_file) else None

        rows.append({
            "Call ID": c.id,
            "Customer Name": sanitize_for_excel(cust.name if cust else "Unknown"),
            "Mobile": sanitize_for_excel(cust.mobile if cust else ""),
            "Company": sanitize_for_excel(cust.company if cust else ""),
            "Date & Time": c.call_datetime.strftime("%Y-%m-%d %H:%M") if c.call_datetime else "",
            "Work Outcome": sanitize_for_excel(c.outcome),
            "Call Notes": sanitize_for_excel(c.notes or ""),
            "Next Action": sanitize_for_excel(c.next_action or ""),
            "Logged By": sanitize_for_excel(c.caller.full_name if c.caller else "Admin"),
            "Source File": sanitize_for_excel(fname or (cust.source if cust else "Direct"))
        })

    df = pd.DataFrame(rows)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"calls_report_{ts}.xlsx"
    filepath = os.path.join(settings.EXPORT_DIR, filename)
    df.to_excel(filepath, index=False)

    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@router.get("/api/calls/export/pdf")
def export_calls_pdf(
    outcome: Optional[str] = None,
    search: Optional[str] = None,
    date_preset: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    import_file_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Exports filtered calls and work activities to a formatted PDF report."""
    query = build_calls_query(
        db=db,
        outcome=outcome,
        search=search,
        date_preset=date_preset,
        date_from=date_from,
        date_to=date_to,
        import_file_id=import_file_id
    )
    calls = query.order_by(CallHistory.call_datetime.desc()).limit(1000).all()

    calls_data = []
    conv_cnt = 0
    inter_cnt = 0
    sched_cnt = 0

    for c in calls:
        cust = c.customer
        if c.outcome == "Converted":
            conv_cnt += 1
        elif c.outcome == "Interested":
            inter_cnt += 1
        elif c.outcome == "Call Back Required":
            sched_cnt += 1

        calls_data.append({
            "customer_name": cust.name if cust else "Unknown",
            "customer_mobile": cust.mobile if cust else "-",
            "call_datetime": c.call_datetime.strftime("%d %b %Y %H:%M") if c.call_datetime else "-",
            "outcome": c.outcome,
            "notes": c.notes or "-",
            "next_action": c.next_action or "-",
            "created_by_name": c.caller.full_name if c.caller else "Admin"
        })

    filter_desc = []
    if outcome:
        filter_desc.append(f"Outcome: {outcome}")
    if date_preset:
        filter_desc.append(f"Date: {date_preset.capitalize()}")
    elif date_from or date_to:
        filter_desc.append(f"Range: {date_from or 'Start'} to {date_to or 'Present'}")
    if import_file_id:
        filter_desc.append(f"File ID: #{import_file_id}")
    if search:
        filter_desc.append(f"Search: '{search}'")

    summary_str = " | ".join(filter_desc) if filter_desc else "All Recorded Calls & Completed Work"

    stats_summary = {
        "total": len(calls_data),
        "converted": conv_cnt,
        "interested": inter_cnt,
        "scheduled": sched_cnt,
        "other": len(calls_data) - (conv_cnt + inter_cnt + sched_cnt)
    }

    pdf_path = PDFService.generate_calls_pdf(calls_data, summary_str, stats_summary, firm_info=get_firm_profile(db))

    return FileResponse(
        path=pdf_path,
        filename="calls_work_report.pdf",
        media_type="application/pdf"
    )
