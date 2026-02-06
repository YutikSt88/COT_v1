"""Generate password hash (utility)."""

from __future__ import annotations

import argparse
import getpass

from src.app.auth import hash_password


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", default=None, help="Plain-text password (optional).")
    args = parser.parse_args()

    password = args.password
    if password is None:
        password = getpass.getpass("Password: ")
    if not password:
        print("Password is empty.")
        return 2

    print(hash_password(password))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
