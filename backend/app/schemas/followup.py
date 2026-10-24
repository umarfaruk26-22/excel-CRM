from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class FollowupBase(BaseModel):
    customer_id: int
    scheduled_at: datetime
    priority: Optional[str] = "Medium" # Low, Medium, High, Urgent
    notes: Optional[str] = None

class FollowupCreate(FollowupBase):
    pass

class FollowupReschedule(BaseModel):
    new_scheduled_at: datetime
    reason: Optional[str] = "Rescheduled by user"

class FollowupComplete(BaseModel):
    outcome: Optional[str] = "Interested"
    notes: Optional[str] = None
    next_action: Optional[str] = None
    schedule_next_followup: Optional[datetime] = None

class FollowupOut(BaseModel):
    id: int
    customer_id: int
    customer_name: Optional[str] = None
    customer_mobile: Optional[str] = None
    customer_company: Optional[str] = None
    customer_city: Optional[str] = None
    scheduled_at: datetime
    status: str
    priority: str
    notes: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    is_overdue: bool = False
    overdue_text: Optional[str] = None
    is_due_soon: Optional[bool] = False
    days_until_due: Optional[int] = None
    due_soon_text: Optional[str] = None

    class Config:
        from_attributes = True

class FollowupListResponse(BaseModel):
    items: List[FollowupOut]
    total: int
    page: int
    per_page: int
    total_pages: int
