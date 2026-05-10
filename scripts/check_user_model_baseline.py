#!/usr/bin/env python
"""I.6.7 — Custom user model baseline check.

Asserts:

* ``backend/apps/platform/accounts/migrations/0001_initial.py`` exists.
* It defines a Django model named ``User`` (CreateModel(name='User', ...)).
* ``backend/config/settings/base.py`` declares
  ``AUTH_USER_MODEL = "platform_accounts.User"``.

Retrofitting AUTH_USER_MODEL after deployment is prohibited (B.3.1).
This script is a CI gate — failing it should block merge.

Exit codes:
    0  baseline is intact
    1  baseline is broken (message printed to stderr)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND = REPO_ROOT / "backend"

USER_MIGRATION = (
    BACKEND / "apps" / "platform" / "accounts" / "migrations" / "0001_initial.py"
)
SETTINGS_BASE = BACKEND / "config" / "settings" / "base.py"

EXPECTED_AUTH_USER_MODEL = "platform_accounts.User"


def fail(msg: str) -> None:
    print(f"check_user_model_baseline: FAIL — {msg}", file=sys.stderr)
    sys.exit(1)


def ok(msg: str) -> None:
    print(f"check_user_model_baseline: OK — {msg}")


def main() -> None:
    # 1. Migration file exists.
    if not USER_MIGRATION.is_file():
        fail(
            f"missing migration file at {USER_MIGRATION.relative_to(REPO_ROOT)}. "
            "The custom User model MUST be defined in apps/platform/accounts/"
            "migrations/0001_initial.py (B.3.1, I.6.7)."
        )
    ok(f"found {USER_MIGRATION.relative_to(REPO_ROOT)}")

    # 2. Migration defines a User model.
    migration_src = USER_MIGRATION.read_text(encoding="utf-8")
    if not re.search(
        r"migrations\.CreateModel\(\s*name\s*=\s*[\"']User[\"']",
        migration_src,
    ):
        fail(
            f"{USER_MIGRATION.relative_to(REPO_ROOT)} does not contain "
            "CreateModel(name='User', ...). The User model must be created "
            "in this migration."
        )
    ok("migration defines User model")

    # 3. AUTH_USER_MODEL is wired up correctly.
    if not SETTINGS_BASE.is_file():
        fail(f"missing {SETTINGS_BASE.relative_to(REPO_ROOT)}")
    settings_src = SETTINGS_BASE.read_text(encoding="utf-8")
    pattern = (
        r"AUTH_USER_MODEL\s*(?::\s*str\s*)?=\s*[\"']"
        + re.escape(EXPECTED_AUTH_USER_MODEL)
        + r"[\"']"
    )
    if not re.search(pattern, settings_src):
        fail(
            f'AUTH_USER_MODEL = "{EXPECTED_AUTH_USER_MODEL}" not found in '
            f"{SETTINGS_BASE.relative_to(REPO_ROOT)}."
        )
    ok(f'AUTH_USER_MODEL = "{EXPECTED_AUTH_USER_MODEL}" is set in base settings')

    print("check_user_model_baseline: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
