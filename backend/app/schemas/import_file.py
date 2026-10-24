from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date

class UploadPreviewResponse(BaseModel):
    file_id: int
    original_filename: str
    stored_filename: str
    sheets: List[str]
    selected_sheet: str
    headers: List[str]
    preview_rows: List[Dict[str, Any]]
    total_preview_rows: int
    suggested_mapping: Dict[str, Optional[str]]

class ConfirmImportRequest(BaseModel):
    file_id: int
    sheet_name: str
    column_mapping: Dict[str, str] # e.g. {"name": "Client Name", "mobile": "Phone No"}
    custom_field_columns: Optional[List[str]] = []
    duplicate_handling: str = "skip" # "skip" | "update" | "import_new"
    data_period_start: Optional[date] = None
    data_period_end: Optional[date] = None

class ImportSummaryResponse(BaseModel):
    import_id: int
    original_filename: str
    uploaded_at: datetime
    total_rows: int
    imported_rows: int
    updated_rows: int
    duplicate_rows: int
    rejected_rows: int
    import_status: str
    error_report_url: Optional[str] = None

class ImportFileListResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int
    page: int
    per_page: int
    total_pages: int
