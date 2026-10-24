import os
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc

from backend.app.core.config import settings
from backend.app.db.models import Customer, CallHistory, Followup, ImportFileRecord, ImportFile
from backend.app.schemas.customer import CustomerCreate, CustomerUpdate
from backend.app.utils.validators import normalize_phone, normalize_email, sanitize_for_excel

class CustomerService:
    @staticmethod
    def get_customers(
        db: Session,
        page: int = 1,
        per_page: int = 25,
        search: Optional[str] = None,
        city: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
        import_file_id: Optional[int] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """Fetches paginated, filtered, and sorted customer records."""
        query = db.query(Customer).filter(Customer.archived_at.is_(None))

        # Search across name, mobile, email, company, customer_code
        if search and search.strip():
            s = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Customer.name.ilike(s),
                    Customer.mobile.ilike(s),
                    Customer.normalized_mobile.ilike(s),
                    Customer.email.ilike(s),
                    Customer.company.ilike(s),
                    Customer.customer_code.ilike(s),
                    Customer.city.ilike(s)
                )
            )

        if city and city.strip():
            query = query.filter(Customer.city == city.strip())

        if status and status.strip():
            query = query.filter(Customer.status == status.strip())

        if category and category.strip():
            query = query.filter(Customer.category == category.strip())

        if import_file_id:
            query = query.join(ImportFileRecord, ImportFileRecord.customer_id == Customer.id)\
                         .filter(ImportFileRecord.import_file_id == import_file_id)\
                         .distinct()

        # Sorting
        sort_col = getattr(Customer, sort_by, Customer.created_at)
        if sort_order.lower() == "asc":
            query = query.order_by(asc(sort_col))
        else:
            query = query.order_by(desc(sort_col))

        total = query.count()
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1
        items = query.offset((page - 1) * per_page).limit(per_page).all()

        # Augment with total_calls, next_followup, and import file details
        customer_items = []
        for c in items:
            total_calls = len(c.calls)
            pending_f = next((f for f in c.followups if f.status == "Pending"), None)
            primary_rec = next((r for r in c.import_records if r.import_file), None) if c.import_records else None
            import_fid = primary_rec.import_file_id if primary_rec else None
            import_fname = primary_rec.import_file.original_filename if (primary_rec and primary_rec.import_file) else None

            customer_dict = {
                "id": c.id,
                "customer_code": c.customer_code,
                "name": c.name,
                "mobile": c.mobile,
                "normalized_mobile": c.normalized_mobile,
                "alternate_phone": c.alternate_phone,
                "email": c.email,
                "normalized_email": c.normalized_email,
                "company": c.company,
                "address": c.address,
                "city": c.city,
                "state": c.state,
                "country": c.country,
                "category": c.category,
                "source": c.source,
                "status": c.status,
                "custom_fields": c.custom_fields,
                "last_contacted_at": c.last_contacted_at,
                "created_at": c.created_at,
                "updated_at": c.updated_at,
                "archived_at": c.archived_at,
                "total_calls": total_calls,
                "next_followup_date": pending_f.scheduled_at if pending_f else None,
                "import_file_id": import_fid,
                "import_filename": import_fname
            }
            customer_items.append(customer_dict)

        return {
            "items": customer_items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages
        }

    @staticmethod
    def get_customer_by_id(db: Session, customer_id: int) -> Optional[Customer]:
        return db.query(Customer).filter(Customer.id == customer_id, Customer.archived_at.is_(None)).first()

    @staticmethod
    def create_customer(db: Session, data: CustomerCreate) -> Customer:
        customer = Customer(
            customer_code=data.customer_code,
            name=data.name,
            mobile=data.mobile,
            normalized_mobile=normalize_phone(data.mobile),
            alternate_phone=data.alternate_phone,
            email=data.email,
            normalized_email=normalize_email(data.email),
            company=data.company,
            address=data.address,
            city=data.city,
            state=data.state,
            country=data.country or "India",
            category=data.category or "General",
            source=data.source or "Manual Entry",
            status=data.status or "New",
            custom_fields=data.custom_fields
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        return customer

    @staticmethod
    def update_customer(db: Session, customer_id: int, data: CustomerUpdate) -> Optional[Customer]:
        customer = CustomerService.get_customer_by_id(db, customer_id)
        if not customer:
            return None

        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            if key == "mobile":
                customer.mobile = value
                customer.normalized_mobile = normalize_phone(value)
            elif key == "email":
                customer.email = value
                customer.normalized_email = normalize_email(value)
            elif key == "custom_fields" and value is not None:
                existing_cf = customer.custom_fields or {}
                existing_cf.update(value)
                customer.custom_fields = existing_cf
            else:
                setattr(customer, key, value)

        customer.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(customer)
        return customer

    @staticmethod
    def export_customers_excel(
        db: Session,
        search: Optional[str] = None,
        city: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
        import_file_id: Optional[int] = None
    ) -> str:
        """Generates an Excel export of filtered customers with sanitization."""
        # Query without pagination limit
        result = CustomerService.get_customers(
            db=db, page=1, per_page=100000,
            search=search, city=city, status=status,
            category=category, import_file_id=import_file_id
        )

        rows = []
        for c in result["items"]:
            rows.append({
                "Customer Code": sanitize_for_excel(c.get("customer_code")),
                "Customer Name": sanitize_for_excel(c.get("name")),
                "Mobile": sanitize_for_excel(c.get("mobile")),
                "Alternate Phone": sanitize_for_excel(c.get("alternate_phone")),
                "Email": sanitize_for_excel(c.get("email")),
                "Company": sanitize_for_excel(c.get("company")),
                "City": sanitize_for_excel(c.get("city")),
                "State": sanitize_for_excel(c.get("state")),
                "Category": sanitize_for_excel(c.get("category")),
                "Status": sanitize_for_excel(c.get("status")),
                "Source": sanitize_for_excel(c.get("source")),
                "Total Calls": c.get("total_calls"),
                "Last Contacted": str(c.get("last_contacted_at")) if c.get("last_contacted_at") else "",
                "Next Follow-up": str(c.get("next_followup_date")) if c.get("next_followup_date") else "",
                "Created Date": str(c.get("created_at"))
            })

        df = pd.DataFrame(rows)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        export_filename = f"customers_export_{ts}.xlsx"
        export_path = os.path.join(settings.EXPORT_DIR, export_filename)
        df.to_excel(export_path, index=False)
        return export_path
