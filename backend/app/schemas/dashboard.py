from pydantic import BaseModel
from typing import List, Dict, Any
from backend.app.schemas.followup import FollowupOut

class DashboardStats(BaseModel):
    total_customers: int
    total_files: int
    today_followups_count: int
    upcoming_followups_count: int
    overdue_followups_count: int
    completed_calls_count: int
    pending_followups_count: int

class DashboardResponse(BaseModel):
    stats: DashboardStats
    today_followups: List[FollowupOut]
    overdue_followups: List[FollowupOut]
    upcoming_followups: List[FollowupOut]
    recent_imports: List[Dict[str, Any]]
    recent_calls: List[Dict[str, Any]]
