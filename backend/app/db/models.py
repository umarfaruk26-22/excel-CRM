from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date, 
    ForeignKey, JSON, Index
)
from sqlalchemy.orm import relationship
from backend.app.db.database import Base

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150), default="Administrator")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    import_files = relationship("ImportFile", back_populates="creator")
    calls_logged = relationship("CallHistory", back_populates="caller")
    followups_created = relationship("Followup", back_populates="creator")

class ImportFile(Base):
    __tablename__ = "import_files"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    storage_path = Column(String(500), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, index=True)
    data_period_start = Column(Date, nullable=True)
    data_period_end = Column(Date, nullable=True)
    import_month = Column(Integer, nullable=False) # 1 - 12
    import_year = Column(Integer, nullable=False)  # e.g. 2026
    worksheet_name = Column(String(100), nullable=True)
    total_rows = Column(Integer, default=0)
    imported_rows = Column(Integer, default=0)
    updated_rows = Column(Integer, default=0)
    duplicate_rows = Column(Integer, default=0)
    rejected_rows = Column(Integer, default=0)
    import_status = Column(String(50), default="Completed") # Completed, Partial, Failed, In Progress
    error_report_path = Column(String(500), nullable=True)
    created_by = Column(Integer, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    creator = relationship("Admin", back_populates="import_files")
    records = relationship("ImportFileRecord", back_populates="import_file", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_import_year_month", "import_year", "import_month"),
    )

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_code = Column(String(100), unique=True, nullable=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    normalized_mobile = Column(String(30), nullable=True, index=True)
    mobile = Column(String(50), nullable=True)
    alternate_phone = Column(String(50), nullable=True)
    normalized_email = Column(String(255), nullable=True, index=True)
    email = Column(String(255), nullable=True)
    company = Column(String(200), nullable=True, index=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True, index=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), default="India")
    category = Column(String(100), default="General", index=True)
    source = Column(String(100), default="Excel Import", index=True)
    status = Column(String(50), default="New", index=True) # New, Contacted, Follow-up Scheduled, Interested, Converted, Not Interested
    custom_fields = Column(JSON, nullable=True) # JSON store for unmapped Excel columns
    last_contacted_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    archived_at = Column(DateTime, nullable=True, index=True)

    # Relationships
    import_records = relationship("ImportFileRecord", back_populates="customer")
    calls = relationship("CallHistory", back_populates="customer", cascade="all, delete-orphan", order_by="desc(CallHistory.call_datetime)")
    followups = relationship("Followup", back_populates="customer", cascade="all, delete-orphan", order_by="desc(Followup.scheduled_at)")

class ImportFileRecord(Base):
    __tablename__ = "import_file_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    import_file_id = Column(Integer, ForeignKey("import_files.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    source_row_number = Column(Integer, nullable=False)
    row_status = Column(String(50), nullable=False) # Imported, Updated, Duplicate_Skipped, Rejected
    row_hash = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    import_file = relationship("ImportFile", back_populates="records")
    customer = relationship("Customer", back_populates="import_records")

class Followup(Base):
    __tablename__ = "followups"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    scheduled_at = Column(DateTime, nullable=False, index=True)
    status = Column(String(50), default="Pending", index=True) # Pending, Completed, Rescheduled, Cancelled
    priority = Column(String(30), default="Medium") # Low, Medium, High, Urgent
    notes = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    customer = relationship("Customer", back_populates="followups")
    creator = relationship("Admin", back_populates="followups_created")
    audits = relationship("FollowupAudit", back_populates="followup", cascade="all, delete-orphan", order_by="desc(FollowupAudit.changed_at)")
    resulting_calls = relationship("CallHistory", back_populates="followup")

    __table_args__ = (
        Index("idx_followup_status_scheduled", "status", "scheduled_at"),
    )

class FollowupAudit(Base):
    __tablename__ = "followup_audit"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    followup_id = Column(Integer, ForeignKey("followups.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_scheduled_at = Column(DateTime, nullable=True)
    new_scheduled_at = Column(DateTime, nullable=True)
    previous_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=False)
    reason = Column(Text, nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow)
    changed_by = Column(Integer, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    followup = relationship("Followup", back_populates="audits")
    changed_by_admin = relationship("Admin")

class CallHistory(Base):
    __tablename__ = "call_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    followup_id = Column(Integer, ForeignKey("followups.id", ondelete="SET NULL"), nullable=True, index=True)
    call_datetime = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    outcome = Column(String(100), nullable=False, index=True) # Interested, Not Interested, No Answer, Busy, Call Back Required, Converted, Wrong Number, Other
    notes = Column(Text, nullable=True)
    next_action = Column(String(255), nullable=True)
    created_by = Column(Integer, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="calls")
    followup = relationship("Followup", back_populates="resulting_calls")
    caller = relationship("Admin", back_populates="calls_logged")

class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    setting_key = Column(String(100), unique=True, nullable=False, index=True)
    setting_value = Column(Text, nullable=False)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
