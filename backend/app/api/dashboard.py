from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.db.database import get_db
from backend.app.db.models import Admin
from backend.app.api.auth import get_current_admin
from backend.app.api.settings import get_system_setting
from backend.app.services.report_service import ReportService
from backend.app.services.followup_service import FollowupService

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/stats")
def get_stats(db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_admin)):
    return ReportService.get_dashboard_stats(db)

@router.get("/overview")
def get_overview(db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_admin)):
    advance_days = get_system_setting(db, "reminder_advance_days", default=settings.REMINDER_ADVANCE_DAYS)
    stats = ReportService.get_dashboard_stats(db)
    today = FollowupService.get_today_followups(db, page=1, per_page=10)
    overdue = FollowupService.get_overdue_followups(db, page=1, per_page=10)
    upcoming = FollowupService.get_upcoming_followups(db, page=1, per_page=10)
    due_soon = FollowupService.get_due_soon_followups(db, page=1, per_page=10, advance_days=advance_days)
    recent_imports = ReportService.get_recent_imports(db, limit=5)
    recent_calls = ReportService.get_recent_calls(db, limit=6)

    return {
        "stats": stats,
        "today_followups": today["items"],
        "overdue_followups": overdue["items"],
        "upcoming_followups": upcoming["items"],
        "due_soon_followups": due_soon["items"],
        "due_soon_count": due_soon["total"],
        "reminder_advance_days": advance_days,
        "recent_imports": recent_imports,
        "recent_calls": recent_calls
    }
