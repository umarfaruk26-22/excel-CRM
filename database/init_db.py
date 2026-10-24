import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.app.db.database import init_tables

def main():
    print("[Database] Initializing customer_followup_crm database and tables...")
    init_tables()
    print("[Database] Initialization complete!")

if __name__ == "__main__":
    main()
