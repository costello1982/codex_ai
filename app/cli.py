from __future__ import annotations

import argparse
from getpass import getpass

from sqlalchemy.exc import IntegrityError

from .auth import get_password_hash
from .database import SessionLocal
from .models import User


def create_user(username: str, password: str) -> None:
    with SessionLocal() as session:
        if session.query(User).filter_by(username=username).first():
            raise SystemExit(f"User '{username}' already exists")
        user = User(username=username, hashed_password=get_password_hash(password))
        session.add(user)
        try:
            session.commit()
        except IntegrityError as exc:  # pragma: no cover - defensive
            session.rollback()
            raise SystemExit(f"Failed to create user: {exc}")
        else:
            print(f"Created user '{username}'")


def main() -> None:
    parser = argparse.ArgumentParser(description="IPAM helper commands")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create-user", help="Create a local user account")
    create_parser.add_argument("username", help="Username for the new account")
    create_parser.add_argument(
        "--password",
        help="Password for the new account (prompted if omitted)",
    )

    args = parser.parse_args()

    if args.command == "create-user":
        password = args.password or getpass("Password: ")
        create_user(args.username, password)


if __name__ == "__main__":
    main()
