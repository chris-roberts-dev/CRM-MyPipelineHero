from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = PROJECT_ROOT / "docs" / "models_reference.md"

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

SKIP_MIGRATIONS = True


def should_skip(path: Path) -> bool:
    parts = set(path.parts)

    if parts & EXCLUDED_DIRS:
        return True

    if SKIP_MIGRATIONS and "migrations" in parts:
        return True

    return False


def heading_for_models_file(path: Path) -> str:
    """
    Example:
    backend/apps/platform/accounts/models.py

    Becomes:
    ## apps / platform / accounts
    """
    relative_path = path.relative_to(PROJECT_ROOT)

    # Remove the actual models.py filename
    parent_path = relative_path.parent

    return f"## {parent_path.as_posix().replace('/', ' / ')}"


def main() -> None:
    markdown: list[str] = [
        "# Django Models Reference",
        "",
        "This file combines all `models.py` files in the project.",
        "",
    ]

    model_files = sorted(PROJECT_ROOT.rglob("models.py"))

    for path in model_files:
        if should_skip(path):
            continue

        relative_path = path.relative_to(PROJECT_ROOT)

        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            markdown.extend(
                [
                    f"## `{relative_path.as_posix()}`",
                    "",
                    "> Could not read this file due to an encoding issue.",
                    "",
                ]
            )
            continue

        markdown.extend(
            [
                heading_for_models_file(path),
                "",
                f"`{relative_path.as_posix()}`",
                "",
                "```python",
                source.rstrip(),
                "```",
                "",
            ]
        )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text("\n".join(markdown), encoding="utf-8")

    print(f"Models reference created: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
