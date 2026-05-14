#!/usr/bin/env python
"""A.4.5 — Service-layer discipline AST static check.

Walks ``backend/apps/**/*.py`` and warns on patterns the guide
prohibits outside the service layer:

* ``Model.objects.create(...)`` outside ``apps/*/services/``,
  ``apps/**/admin*.py``, ``apps/**/migrations/``, ``apps/**/tests/``,
  and ``apps/**/management/commands/`` (CLI seed/admin tools).
* ``.save()`` and ``.delete()`` outside ``apps/*/services/``.
* ``Manager.update(...)`` on a queryset outside ``apps/*/services/``.
* ``transaction.atomic()`` opened outside ``apps/*/services/`` (warning).
* ``request.user`` referenced inside ``apps/*/services/``.
* ``GenericForeignKey`` declared anywhere.
* ``forms.ModelChoiceField`` not nested under ``TenantModelChoiceField``
  (narrow heuristic — flag any direct ``forms.ModelChoiceField(...)``
  call in ``apps/**/forms.py``).

The script is ADVISORY in M0 — it reports findings and exits 0. Per
A.4.5 the check becomes blocking from M2.

Output format: ``<path>:<line>: WARN[<rule>] <message>``

Exit codes:
    0  Always (M0). The script is non-blocking.
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
APPS_ROOT = REPO_ROOT / "backend" / "apps"


# ---------------------------------------------------------------------------
# Path classification
# ---------------------------------------------------------------------------


def _path_parts(path: Path) -> tuple[str, ...]:
    return path.relative_to(REPO_ROOT).parts


def is_service_path(path: Path) -> bool:
    """True if the file lives under any ``apps/*/services/`` tree."""
    parts = _path_parts(path)
    if "services" in parts:
        return True
    return path.name == "services.py" and parts[:2] == ("backend", "apps")


def is_admin_path(path: Path) -> bool:
    """True if the file is an admin module or under an admin subtree."""
    parts = _path_parts(path)
    if "admin" in parts:
        return True
    return path.name == "admin.py" or path.name.startswith("admin_")


def is_migration_path(path: Path) -> bool:
    return "migrations" in _path_parts(path)


def is_test_path(path: Path) -> bool:
    parts = _path_parts(path)
    if "tests" in parts:
        return True
    return path.name.startswith("test_") or path.name == "conftest.py"


def is_forms_path(path: Path) -> bool:
    return path.name == "forms.py" or "forms" in _path_parts(path)


def is_management_command_path(path: Path) -> bool:
    """True if the file lives under any ``management/commands/`` directory.

    Django management commands are dev-/admin-tier CLI tools and are
    explicitly exempt from the service-layer write rules along with
    admin/migrations/tests.
    """
    parts = _path_parts(path)
    for i in range(len(parts) - 1):
        if parts[i] == "management" and parts[i + 1] == "commands":
            return True
    return False


# ---------------------------------------------------------------------------
# Finding model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    rule: str
    message: str

    def render(self) -> str:
        rel = self.path.relative_to(REPO_ROOT).as_posix()
        return f"{rel}:{self.line}: WARN[{self.rule}] {self.message}"


# ---------------------------------------------------------------------------
# AST visitor
# ---------------------------------------------------------------------------


class _ServiceDisciplineVisitor(ast.NodeVisitor):
    """Walk a module's AST and collect rule violations."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.findings: list[Finding] = []
        self._in_service = is_service_path(path)
        self._in_admin = is_admin_path(path)
        self._in_migration = is_migration_path(path)
        self._in_test = is_test_path(path)
        self._in_forms = is_forms_path(path)
        self._in_mgmt_command = is_management_command_path(path)
        # Aggregate exemption flag for state-changing operations.
        self._is_exempt_for_writes = (
            self._in_service
            or self._in_admin
            or self._in_migration
            or self._in_test
            or self._in_mgmt_command
        )

    # -- helpers ----------------------------------------------------------

    def _add(self, node: ast.AST, rule: str, message: str) -> None:
        self.findings.append(
            Finding(
                path=self.path,
                line=getattr(node, "lineno", 0),
                rule=rule,
                message=message,
            ),
        )

    @staticmethod
    def _attr_chain(node: ast.AST) -> list[str]:
        """Flatten an attribute access into a list of names.

        ``Quote.objects.create`` → ``["Quote", "objects", "create"]``
        """
        parts: list[str] = []
        cur: ast.AST | None = node
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
        return list(reversed(parts))

    # -- rule: Model.objects.create(...) outside allowed paths ------------

    def _check_objects_create(self, call: ast.Call) -> None:
        if self._is_exempt_for_writes:
            return
        if not isinstance(call.func, ast.Attribute):
            return
        chain = self._attr_chain(call.func)
        if len(chain) < 3:
            return
        if chain[-2] == "objects" and chain[-1] == "create":
            self._add(
                call,
                "objects.create",
                "Model.objects.create(...) outside services/admin/migrations/tests/"
                "management-commands; state changes belong in apps/*/services/.",
            )

    # -- rule: queryset .update(...) outside services ---------------------

    def _check_queryset_update(self, call: ast.Call) -> None:
        if self._is_exempt_for_writes:
            return
        if not isinstance(call.func, ast.Attribute):
            return
        if call.func.attr != "update":
            return
        chain = self._attr_chain(call.func)
        if "objects" in chain:
            self._add(
                call,
                "queryset.update",
                ".update(...) on a queryset outside services; state changes "
                "belong in apps/*/services/.",
            )

    # -- rule: .save() / .delete() outside services -----------------------

    def _check_save_delete(self, call: ast.Call) -> None:
        if self._is_exempt_for_writes:
            return
        if not isinstance(call.func, ast.Attribute):
            return
        if call.func.attr not in {"save", "delete"}:
            return
        # ModelForm.save is a Django idiom; skip forms.
        if self._in_forms:
            return
        receiver = call.func.value
        if not isinstance(receiver, (ast.Name, ast.Attribute, ast.Subscript)):
            return
        chain = (
            self._attr_chain(receiver)
            if isinstance(receiver, ast.Attribute)
            else [receiver.id if isinstance(receiver, ast.Name) else ""]
        )
        if chain and chain[0] in {"session", "cache", "logger", "log"}:
            return
        self._add(
            call,
            f".{call.func.attr}()",
            f".{call.func.attr}() called outside apps/*/services/; state "
            "changes belong in the service layer.",
        )

    # -- rule: transaction.atomic() outside services ----------------------

    def _check_transaction_atomic(self, call: ast.Call) -> None:
        if self._is_exempt_for_writes:
            return
        if not isinstance(call.func, ast.Attribute):
            return
        chain = self._attr_chain(call.func)
        if chain[-2:] == ["transaction", "atomic"]:
            self._add(
                call,
                "transaction.atomic",
                "transaction.atomic() opened outside services; transaction "
                "boundaries should live with the orchestration logic.",
            )

    # -- rule: request.user inside services -------------------------------

    def _check_request_user(self, node: ast.Attribute) -> None:
        if not self._in_service:
            return
        if node.attr != "user":
            return
        if not isinstance(node.value, ast.Name):
            return
        if node.value.id != "request":
            return
        self._add(
            node,
            "request.user-in-service",
            "request.user referenced inside a service module; services accept "
            "actor_id primitives, not request objects (A.4.4 #2).",
        )

    # -- rule: GenericForeignKey anywhere ---------------------------------

    def _check_generic_fk_call(self, call: ast.Call) -> None:
        if not isinstance(call.func, (ast.Name, ast.Attribute)):
            return
        if isinstance(call.func, ast.Name):
            if call.func.id == "GenericForeignKey":
                self._add(
                    call,
                    "GenericForeignKey",
                    "GenericForeignKey is prohibited (A.2.6); use a typed FK.",
                )
        else:
            if call.func.attr == "GenericForeignKey":
                self._add(
                    call,
                    "GenericForeignKey",
                    "GenericForeignKey is prohibited (A.2.6); use a typed FK.",
                )

    # -- rule: forms.ModelChoiceField without TenantModelChoiceField ------

    def _check_model_choice_field(self, call: ast.Call) -> None:
        if not self._in_forms:
            return
        if not isinstance(call.func, ast.Attribute):
            return
        chain = self._attr_chain(call.func)
        if chain[-2:] == ["forms", "ModelChoiceField"]:
            self._add(
                call,
                "ModelChoiceField",
                "forms.ModelChoiceField used directly; subclass "
                "TenantModelChoiceField to enforce tenant isolation.",
            )

    # -- entry points -----------------------------------------------------

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        self._check_objects_create(node)
        self._check_queryset_update(node)
        self._check_save_delete(node)
        self._check_transaction_atomic(node)
        self._check_generic_fk_call(node)
        self._check_model_choice_field(node)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:  # noqa: N802
        self._check_request_user(node)
        self.generic_visit(node)


