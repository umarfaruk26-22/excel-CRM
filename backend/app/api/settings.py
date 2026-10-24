import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from backend.app.core.config import settings
from backend.app.db.database import get_db
from backend.app.db.models import Admin, SystemSetting, Customer, Followup, CallHistory, ImportFile
from backend.app.api.auth import get_current_admin

router = APIRouter(prefix="/api/settings", tags=["Settings"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
UPLOADS_DIR = BASE_DIR / "storage" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

class UpdateSettingsRequest(BaseModel):
    reminder_advance_days: int = Field(5, ge=1, le=60, description="Number of days in advance to surface follow-up reminders")

class FirmSettingsRequest(BaseModel):
    firm_name: str = Field(..., min_length=1, max_length=200, description="Company or firm name")
    firm_tagline: Optional[str] = Field(None, max_length=255, description="Business tagline or slogan")
    firm_phone: Optional[str] = Field(None, max_length=50, description="Contact phone")
    firm_email: Optional[str] = Field(None, max_length=100, description="Contact email")
    firm_address: Optional[str] = Field(None, description="Physical office or warehouse address")
    firm_gst: Optional[str] = Field(None, max_length=50, description="GST / Tax ID number")
    firm_website: Optional[str] = Field(None, max_length=255, description="Website URL")
    theme_color: Optional[str] = Field("#2563eb", max_length=20, description="Brand accent color hex")
    currency_symbol: Optional[str] = Field("₹", max_length=10, description="Default currency symbol")
    date_format: Optional[str] = Field("DD/MM/YYYY", max_length=20, description="Date display format")
    default_followup_days: Optional[int] = Field(7, ge=1, le=180, description="Default days for next follow-up")
    reminder_advance_days: Optional[int] = Field(5, ge=1, le=60, description="Days in advance to show reminder alerts")

def get_system_setting(db: Session, key: str, default: any = None) -> any:
    """Helper to retrieve setting value with fallback to default."""
    row = db.query(SystemSetting).filter(SystemSetting.setting_key == key).first()
    if row and row.setting_value is not None:
        if isinstance(default, int):
            try:
                return int(row.setting_value)
            except ValueError:
                return default
        return row.setting_value
    return default

def set_system_setting(db: Session, key: str, value: any, description: Optional[str] = None):
    """Helper to upsert a system setting."""
    row = db.query(SystemSetting).filter(SystemSetting.setting_key == key).first()
    val_str = "" if value is None else str(value)
    if row:
        row.setting_value = val_str
        if description:
            row.description = description
    else:
        row = SystemSetting(
            setting_key=key,
            setting_value=val_str,
            description=description or f"Setting for {key}"
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row

def get_firm_profile(db: Session) -> dict:
    """Helper to fetch complete firm profile and branding configuration."""
    return {
        "firm_name": get_system_setting(db, "firm_name", default="CRM Follow-up"),
        "firm_tagline": get_system_setting(db, "firm_tagline", default="Customer Follow-up & Sales CRM"),
        "firm_phone": get_system_setting(db, "firm_phone", default=""),
        "firm_email": get_system_setting(db, "firm_email", default=""),
        "firm_address": get_system_setting(db, "firm_address", default=""),
        "firm_gst": get_system_setting(db, "firm_gst", default=""),
        "firm_website": get_system_setting(db, "firm_website", default=""),
        "firm_logo": get_system_setting(db, "firm_logo", default=""),
        "theme_color": get_system_setting(db, "theme_color", default="#2563eb"),
        "currency_symbol": get_system_setting(db, "currency_symbol", default="₹"),
        "date_format": get_system_setting(db, "date_format", default="DD/MM/YYYY"),
        "default_followup_days": get_system_setting(db, "default_followup_days", default=7),
        "reminder_advance_days": get_system_setting(db, "reminder_advance_days", default=5)
    }

@router.get("/public")
def get_public_settings(db: Session = Depends(get_db)):
    """Unauthenticated public endpoint for sidebar, login, and header branding."""
    firm = get_firm_profile(db)
    return {
        "firm_name": firm["firm_name"],
        "firm_tagline": firm["firm_tagline"],
        "firm_logo": firm["firm_logo"],
        "firm_phone": firm["firm_phone"],
        "firm_email": firm["firm_email"],
        "firm_website": firm["firm_website"],
        "theme_color": firm["theme_color"],
        "currency_symbol": firm["currency_symbol"],
        "date_format": firm["date_format"]
    }

@router.get("")
def get_settings(db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_admin)):
    advance_days = get_system_setting(db, "reminder_advance_days", default=settings.REMINDER_ADVANCE_DAYS)
    firm = get_firm_profile(db)
    return {
        "reminder_advance_days": advance_days,
        "timezone": settings.TIMEZONE,
        "max_upload_size_mb": settings.MAX_UPLOAD_SIZE_MB,
        "db_name": settings.DB_NAME,
        "app_name": settings.APP_NAME,
        **firm
    }

@router.put("")
def update_settings(
    req: UpdateSettingsRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    set_system_setting(
        db,
        key="reminder_advance_days",
        value=req.reminder_advance_days,
        description="Number of days in advance to display follow-up reminder alerts"
    )
    return {
        "message": f"Settings saved: Reminders will now appear {req.reminder_advance_days} days in advance.",
        "reminder_advance_days": req.reminder_advance_days
    }

@router.put("/firm")
def update_firm_profile(
    req: FirmSettingsRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    set_system_setting(db, "firm_name", req.firm_name.strip(), "Company / Firm Name")
    set_system_setting(db, "firm_tagline", req.firm_tagline.strip() if req.firm_tagline else "", "Business Tagline")
    set_system_setting(db, "firm_phone", req.firm_phone.strip() if req.firm_phone else "", "Firm Phone")
    set_system_setting(db, "firm_email", req.firm_email.strip() if req.firm_email else "", "Firm Email")
    set_system_setting(db, "firm_address", req.firm_address.strip() if req.firm_address else "", "Firm Address")
    set_system_setting(db, "firm_gst", req.firm_gst.strip() if req.firm_gst else "", "Firm GST / Registration")
    set_system_setting(db, "firm_website", req.firm_website.strip() if req.firm_website else "", "Firm Website URL")
    
    if req.theme_color:
        set_system_setting(db, "theme_color", req.theme_color.strip(), "Brand Accent Theme Color")
    if req.currency_symbol:
        set_system_setting(db, "currency_symbol", req.currency_symbol.strip(), "Currency Symbol")
    if req.date_format:
        set_system_setting(db, "date_format", req.date_format.strip(), "Date Format Preference")
    if req.default_followup_days:
        set_system_setting(db, "default_followup_days", req.default_followup_days, "Default Follow-up Days Interval")
    if req.reminder_advance_days:
        set_system_setting(db, "reminder_advance_days", req.reminder_advance_days, "Reminder Advance Notice Days")

    return {
        "message": "Firm profile, branding, and system preferences updated successfully!",
        "firm": get_firm_profile(db)
    }

@router.post("/firm/logo")
async def upload_firm_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    # Validate extension
    ext = Path(file.filename).suffix.lower()
    if ext not in [".png", ".jpg", ".jpeg", ".webp", ".svg"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image format. Supported formats: PNG, JPG, JPEG, WebP, SVG."
        )

    # Save file
    target_filename = f"firm_logo{ext}"
    target_path = UPLOADS_DIR / target_filename
    contents = await file.read()
    
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Logo file size must be less than 5 MB."
        )

    with open(target_path, "wb") as f:
        f.write(contents)

    logo_url = f"/uploads/{target_filename}"
    set_system_setting(db, "firm_logo", logo_url, "Firm Logo Path")

    return {
        "message": "Firm logo uploaded successfully!",
        "logo_url": logo_url
    }

@router.delete("/firm/logo")
def delete_firm_logo(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    current_logo = get_system_setting(db, "firm_logo", "")
    if current_logo and current_logo.startswith("/uploads/"):
        filename = Path(current_logo).name
        file_path = UPLOADS_DIR / filename
        if file_path.exists():
            try:
                os.remove(file_path)
            except Exception:
                pass

    set_system_setting(db, "firm_logo", "", "Firm Logo Path")
    return {"message": "Firm logo removed successfully."}

@router.post("/reset-branding")
def reset_branding(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Resets all firm profile and branding configuration back to factory defaults."""
    set_system_setting(db, "firm_name", "CRM Follow-up", "Company / Firm Name")
    set_system_setting(db, "firm_tagline", "Customer Follow-up & Sales CRM", "Business Tagline")
    set_system_setting(db, "firm_phone", "", "Firm Phone")
    set_system_setting(db, "firm_email", "", "Firm Email")
    set_system_setting(db, "firm_address", "", "Firm Address")
    set_system_setting(db, "firm_gst", "", "Firm GST / Registration")
    set_system_setting(db, "firm_website", "", "Firm Website URL")
    set_system_setting(db, "theme_color", "#2563eb", "Brand Accent Theme Color")
    set_system_setting(db, "currency_symbol", "₹", "Currency Symbol")
    set_system_setting(db, "date_format", "DD/MM/YYYY", "Date Format Preference")
    set_system_setting(db, "default_followup_days", 7, "Default Follow-up Days Interval")
    set_system_setting(db, "reminder_advance_days", 5, "Reminder Advance Notice Days")

    current_logo = get_system_setting(db, "firm_logo", "")
    if current_logo and current_logo.startswith("/uploads/"):
        filename = Path(current_logo).name
        file_path = UPLOADS_DIR / filename
        if file_path.exists():
            try:
                os.remove(file_path)
            except Exception:
                pass
    set_system_setting(db, "firm_logo", "", "Firm Logo Path")

    return {
        "message": "Branding and system preferences reset to defaults.",
        "firm": get_firm_profile(db)
    }

@router.get("/backup/export")
def export_database_backup(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Dumps all key CRM entities (Customers, Followups, Call History, Settings) as structured JSON for easy backup."""
    from datetime import datetime
    
    customers_data = []
    for c in db.query(Customer).all():
        customers_data.append({
            "id": c.id,
            "customer_code": c.customer_code,
            "name": c.name,
            "mobile": c.mobile,
            "email": c.email,
            "company_name": c.company_name,
            "city": c.city,
            "state": c.state,
            "current_status": c.current_status,
            "source": c.source,
            "custom_fields": c.custom_fields,
            "created_at": c.created_at.isoformat() if c.created_at else None
        })

    followups_data = []
    for f in db.query(Followup).all():
        followups_data.append({
            "id": f.id,
            "customer_id": f.customer_id,
            "scheduled_at": f.scheduled_at.isoformat() if f.scheduled_at else None,
            "status": f.status,
            "priority": f.priority,
            "notes": f.notes,
            "created_at": f.created_at.isoformat() if f.created_at else None
        })

    calls_data = []
    for cl in db.query(CallHistory).all():
        calls_data.append({
            "id": cl.id,
            "customer_id": cl.customer_id,
            "call_datetime": cl.call_datetime.isoformat() if cl.call_datetime else None,
            "outcome": cl.outcome,
            "notes": cl.notes,
            "next_action": cl.next_action
        })

    return {
        "backup_timestamp": datetime.utcnow().isoformat(),
        "exported_by": current_admin.email,
        "firm_profile": get_firm_profile(db),
        "total_customers": len(customers_data),
        "total_followups": len(followups_data),
        "total_calls": len(calls_data),
        "customers": customers_data,
        "followups": followups_data,
        "calls": calls_data
    }
