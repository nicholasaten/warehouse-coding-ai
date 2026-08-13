"""Creates the one dedicated system-administrator account.

Run once, after the Alembic migration, from api/ with the venv active:

    python -m scripts.seed_admin --email admin@yourorg.com --name "System Administrator" --password "..."
"""
import argparse

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        existing = db.scalar(select(User).where(User.email == args.email))
        if existing is not None:
            print(f"A user with email {args.email} already exists (id={existing.id}). Nothing to do.")
            return

        admin = User(full_name=args.name, email=args.email, password_hash=hash_password(args.password), role="admin")
        db.add(admin)
        db.commit()
        print(f"Created admin {args.email} (id={admin.id}).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
