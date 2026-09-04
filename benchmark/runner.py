from __future__ import annotations

import shlex
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from .models import BenchmarkTask, ModelResult
from .patching import PatchError, apply_unified_diff, extract_unified_diff
from .providers import ModelProvider, ProviderError
from .prompts import build_prompt
from .workspace import collect_workspace


MAX_OUTPUT_CHARS = 12_000
IGNORED_COPY_DIRECTORIES = {
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
    "results",
}


def _truncate(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[:MAX_OUTPUT_CHARS] + "\n...[output truncated]..."


def _copy_ignore(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in IGNORED_COPY_DIRECTORIES}


def run_command(command: str, cwd: Path, timeout: int) -> tuple[int, str]:
    arguments = shlex.split(command)
    if not arguments:
        raise ValueError("Command must not be empty")
    try:
        completed = subprocess.run(
            arguments,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        output = str(exc.stdout or "") + str(exc.stderr or "")
        return 124, _truncate(output + "\nCommand timed out.")

    output = (completed.stdout or "") + (completed.stderr or "")
    return completed.returncode, _truncate(output.strip())


def run_model(
    task: BenchmarkTask,
    workspace: str | Path,
    provider: ModelProvider,
    *,
    timeout: int = 300,
    workspace_snapshot: str | None = None,
) -> ModelResult:
    started = time.perf_counter()
    result = ModelResult(provider=provider.provider, model=provider.model)
    workspace = Path(workspace).resolve()

    try:
        snapshot = workspace_snapshot or collect_workspace(
            workspace,
            max_files=task.max_files,
            max_file_bytes=task.max_file_bytes,
        )
        response = provider.generate(build_prompt(task, snapshot))
        result.input_tokens = response.input_tokens
        result.output_tokens = response.output_tokens

        patch = extract_unified_diff(response.text)
        if not patch:
            result.error = "Model response did not contain an applicable unified diff"
            return result
        result.patch = patch

        with tempfile.TemporaryDirectory(prefix="coding-benchmark-") as directory:
            candidate = Path(directory) / "workspace"
            shutil.copytree(
                workspace,
                candidate,
                dirs_exist_ok=True,
                ignore=_copy_ignore,
            )
            apply_unified_diff(candidate, patch)
            result.patch_applied = True

            if task.setup_command:
                setup_code, setup_output = run_command(
                    task.setup_command,
                    candidate,
                    timeout,
                )
                if setup_code != 0:
                    result.test_returncode = setup_code
                    result.test_output = _truncate(
                        "Setup command failed:\n" + setup_output
                    )
                    result.error = "Setup command failed"
                    return result

            test_code, test_output = run_command(
                task.test_command,
                candidate,
                timeout,
            )
            result.test_returncode = test_code
            result.test_output = test_output
            result.tests_passed = test_code == 0
    except (PatchError, OSError, ProviderError, ValueError) as exc:
        result.error = str(exc)
    finally:
        result.elapsed_seconds = round(time.perf_counter() - started, 3)

    return result


def compare_models(
    task: BenchmarkTask,
    workspace: str | Path,
    providers: list[ModelProvider],
    *,
    timeout: int = 300,
) -> list[ModelResult]:
    snapshot = collect_workspace(
        workspace,
        max_files=task.max_files,
        max_file_bytes=task.max_file_bytes,
    )
    return [
        run_model(
            task,
            workspace,
            provider,
            timeout=timeout,
            workspace_snapshot=snapshot,
        )
        for provider in providers
    ]
