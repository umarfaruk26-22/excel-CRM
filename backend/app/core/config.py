import os
from pathlib import Path
from pydantic_settings import BaseSettings

# Base directory for the backend/project
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

class Settings(BaseSettings):
    APP_NAME: str = "Customer Follow-up CRM"
    APP_ENV: str = "development"
    SECRET_KEY: str = "crm-secret-prod-token-94f83b2847a9e102f91c95e29c1b3f94"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    TIMEZONE: str = "Asia/Kolkata"
    REMINDER_ADVANCE_DAYS: int = 5

    # Database Configuration
    DB_TYPE: str = "sqlite"
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "customer_followup_crm"
    SQLITE_PATH: str = str(BASE_DIR / "database" / "crm.db")

    # Uploads & Storage Directories
    MAX_UPLOAD_SIZE_MB: int = 25
    UPLOAD_DIR: str = str(BASE_DIR / "storage" / "uploads")
    ERROR_REPORT_DIR: str = str(BASE_DIR / "storage" / "import-errors")
    EXPORT_DIR: str = str(BASE_DIR / "storage" / "exports")

    @property
    def DATABASE_URL(self) -> str:
        if self.DB_TYPE.lower() == "sqlite" or os.environ.get("DB_TYPE", "").lower() == "sqlite":
            return f"sqlite:///{self.SQLITE_PATH}"
        pwd = f":{self.DB_PASSWORD}" if self.DB_PASSWORD else ""
        return f"mysql+pymysql://{self.DB_USER}{pwd}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"

    @property
    def SERVER_URL_WITHOUT_DB(self) -> str:
        pwd = f":{self.DB_PASSWORD}" if self.DB_PASSWORD else ""
        return f"mysql+pymysql://{self.DB_USER}{pwd}@{self.DB_HOST}:{self.DB_PORT}?charset=utf8mb4"

    class Config:
        env_file = str(Path(__file__).resolve().parent.parent.parent.parent / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.ERROR_REPORT_DIR, exist_ok=True)
os.makedirs(settings.EXPORT_DIR, exist_ok=True)
