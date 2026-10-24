import os

# Limit OpenBLAS and multi-threading libraries to 1 thread for shared hosting stability
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from backend.app.core.config import settings
from backend.app.db.database import init_tables

# Import API Routers
from backend.app.api.auth import router as auth_router
from backend.app.api.dashboard import router as dashboard_router
from backend.app.api.imports import router as imports_router
from backend.app.api.customers import router as customers_router
from backend.app.api.calls import router as calls_router
from backend.app.api.followups import router as followups_router
from backend.app.api.reports import router as reports_router
from backend.app.api.settings import router as settings_router

app = FastAPI(
    title=settings.APP_NAME,
    description="Full-stack Excel Customer Follow-up CRM with MySQL persistence and follow-up reminders.",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(imports_router)
app.include_router(customers_router)
app.include_router(calls_router)
app.include_router(followups_router)
app.include_router(reports_router)
app.include_router(settings_router)

# Mount Frontend Static Assets
BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
ASSETS_DIR = FRONTEND_DIR / "assets"
UPLOADS_DIR = BASE_DIR / "storage" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# Frontend Page Routes (Supporting both clean URLs and .html extensions)
@app.get("/")
def serve_dashboard():
    return FileResponse(FRONTEND_DIR / "index.html")

@app.get("/login")
@app.get("/login.html")
def serve_login():
    return FileResponse(FRONTEND_DIR / "login.html")

@app.get("/customers")
@app.get("/customers.html")
def serve_customers():
    return FileResponse(FRONTEND_DIR / "customers.html")

@app.get("/customer-details")
@app.get("/customer-details.html")
def serve_customer_details():
    return FileResponse(FRONTEND_DIR / "customer-details.html")

@app.get("/imports")
@app.get("/imports.html")
def serve_imports():
    return FileResponse(FRONTEND_DIR / "imports.html")

@app.get("/month-files")
@app.get("/month-files.html")
def serve_month_files():
    return FileResponse(FRONTEND_DIR / "month-files.html")

@app.get("/followups")
@app.get("/followups.html")
def serve_followups():
    return FileResponse(FRONTEND_DIR / "followups.html")

@app.get("/call-history")
@app.get("/call-history.html")
def serve_call_history():
    return FileResponse(FRONTEND_DIR / "call-history.html")

@app.get("/reports")
@app.get("/reports.html")
def serve_reports():
    return FileResponse(FRONTEND_DIR / "reports.html")

@app.get("/settings")
@app.get("/settings.html")
def serve_settings():
    return FileResponse(FRONTEND_DIR / "settings.html")

@app.on_event("startup")
def on_startup():
    print("[CRM] Initializing database and tables on startup...")
    init_tables()
    print("[CRM] Application started successfully.")

@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
