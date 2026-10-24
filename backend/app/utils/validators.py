import re
from typing import Optional, Any

def normalize_phone(phone: Optional[Any]) -> Optional[str]:
    """
    Normalizes phone/mobile numbers:
    - Strips all non-digit characters (+, -, space, parentheses)
    - If starts with 91 and has 12 digits, normalizes to 10 digits (India default)
    - Returns None if no digits found.
    """
    if phone is None:
        return None
    
    val_str = str(phone).strip()
    if not val_str or val_str.lower() in ["nan", "none", "null", "-"]:
        return None

    # Handle float representation from Excel like 9876543210.0
    if val_str.endswith(".0"):
        val_str = val_str[:-2]

    # Keep only digits
    digits = re.sub(r"\D", "", val_str)
    if not digits:
        return None

    # Common Indian prefix handling: if 12 digits and starts with 91
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]

    return digits

def normalize_email(email: Optional[Any]) -> Optional[str]:
    """Normalizes email to lowercased and stripped string, or None if invalid."""
    if email is None:
        return None
    val_str = str(email).strip().lower()
    if not val_str or val_str in ["nan", "none", "null", "-"]:
        return None
    # Basic email sanity check
    if "@" in val_str and "." in val_str.split("@")[-1]:
        return val_str
    return None

def sanitize_for_excel(val: Any) -> Any:
    """
    Prevents CSV / Excel Formula Injection (DDE injection).
    If a string starts with =, +, -, @, \t, \r, prefix with a single quote.
    """
    if val is None:
        return ""
    val_str = str(val)
    if val_str and val_str[0] in ["=", "+", "-", "@", "\t", "\r"]:
        return "'" + val_str
    return val_str