# ---------------------------------------------------------------------------
# File discovery + driver
# ---------------------------------------------------------------------------


SKIP_DIRECTORY_NAMES = {"__pycache__", ".mypy_cache", ".ruff_cache", "node_modules"}


def _iter_python_files(root: Path) -> Iterator[Path]:
    if not root.is_dir():
        return
    for entry in root.iterdir():
        if entry.is_dir():
            if entry.name in SKIP_DIRECTORY_NAMES:
                continue
            yield from _iter_python_files(entry)
        elif entry.is_file() and entry.suffix == ".py":
            yield entry


def _analyze_file(path: Path) -> list[Finding]:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return [
            Finding(
                path=path,
                line=exc.lineno or 0,
                rule="syntax",
                message=f"could not parse: {exc.msg}",
            ),
        ]
    visitor = _ServiceDisciplineVisitor(path)
    visitor.visit(tree)
    return visitor.findings


def analyze(paths: Iterable[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for p in paths:
        findings.extend(_analyze_file(p))
    return findings


def main() -> int:
    files = list(_iter_python_files(APPS_ROOT))
    findings = analyze(files)

    if findings:
        for f in findings:
            print(f.render())
        print(
            f"\ncheck_service_layer_discipline: {len(findings)} WARN(s) in "
            f"{len(files)} files. Non-blocking in M0 (A.4.5).",
            file=sys.stderr,
        )
    else:
        print(
            f"check_service_layer_discipline: clean ({len(files)} files scanned).",
        )

    # Always exit 0 in M0. Promotion to blocking happens at M2 per A.4.5.
    return 0


if __name__ == "__main__":
    sys.exit(main())
