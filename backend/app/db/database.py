from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.app.core.config import settings

# Base Declarative Model
Base = declarative_base()

is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# SQLAlchemy Engine
if is_sqlite:
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=10,
        max_overflow=20,
        echo=False
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """FastAPI Dependency for database session management."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def ensure_database_exists():
    """Ensures database directory and file/database exists."""
    if is_sqlite:
        import os
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        return

    try:
        import pymysql
        conn = pymysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            charset='utf8mb4'
        )
        with conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{settings.DB_NAME}` "
                f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
        conn.commit()
        conn.close()
        print(f"[Database] Confirmed database `{settings.DB_NAME}` exists.")
    except Exception as e:
        print(f"[Database Warning] Could not verify/create database via pymysql: {e}")

def init_tables():
    """Initializes all table definitions."""
    ensure_database_exists()
    from backend.app.db import models  # Ensure all models are imported
    Base.metadata.create_all(bind=engine)
    print("[Database] All tables initialized successfully.")
