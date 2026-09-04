from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path


class PatchError(RuntimeError):
    """Raised when a model patch cannot be extracted or applied."""


FENCE_PATTERN = re.compile(
    r"\x60\x60\x60(?:diff|patch|udiff)?[ \t]*\n(?P<patch>.*?)\x60\x60\x60",
    flags=re.IGNORECASE | re.DOTALL,
)


def _strip_closing_fence(value: str) -> str:
    return re.sub(r"\n?\x60\x60\x60[ \t]*$", "", value).rstrip()


def extract_unified_diff(response_text: str) -> str | None:
    for match in FENCE_PATTERN.finditer(response_text):
        candidate = match.group("patch").strip()
        if "diff --git " in candidate or (
            candidate.startswith("--- ") and "\n+++ " in candidate
        ):
            return _strip_closing_fence(candidate) + "\n"

    for marker in ("diff --git ", "--- "):
        start = response_text.find(marker)
        if start >= 0:
            candidate = _strip_closing_fence(response_text[start:].strip())
            if "diff --git " in candidate or "\n+++ " in candidate:
                return candidate + "\n"
    return None


def apply_unified_diff(root: str | Path, patch: str) -> None:
    root = Path(root)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".patch",
        prefix="benchmark-",
        delete=False,
    ) as handle:
        handle.write(patch)
        patch_path = Path(handle.name)

    try:
        check = subprocess.run(
            [
                "git",
                "apply",
                "--check",
                "--recount",
                "--whitespace=nowarn",
                str(patch_path),
            ],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if check.returncode != 0:
            detail = (check.stderr or check.stdout).strip()
            raise PatchError(f"Patch did not apply cleanly: {detail[:1000]}")

        applied = subprocess.run(
            [
                "git",
                "apply",
                "--recount",
                "--whitespace=nowarn",
                str(patch_path),
            ],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if applied.returncode != 0:
            detail = (applied.stderr or applied.stdout).strip()
            raise PatchError(f"Patch application failed: {detail[:1000]}")
    except subprocess.TimeoutExpired as exc:
        raise PatchError("Patch application timed out") from exc
    finally:
        patch_path.unlink(missing_ok=True)
