"""LRS command-line utilities.

Run with:

    python -m app.cli create-system-admin

Currently implements exactly one command: bootstrapping the first System
Admin account. This is deliberately CLI-only, never an HTTP endpoint — see
app/services/bootstrap_service.py for why. It is meant to be run once, by
whoever has access to the application server and its database connection
string; see docs/architecture/authentication.md, "Bootstrap System Admin".

Password input uses `getpass` (masked, not echoed to the terminal) and is
never accepted as a command-line argument — an argument would be visible in
shell history and in process listings (e.g. `ps`) on a shared server, which
is exactly what this command exists to avoid.
"""

import argparse
import getpass
import sys

from app.database.session import get_session_factory
from app.services.bootstrap_service import create_system_admin
from app.services.exceptions import (
    DuplicateEmailError,
    InvalidPasswordError,
    SystemAdminAlreadyExistsError,
)


def _prompt_create_system_admin() -> int:
    print("LRS -- Bootstrap System Administrator")
    print(
        "This creates the FIRST System Admin account. It can only be run "
        "once; a second attempt is refused if an active System Admin "
        "already exists.\n"
    )

    full_name = input("Full name: ").strip()
    email = input("Email: ").strip()
    password = getpass.getpass("Password: ")
    password_confirm = getpass.getpass("Confirm password: ")

    session_factory = get_session_factory()
    session = session_factory()
    try:
        user = create_system_admin(
            session,
            full_name=full_name,
            email=email,
            password=password,
            password_confirm=password_confirm,
        )
    except SystemAdminAlreadyExistsError:
        print(
            "\nRefused: an active System Admin already exists. A future "
            "administrative workflow will let an existing System Admin "
            "transfer that authority (see "
            "docs/architecture/authentication.md, \"System Admin "
            "handover\") -- that workflow is not implemented yet.",
            file=sys.stderr,
        )
        return 1
    except InvalidPasswordError as exc:
        print(f"\nRefused: {exc}", file=sys.stderr)
        return 1
    except DuplicateEmailError:
        print("\nRefused: a user with this email already exists.", file=sys.stderr)
        return 1
    finally:
        session.close()
        # `password` and `password_confirm` go out of scope here and are
        # never written to a log, a file, or stdout above this line.

    print(f"\nSystem Admin created: {user.email} (id={user.id}).")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli", description="LRS command-line utilities."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "create-system-admin",
        help="Bootstrap the first System Admin account (interactive, run once).",
    )
    args = parser.parse_args(argv)

    if args.command == "create-system-admin":
        return _prompt_create_system_admin()
    return 1  # pragma: no cover - unreachable while there is one subcommand


if __name__ == "__main__":
    sys.exit(main())
