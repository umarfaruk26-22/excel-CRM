from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from datetime import timedelta

from backend.app.db.database import get_db
from backend.app.db.models import Admin
from backend.app.core.security import verify_password, get_password_hash, create_access_token, decode_access_token
from backend.app.core.rate_limiter import login_limiter
from backend.app.core.config import settings
from backend.app.schemas.auth import LoginRequest, TokenResponse, AdminOut, UpdateProfileRequest, ChangePasswordRequest

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

def get_current_admin(request: Request, db: Session = Depends(get_db)) -> Admin:
    """Dependency: extracts and verifies JWT from Bearer Authorization header or HTTP-only cookie."""
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        admin_id = int(payload.get("sub"))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token subject.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    admin = db.query(Admin).filter(Admin.id == admin_id, Admin.is_active == True).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or disabled.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return admin

@router.post("/login", response_model=TokenResponse)
def login(login_data: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{client_ip}:{login_data.email}"

    # Rate limiting check
    allowed, retry_after = login_limiter.is_allowed(rate_key)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Please try again after {retry_after} seconds."
        )

    admin = db.query(Admin).filter(Admin.email == login_data.email.strip().lower()).first()
    if not admin or not verify_password(login_data.password, admin.password_hash):
        login_limiter.record_attempt(rate_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is currently deactivated."
        )

    # Success: reset limiter
    login_limiter.reset(rate_key)

    expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token({"sub": str(admin.id), "email": admin.email}, expires_delta=expires)

    # Set HTTP-only Cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False # Set to True in production with HTTPS
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "admin": admin
    }

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}

@router.get("/me", response_model=AdminOut)
def get_me(admin: Admin = Depends(get_current_admin)):
    return admin

@router.put("/profile", response_model=AdminOut)
def update_profile(
    req: UpdateProfileRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    email_clean = req.email.strip().lower()
    # Check if email is already taken by another admin
    existing = db.query(Admin).filter(Admin.email == email_clean, Admin.id != admin.id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    admin.full_name = req.full_name.strip()
    admin.email = email_clean
    db.commit()
    db.refresh(admin)
    return admin

@router.put("/change-password")
def change_password(
    req: ChangePasswordRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    if not verify_password(req.current_password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect. Please verify and try again."
        )

    if len(req.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters long."
        )

    admin.password_hash = get_password_hash(req.new_password)
    db.commit()
    return {"message": "Admin password changed successfully! You can now use your new password."}
