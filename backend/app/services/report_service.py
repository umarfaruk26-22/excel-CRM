import os
import pandas as pd
from datetime import datetime, date, time, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from backend.app.core.config import settings
from backend.app.db.models import Customer, Followup, CallHistory, ImportFile
from backend.app.utils.date_utils import get_current_datetime
from backend.app.utils.validators import sanitize_for_excel

class ReportService:
    @staticmethod
    def get_dashboard_stats(db: Session) -> Dict[str, Any]:
        """Calculates exact real-time statistics for the dashboard."""
        now = get_current_datetime()
        today_start = datetime.combine(now.date(), time.min)
        today_end = datetime.combine(now.date(), time.max)

        total_customers = db.query(Customer).filter(Customer.archived_at.is_(None)).count()
        total_files = db.query(ImportFile).count()

        today_followups = db.query(Followup).join(Customer)\
            .filter(Customer.archived_at.is_(None))\
            .filter(Followup.status == "Pending")\
            .filter(Followup.scheduled_at >= today_start, Followup.scheduled_at <= today_end)\
            .count()

        upcoming_followups = db.query(Followup).join(Customer)\
            .filter(Customer.archived_at.is_(None))\
            .filter(Followup.status == "Pending")\
            .filter(Followup.scheduled_at > today_end)\
            .count()

        overdue_followups = db.query(Followup).join(Customer)\
            .filter(Customer.archived_at.is_(None))\
            .filter(Followup.status == "Pending")\
            .filter(Followup.scheduled_at < now)\
            .count()

        completed_calls = db.query(CallHistory).count()

        pending_followups = db.query(Followup).join(Customer)\
            .filter(Customer.archived_at.is_(None))\
            .filter(Followup.status == "Pending")\
            .count()

        from backend.app.api.settings import get_system_setting
        advance_days = get_system_setting(db, "reminder_advance_days", default=settings.REMINDER_ADVANCE_DAYS)
        deadline = datetime.combine(now.date() + timedelta(days=advance_days), time.max)
        due_soon_followups = db.query(Followup).join(Customer)\
            .filter(Customer.archived_at.is_(None))\
            .filter(Followup.status == "Pending")\
            .filter(Followup.scheduled_at >= today_start, Followup.scheduled_at <= deadline)\
            .count()

        return {
            "total_customers": total_customers,
            "total_files": total_files,
            "today_followups_count": today_followups,
            "upcoming_followups_count": upcoming_followups,
            "overdue_followups_count": overdue_followups,
            "completed_calls_count": completed_calls,
            "pending_followups_count": pending_followups,
            "due_soon_followups_count": due_soon_followups,
            "reminder_advance_days": advance_days
        }

    @staticmethod
    def get_call_outcomes_summary(db: Session, date_from: Optional[date] = None, date_to: Optional[date] = None) -> List[Dict[str, Any]]:
        """Returns count of calls grouped by outcome."""
        query = db.query(CallHistory.outcome, func.count(CallHistory.id).label("count"))
        if date_from:
            query = query.filter(CallHistory.call_datetime >= datetime.combine(date_from, time.min))
        if date_to:
            query = query.filter(CallHistory.call_datetime <= datetime.combine(date_to, time.max))

        results = query.group_by(CallHistory.outcome).all()
        return [{"outcome": r[0], "count": r[1]} for r in results]

    @staticmethod
    def get_monthly_customers_trend(db: Session) -> List[Dict[str, Any]]:
        """Returns customer registrations grouped by Year-Month."""
        if "sqlite" in settings.DATABASE_URL:
            results = db.query(
                func.strftime("%Y", Customer.created_at).label("year"),
                func.strftime("%m", Customer.created_at).label("month"),
                func.count(Customer.id).label("count")
            ).filter(Customer.archived_at.is_(None))\
             .group_by("year", "month")\
             .order_by("year", "month")\
             .limit(12).all()

            return [
                {
                    "year": int(r[0]) if r[0] else 0,
                    "month": int(r[1]) if r[1] else 0,
                    "label": f"{r[0]}-{r[1]}",
                    "count": r[2]
                }
                for r in results
            ]

        results = db.query(
            func.year(Customer.created_at).label("year"),
            func.month(Customer.created_at).label("month"),
            func.count(Customer.id).label("count")
        ).filter(Customer.archived_at.is_(None))\
         .group_by("year", "month")\
         .order_by("year", "month")\
         .limit(12).all()

        return [
            {
                "year": r[0],
                "month": r[1],
                "label": f"{r[0]}-{r[1]:02d}",
                "count": r[2]
            }
            for r in results
        ]

    @staticmethod
    def get_recent_calls(db: Session, limit: int = 8) -> List[Dict[str, Any]]:
        """Fetches latest call activities."""
        calls = db.query(CallHistory).order_by(desc(CallHistory.call_datetime)).limit(limit).all()
        items = []
        for c in calls:
            items.append({
                "id": c.id,
                "customer_id": c.customer_id,
                "customer_name": c.customer.name if c.customer else "Unknown",
                "customer_mobile": c.customer.mobile if c.customer else "",
                "call_datetime": c.call_datetime,
                "outcome": c.outcome,
                "notes": c.notes,
                "next_action": c.next_action,
                "caller": c.caller.full_name if c.caller else "Admin"
            })
        return items

    @staticmethod
    def get_recent_imports(db: Session, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetches recent imports."""
        files = db.query(ImportFile).order_by(desc(ImportFile.uploaded_at)).limit(limit).all()
        items = []
        for f in files:
            items.append({
                "id": f.id,
                "original_filename": f.original_filename,
                "uploaded_at": f.uploaded_at,
                "import_month": f.import_month,
                "import_year": f.import_year,
                "total_rows": f.total_rows,
                "imported_rows": f.imported_rows,
                "updated_rows": f.updated_rows,
                "duplicate_rows": f.duplicate_rows,
                "rejected_rows": f.rejected_rows,
                "status": f.import_status
            })
        return items
