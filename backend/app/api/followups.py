from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from backend.app.db.database import get_db
from backend.app.db.models import Admin, Followup, FollowupAudit, Customer
from backend.app.api.auth import get_current_admin
from backend.app.services.followup_service import FollowupService
from backend.app.schemas.followup import (
    FollowupCreate, FollowupReschedule, FollowupComplete, 
    FollowupListResponse
)
from backend.app.utils.date_utils import get_current_datetime

router = APIRouter(prefix="/api/followups", tags=["Follow-ups"])

@router.get("", response_model=FollowupListResponse)
def list_followups(
    filter_type: str = Query("today", description="today | upcoming | overdue | completed | all"),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    from backend.app.api.settings import get_system_setting
    from backend.app.core.config import settings
    advance_days = get_system_setting(db, "reminder_advance_days", default=settings.REMINDER_ADVANCE_DAYS)

    if filter_type == "today":
        return FollowupService.get_today_followups(db, page=page, per_page=per_page)
    elif filter_type in ["due_soon", "advance"]:
        return FollowupService.get_due_soon_followups(db, page=page, per_page=per_page, advance_days=advance_days)
    elif filter_type == "upcoming":
        return FollowupService.get_upcoming_followups(db, page=page, per_page=per_page)
    elif filter_type == "overdue":
        return FollowupService.get_overdue_followups(db, page=page, per_page=per_page)
    else:
        # Completed or All
        now = get_current_datetime()
        query = db.query(Followup).join(Customer).filter(Customer.archived_at.is_(None))
        if filter_type == "completed":
            query = query.filter(Followup.status == "Completed")
        query = query.order_by(Followup.scheduled_at.desc())

        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        return {
            "items": [FollowupService._to_followup_dict(f, now) for f in items],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 1
        }

@router.post("", status_code=status.HTTP_201_CREATED)
def schedule_followup(
    data: FollowupCreate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found.")

    followup = FollowupService.schedule_followup(
        db=db,
        customer_id=data.customer_id,
        scheduled_at=data.scheduled_at,
        priority=data.priority or "Medium",
        notes=data.notes,
        admin_id=current_admin.id
    )
    return {"message": "Follow-up scheduled successfully", "followup_id": followup.id}

@router.post("/{followup_id}/reschedule")
def reschedule_followup(
    followup_id: int,
    data: FollowupReschedule,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    f = FollowupService.reschedule_followup(
        db=db,
        followup_id=followup_id,
        new_scheduled_at=data.new_scheduled_at,
        reason=data.reason,
        admin_id=current_admin.id
    )
    if not f:
        raise HTTPException(status_code=404, detail="Follow-up not found.")
    return {"message": "Follow-up rescheduled successfully"}

@router.post("/{followup_id}/complete")
def complete_followup(
    followup_id: int,
    data: FollowupComplete,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    f = FollowupService.complete_followup(
        db=db,
        followup_id=followup_id,
        outcome=data.outcome or "Interested",
        notes=data.notes,
        next_action=data.next_action,
        admin_id=current_admin.id,
        schedule_next=data.schedule_next_followup
    )
    if not f:
        raise HTTPException(status_code=404, detail="Follow-up not found.")
    return {"message": "Follow-up marked as completed"}

@router.post("/{followup_id}/cancel")
def cancel_followup(
    followup_id: int,
    reason: Optional[str] = "Cancelled by user",
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    f = db.query(Followup).filter(Followup.id == followup_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Follow-up not found.")

    f.status = "Cancelled"
    audit = FollowupAudit(
        followup_id=f.id,
        previous_scheduled_at=f.scheduled_at,
        new_scheduled_at=f.scheduled_at,
        previous_status="Pending",
        new_status="Cancelled",
        reason=reason,
        changed_by=current_admin.id
    )
    db.add(audit)
    db.commit()
    return {"message": "Follow-up cancelled"}
