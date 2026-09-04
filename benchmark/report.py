from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import BenchmarkTask, ModelResult, utc_now


def build_payload(task: BenchmarkTask, results: list[ModelResult]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "created_at": utc_now(),
        "task": task.to_dict(),
        "results": [
            {**result.to_dict(), "status": result.status} for result in results
        ],
    }


def write_json(payload: dict[str, Any], output: str | Path) -> None:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def render_markdown(payload: dict[str, Any]) -> str:
    task = payload["task"]
    results = payload.get("results", [])
    lines = [
        f"# Coding benchmark: {task['title']}",
        "",
        f"- Task ID: {task['task_id']}",
        f"- Created: {payload.get('created_at', 'unknown')}",
        f"- Test command: {task['test_command']}",
        "",
        "| Provider | Model | Status | Tests | Time (s) | Input tokens | Output tokens |",
        "|---|---|---|---|---:|---:|---:|",
    ]
    for result in results:
        tests = "passed" if result.get("tests_passed") else "failed"
        lines.append(
            "| {provider} | {model} | {status} | {tests} | {elapsed} | {input} | {output} |".format(
                provider=result.get("provider", ""),
                model=result.get("model", ""),
                status=result.get("status", ""),
                tests=tests,
                elapsed=result.get("elapsed_seconds", ""),
                input=result.get("input_tokens", ""),
                output=result.get("output_tokens", ""),
            )
        )

    lines.extend(["", "## Test output", ""])
    for result in results:
        label = f"{result.get('provider', '')}:{result.get('model', '')}"
        lines.extend(
            [
                f"### {label}",
                "",
                f"Error: {result.get('error') or 'none'}",
                "",
                "<pre>",
                result.get("test_output") or "(no test output)",
                "</pre>",
                "",
            ]
        )
    return "\n".join(lines)


def render_public_markdown(payload: dict[str, Any]) -> str:
    task = payload["task"]
    results = payload.get("results", [])
    lines = [
        f"# Public coding benchmark: {task['title']}",
        "",
        f"- Task ID: {task['task_id']}",
        f"- Created: {payload.get('created_at', 'unknown')}",
        "",
        "This summary intentionally excludes prompts, repository snapshots, "
        "patches, test output, and credentials.",
        "",
        "| Provider | Model | Status | Patch applied | Tests passed | Time (s) | Input tokens | Output tokens |",
        "|---|---|---|---|---|---:|---:|---:|",
    ]
    for result in results:
        lines.append(
            "| {provider} | {model} | {status} | {patch} | {tests} | {elapsed} | {input} | {output} |".format(
                provider=result.get("provider", ""),
                model=result.get("model", ""),
                status=result.get("status", ""),
                patch="yes" if result.get("patch_applied") else "no",
                tests="yes" if result.get("tests_passed") else "no",
                elapsed=result.get("elapsed_seconds", ""),
                input=result.get("input_tokens")
                if result.get("input_tokens") is not None
                else "n/a",
                output=result.get("output_tokens")
                if result.get("output_tokens") is not None
                else "n/a",
            )
        )
    lines.extend(
        [
            "",
            "Results are evidence for this task only; they are not a universal model ranking.",
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown(payload: dict[str, Any], output: str | Path) -> None:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown(payload), encoding="utf-8")
