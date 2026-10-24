from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class CallCreate(BaseModel):
    call_datetime: Optional[datetime] = None
    outcome: str = Field(..., description="Interested, Not Interested, No Answer, Busy, Call Back Required, Converted, Wrong Number, Other")
    notes: Optional[str] = None
    next_action: Optional[str] = None
    followup_id: Optional[int] = None
    
    # Optional next followup scheduling in one go
    schedule_next_followup: Optional[datetime] = None
    next_followup_priority: Optional[str] = "Medium"
    next_followup_notes: Optional[str] = None

class CallOut(BaseModel):
    id: int
    customer_id: int
    customer_name: Optional[str] = None
    customer_mobile: Optional[str] = None
    customer_company: Optional[str] = None
    source_file: Optional[str] = None
    followup_id: Optional[int] = None
    call_datetime: datetime
    outcome: str
    notes: Optional[str] = None
    next_action: Optional[str] = None
    created_by_name: Optional[str] = "Administrator"
    created_at: datetime

    class Config:
        from_attributes = True

class CallListResponse(BaseModel):
    items: List[CallOut]
    total: int
    page: int
    per_page: int
    total_pages: int
    stats: Optional[dict] = None

