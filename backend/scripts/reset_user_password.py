"""
Reset user password utility.
Run: python backend/scripts/reset_user_password.py <email> <new_password>
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
from database.models import User
from auth.password import hash_password

def reset_password(email: str, new_password: str):
    session = SyncSessionFactory()
    try:
        user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if not user:
            print(f"[reset_password] Error: User with email '{email}' not found.")
            sys.exit(1)

        user.password_hash = hash_password(new_password)
        session.commit()
        print(f"[reset_password] Successfully reset password for user: {email}")
    except Exception as e:
        session.rollback()
        print(f"[reset_password] Error resetting password: {e}")
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        # Prompt for inputs
        email = input("Enter user email: ").strip()
        new_password = input("Enter new password: ").strip()
    else:
        email = sys.argv[1].strip()
        new_password = sys.argv[2].strip()

    if not email or not new_password:
        print("Error: Both email and password are required.")
        sys.exit(1)

    reset_password(email, new_password)
