from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = PROJECT_ROOT / "docs" / "project_docstrings.md"

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "staticfiles",
    "media",
    "dist",
    "build",
}

EXCLUDED_FILES = {
    "manage.py",
}

SKIP_MIGRATIONS = True


def should_skip(path: Path) -> bool:
    parts = set(path.parts)

    if parts & EXCLUDED_DIRS:
        return True

    if SKIP_MIGRATIONS and "migrations" in parts:
        return True

    if path.name in EXCLUDED_FILES:
        return True

    return False


def get_docstring(node: ast.AST) -> str | None:
    docstring = ast.get_docstring(node)
    if docstring:
        return docstring.strip()
    return None


def heading_for_file(path: Path) -> str:
    relative_path = path.relative_to(PROJECT_ROOT)
    return f"## `{relative_path.as_posix()}`"


def extract_docstrings_from_file(path: Path) -> list[str]:
    results: list[str] = []

    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [
            f"## `{path.relative_to(PROJECT_ROOT).as_posix()}`",
            "",
            f"> Could not parse file due to syntax error: `{exc}`",
            "",
        ]
    except UnicodeDecodeError:
        return [
            f"## `{path.relative_to(PROJECT_ROOT).as_posix()}`",
            "",
            "> Could not read file due to encoding issue.",
            "",
        ]

    module_docstring = get_docstring(tree)

    if module_docstring:
        results.extend(
            [
                heading_for_file(path),
                "",
                "### Module docstring",
                "",
                module_docstring,
                "",
            ]
        )

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            docstring = get_docstring(node)
            if docstring:
                if not results:
                    results.extend([heading_for_file(path), ""])

                results.extend(
                    [
                        f"### Class `{node.name}`",
                        "",
                        docstring,
                        "",
                    ]
                )

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            docstring = get_docstring(node)
            if docstring:
                if not results:
                    results.extend([heading_for_file(path), ""])

                function_type = (
                    "Async function"
                    if isinstance(node, ast.AsyncFunctionDef)
                    else "Function"
                )

                results.extend(
                    [
                        f"### {function_type} `{node.name}`",
                        "",
                        docstring,
                        "",
                    ]
                )

    return results


def main() -> None:
    markdown: list[str] = [
        "# Project Docstrings",
        "",
        "This file was generated from Python module, class, function, and method docstrings.",
        "",
    ]

    python_files = sorted(PROJECT_ROOT.rglob("*.py"))

    for path in python_files:
        if should_skip(path):
            continue

        docstrings = extract_docstrings_from_file(path)

        if docstrings:
            markdown.extend(docstrings)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text("\n".join(markdown), encoding="utf-8")

    print(f"Docstring export complete: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
