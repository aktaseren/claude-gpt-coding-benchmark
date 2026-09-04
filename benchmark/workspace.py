from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path


IGNORED_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
}

SECRET_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_ed25519",
    "credentials",
    "credentials.json",
}
SECRET_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".crt"}


def _is_secret(path: Path) -> bool:
    return path.name in SECRET_NAMES or path.suffix.lower() in SECRET_SUFFIXES


def collect_workspace(
    root: str | Path,
    *,
    max_files: int = 80,
    max_file_bytes: int = 120_000,
    include_paths: Iterable[str] | None = None,
) -> str:
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError(f"Workspace is not a directory: {root}")

    selected_paths = set()
    for value in include_paths or ():
        relative = Path(value)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Included workspace path must be relative: {value}")
        selected_paths.add(relative)

    sections: list[str] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if not path.is_file():
            continue
        if selected_paths and not any(
            relative == selected or selected in relative.parents
            for selected in selected_paths
        ):
            continue
        if any(part in IGNORED_DIRECTORIES for part in relative.parts):
            continue
        if _is_secret(path) or path.stat().st_size > max_file_bytes:
            continue
        try:
            contents = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "\x00" in contents:
            continue
        sections.append(f"--- {relative.as_posix()} ---\n{contents}")
        if len(sections) >= max_files:
            break

    if not sections:
        raise ValueError("No readable source files were found in the workspace")
    return "\n\n".join(sections)
