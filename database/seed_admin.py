import sys
import argparse
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.app.db.database import SessionLocal, init_tables
from backend.app.db.models import Admin
from backend.app.core.security import get_password_hash

def seed_admin(email: str = "admin@crm.local", password: str = "Admin@12345", full_name: str = "CRM Administrator"):
    init_tables()
    db = SessionLocal()
    try:
        existing = db.query(Admin).filter(Admin.email == email).first()
        if existing:
            print(f"[Seed Admin] Admin with email '{email}' already exists. Updating password...")
            existing.password_hash = get_password_hash(password)
            existing.full_name = full_name
            existing.is_active = True
            db.commit()
            print(f"[Seed Admin] Successfully updated admin account for '{email}'.")
        else:
            admin = Admin(
                email=email,
                password_hash=get_password_hash(password),
                full_name=full_name,
                is_active=True
            )
            db.add(admin)
            db.commit()
            print(f"[Seed Admin] Created default admin account successfully!")
            print(f"            Email: {email}")
            print(f"            Password: {password}")
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create or update CRM admin account")
    parser.add_argument("--email", default="admin@crm.local", help="Admin email address")
    parser.add_argument("--password", default="Admin@12345", help="Admin password")
    parser.add_argument("--name", default="CRM Administrator", help="Admin full name")
    args = parser.parse_args()

    seed_admin(email=args.email, password=args.password, full_name=args.name)
