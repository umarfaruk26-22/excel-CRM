import os
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional

# Fuzzy matching keywords for auto-column mapping
MAPPING_KEYWORDS = {
    "name": ["name", "customer name", "client name", "contact person", "full name", "party name", "customer", "lead name"],
    "customer_code": ["customer code", "cust code", "customer id", "client id", "account id", "code", "id"],
    "mobile": ["mobile", "mobile number", "mobile no", "phone", "phone number", "contact", "contact no", "cell", "whatsapp", "primary phone"],
    "alternate_phone": ["alternate phone", "alt phone", "alt mobile", "alternate number", "secondary phone", "phone 2", "other phone"],
    "email": ["email", "e-mail", "mail id", "email id", "email address", "contact email"],
    "company": ["company", "company name", "organization", "firm", "business", "business name", "enterprise"],
    "address": ["address", "street", "street address", "location", "full address"],
    "city": ["city", "town", "district"],
    "state": ["state", "province"],
    "country": ["country", "nation"],
    "category": ["category", "customer category", "type", "client type", "segment"],
    "source": ["source", "lead source", "reference", "campaign"],
    "status": ["status", "lead status", "customer status"],
    "notes": ["notes", "remarks", "comments", "description"]
}

class ExcelService:
    @staticmethod
    def get_sheets(file_path: str) -> List[str]:
        """Returns list of sheet names from .xlsx or .xls file."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".xlsx":
            import openpyxl
            wb = openpyxl.load_workbook(file_path, read_only=True)
            sheets = wb.sheetnames
            wb.close()
            return sheets
        elif ext == ".xls":
            import xlrd
            wb = xlrd.open_workbook(file_path, on_demand=True)
            sheets = wb.sheet_names()
            wb.release_resources()
            return sheets
        else:
            raise ValueError(f"Unsupported file format: {ext}. Only .xlsx and .xls are supported.")

    @staticmethod
    def read_sheet_preview(file_path: str, sheet_name: Optional[str] = None, preview_limit: int = 10) -> Tuple[List[str], List[Dict[str, Any]], Dict[str, Optional[str]]]:
        """
        Reads headers and top preview rows from sheet.
        Returns (headers, preview_rows, suggested_mapping).
        """
        ext = os.path.splitext(file_path)[1].lower()
        engine = "openpyxl" if ext == ".xlsx" else "xlrd"

        # Read using pandas with data_only logic (no formula execution)
        df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=preview_limit, engine=engine)
        
        # Clean headers: stringify, strip
        headers = [str(col).strip() for col in df.columns]

        # Convert preview records to dict with None for NaN
        preview_rows = []
        for _, row in df.iterrows():
            row_dict = {}
            for h, col in zip(headers, df.columns):
                val = row[col]
                if pd.isna(val):
                    row_dict[h] = None
                else:
                    row_dict[h] = str(val) if not isinstance(val, (int, float, bool)) else val
            preview_rows.append(row_dict)

        # Generate smart suggested mapping
        suggested_mapping = ExcelService.suggest_column_mapping(headers)

        return headers, preview_rows, suggested_mapping

    @staticmethod
    def suggest_column_mapping(headers: List[str]) -> Dict[str, Optional[str]]:
        """Matches sheet headers against standard CRM fields."""
        suggestions: Dict[str, Optional[str]] = {field: None for field in MAPPING_KEYWORDS}
        used_headers = set()

        for crm_field, keywords in MAPPING_KEYWORDS.items():
            for h in headers:
                if h in used_headers:
                    continue
                h_norm = h.lower().strip().replace("_", " ").replace("-", " ")
                # Exact or substring match
                if any(kw == h_norm or kw in h_norm for kw in keywords):
                    suggestions[crm_field] = h
                    used_headers.add(h)
                    break

        return suggestions
