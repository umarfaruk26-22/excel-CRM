from datetime import datetime, date, time, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from backend.app.db.models import Followup, FollowupAudit, Customer, CallHistory
from backend.app.utils.date_utils import get_current_datetime, add_calendar_months

class FollowupService:
    @staticmethod
    def _format_overdue_text(scheduled_at: datetime, now: datetime) -> str:
        diff = now - scheduled_at
        if diff.days > 0:
            return f"Overdue by {diff.days} day{'s' if diff.days > 1 else ''}"
        hours = int(diff.total_seconds() // 3600)
        if hours > 0:
            return f"Overdue by {hours} hour{'s' if hours > 1 else ''}"
        minutes = int(diff.total_seconds() // 60)
        return f"Overdue by {max(minutes, 1)} min"

    @staticmethod
    def _to_followup_dict(f: Followup, now: datetime, advance_days: int = 5) -> Dict[str, Any]:
        is_overdue = f.status == "Pending" and f.scheduled_at < now
        overdue_text = FollowupService._format_overdue_text(f.scheduled_at, now) if is_overdue else None

        days_until_due = None
        is_due_soon = False
        due_soon_text = None

        if f.status == "Pending" and not is_overdue:
            diff_days = (f.scheduled_at.date() - now.date()).days
            days_until_due = diff_days
            if diff_days <= advance_days:
                is_due_soon = True
                if diff_days == 0:
                    due_soon_text = "Due Today"
                elif diff_days == 1:
                    due_soon_text = "Due Tomorrow"
                else:
                    due_soon_text = f"Due in {diff_days} days"

        return {
            "id": f.id,
            "customer_id": f.customer_id,
            "customer_name": f.customer.name if f.customer else "Unknown",
            "customer_mobile": f.customer.mobile if f.customer else None,
            "customer_company": f.customer.company if f.customer else None,
            "customer_city": f.customer.city if f.customer else None,
            "scheduled_at": f.scheduled_at,
            "status": f.status,
            "priority": f.priority,
            "notes": f.notes,
            "completed_at": f.completed_at,
            "created_at": f.created_at,
            "updated_at": f.updated_at,
            "is_overdue": is_overdue,
            "overdue_text": overdue_text,
            "is_due_soon": is_due_soon,
            "days_until_due": days_until_due,
            "due_soon_text": due_soon_text
        }

    @staticmethod
    def get_due_soon_followups(db: Session, page: int = 1, per_page: int = 25, advance_days: int = 5) -> Dict[str, Any]:
        """Returns follow-ups due within the advance notice period (e.g. 5 days)."""
        now = get_current_datetime()
        today_start = datetime.combine(now.date(), time.min)
        deadline = datetime.combine((now + timedelta(days=advance_days)).date(), time.max)

        query = db.query(Followup).join(Customer)\
            .filter(Customer.archived_at.is_(None))\
            .filter(Followup.status == "Pending")\
            .filter(Followup.scheduled_at >= today_start, Followup.scheduled_at <= deadline)\
            .order_by(asc(Followup.scheduled_at))

        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        return {
            "items": [FollowupService._to_followup_dict(f, now, advance_days) for f in items],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 1,
            "advance_days": advance_days
        }

    @staticmethod
    def get_today_followups(db: Session, page: int = 1, per_page: int = 25) -> Dict[str, Any]:
        """Returns follow-ups scheduled for today (calendar day in local TZ)."""
        now = get_current_datetime()
        today_start = datetime.combine(now.date(), time.min)
        today_end = datetime.combine(now.date(), time.max)

        query = db.query(Followup).join(Customer)\
            .filter(Customer.archived_at.is_(None))\
            .filter(Followup.status == "Pending")\
            .filter(Followup.scheduled_at >= today_start, Followup.scheduled_at <= today_end)\
            .order_by(asc(Followup.scheduled_at))

        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        return {
            "items": [FollowupService._to_followup_dict(f, now) for f in items],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 1
        }

    @staticmethod
    def get_upcoming_followups(db: Session, page: int = 1, per_page: int = 25, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None) -> Dict[str, Any]:
        """Returns follow-ups scheduled in the future (after today)."""
        now = get_current_datetime()
        today_end = datetime.combine(now.date(), time.max)
        start_bound = date_from if date_from else today_end

        query = db.query(Followup).join(Customer)\
            .filter(Customer.archived_at.is_(None))\
            .filter(Followup.status == "Pending")\
            .filter(Followup.scheduled_at > start_bound)

        if date_to:
            query = query.filter(Followup.scheduled_at <= date_to)

        query = query.order_by(asc(Followup.scheduled_at))

        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        return {
            "items": [FollowupService._to_followup_dict(f, now) for f in items],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 1
        }

    @staticmethod
    def get_overdue_followups(db: Session, page: int = 1, per_page: int = 25) -> Dict[str, Any]:
        """Returns pending follow-ups whose scheduled datetime is in the past."""
        now = get_current_datetime()
        query = db.query(Followup).join(Customer)\
            .filter(Customer.archived_at.is_(None))\
            .filter(Followup.status == "Pending")\
            .filter(Followup.scheduled_at < now)\
            .order_by(asc(Followup.scheduled_at))

        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        return {
            "items": [FollowupService._to_followup_dict(f, now) for f in items],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 1
        }

    @staticmethod
    def schedule_followup(
        db: Session,
        customer_id: int,
        scheduled_at: datetime,
        priority: str = "Medium",
        notes: Optional[str] = None,
        admin_id: Optional[int] = None
    ) -> Followup:
        followup = Followup(
            customer_id=customer_id,
            scheduled_at=scheduled_at,
            status="Pending",
            priority=priority,
            notes=notes,
            created_by=admin_id
        )
        db.add(followup)

        # Update customer status to Follow-up Scheduled if not already converted
        cust = db.query(Customer).filter(Customer.id == customer_id).first()
        if cust and cust.status not in ["Converted", "Not Interested"]:
            cust.status = "Follow-up Scheduled"

        db.commit()
        db.refresh(followup)
        return followup

    @staticmethod
    def reschedule_followup(
        db: Session,
        followup_id: int,
        new_scheduled_at: datetime,
        reason: Optional[str] = None,
        admin_id: Optional[int] = None
    ) -> Optional[Followup]:
        followup = db.query(Followup).filter(Followup.id == followup_id).first()
        if not followup:
            return None

        # Create audit record
        audit = FollowupAudit(
            followup_id=followup.id,
            previous_scheduled_at=followup.scheduled_at,
            new_scheduled_at=new_scheduled_at,
            previous_status=followup.status,
            new_status="Rescheduled",
            reason=reason or "Rescheduled",
            changed_by=admin_id
        )
        db.add(audit)

        followup.scheduled_at = new_scheduled_at
        followup.status = "Pending" # Re-set to pending for the new date
        followup.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(followup)
        return followup

    @staticmethod
    def complete_followup(
        db: Session,
        followup_id: int,
        outcome: str = "Interested",
        notes: Optional[str] = None,
        next_action: Optional[str] = None,
        admin_id: Optional[int] = None,
        schedule_next: Optional[datetime] = None
    ) -> Optional[Followup]:
        followup = db.query(Followup).filter(Followup.id == followup_id).first()
        if not followup:
            return None

        now = get_current_datetime()
        # Audit entry
        audit = FollowupAudit(
            followup_id=followup.id,
            previous_scheduled_at=followup.scheduled_at,
            new_scheduled_at=followup.scheduled_at,
            previous_status=followup.status,
            new_status="Completed",
            reason=f"Call completed with outcome: {outcome}",
            changed_by=admin_id
        )
        db.add(audit)

        followup.status = "Completed"
        followup.completed_at = now
        followup.updated_at = now

        # Create Call History record linked to this followup
        call = CallHistory(
            customer_id=followup.customer_id,
            followup_id=followup.id,
            call_datetime=now,
            outcome=outcome,
            notes=notes,
            next_action=next_action,
            created_by=admin_id
        )
        db.add(call)

        # Update customer last contacted
        customer = db.query(Customer).filter(Customer.id == followup.customer_id).first()
        if customer:
            customer.last_contacted_at = now
            if outcome == "Converted":
                customer.status = "Converted"
            elif outcome == "Not Interested":
                customer.status = "Not Interested"
            elif outcome in ["Interested", "Call Back Required"]:
                customer.status = "Interested"

        # If a next follow-up is scheduled
        if schedule_next:
            new_f = Followup(
                customer_id=followup.customer_id,
                scheduled_at=schedule_next,
                status="Pending",
                priority="Medium",
                notes=f"Follow-up after call: {next_action or outcome}",
                created_by=admin_id
            )
            db.add(new_f)

        db.commit()
        db.refresh(followup)
        return followup
