"""
Seed administrative user.
Run: python backend/scripts/seed_admin.py
"""
import sys
from pathlib import Path

# Add project roots to path
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

_WORKSPACE = _BACKEND.parent
if str(_WORKSPACE) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE))

from sqlalchemy import select
from database.connection import SyncSessionFactory
from database.models import User, Port
from auth.password import hash_password

def seed_admin():
    session = SyncSessionFactory()
    try:
        # Get or create Port
        port = session.execute(select(Port).where(Port.code == "INMAA")).scalar_one_or_none()
        if not port:
            port = Port(
                name="Chennai",
                code="INMAA",
                country="India",
                config_json={"timezone": "Asia/Kolkata", "currency": "INR"}
            )
            session.add(port)
            session.flush()

        email = "admin@baos.ai"
        user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if not user:
            user = User(
                email=email,
                password_hash=hash_password("admin123"),
                full_name="Port Administrator",
                company="Chennai Port Authority",
                port_id=port.id,
                role="admin",
                is_active=True
            )
            session.add(user)
            print(f"[seed_admin] Created admin user: {email}")
        else:
            user.password_hash = hash_password("admin123")
            user.role = "admin"
            user.is_active = True
            print(f"[seed_admin] Updated password and role for existing admin user: {email}")
        
        session.commit()
        print("[seed_admin] Admin seeded successfully!")
    except Exception as e:
        session.rollback()
        print(f"[seed_admin] Error seeding admin: {e}")
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    seed_admin()
