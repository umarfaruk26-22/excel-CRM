from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from backend.app.db.database import get_db
from backend.app.db.models import Admin
from backend.app.api.auth import get_current_admin
from backend.app.services.report_service import ReportService

router = APIRouter(prefix="/api/reports", tags=["Reports"])

@router.get("/summary")
def get_summary(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    return ReportService.get_dashboard_stats(db)

@router.get("/outcomes")
def get_call_outcomes(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    return ReportService.get_call_outcomes_summary(db, date_from, date_to)

@router.get("/growth")
def get_growth_trend(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    return ReportService.get_monthly_customers_trend(db)
