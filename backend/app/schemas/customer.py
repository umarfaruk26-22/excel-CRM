from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class CustomerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    customer_code: Optional[str] = None
    mobile: Optional[str] = None
    alternate_phone: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "India"
    category: Optional[str] = "General"
    source: Optional[str] = "Manual Entry"
    status: Optional[str] = "New"
    custom_fields: Optional[Dict[str, Any]] = None

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    customer_code: Optional[str] = None
    mobile: Optional[str] = None
    alternate_phone: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    category: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None

class CustomerOut(CustomerBase):
    id: int
    normalized_mobile: Optional[str] = None
    normalized_email: Optional[str] = None
    last_contacted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None
    
    # Extra calculated fields
    total_calls: Optional[int] = 0
    next_followup_date: Optional[datetime] = None
    import_file_id: Optional[int] = None
    import_filename: Optional[str] = None

    class Config:
        from_attributes = True

class CustomerListResponse(BaseModel):
    items: List[CustomerOut]
    total: int
    page: int
    per_page: int
    total_pages: int
