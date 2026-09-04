from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence

from .chart import write_svg
from .github import GitHubClient
from .models import BenchmarkTask
from .providers import make_cli_provider, make_provider
from .report import (
    build_payload,
    read_json,
    render_markdown,
    render_public_batch_markdown,
    render_public_markdown,
    write_json,
)
from .runner import compare_models


def _read_task(path: str | Path) -> BenchmarkTask:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    return BenchmarkTask.from_dict(value)


def _write_task(task: BenchmarkTask, output: str | Path) -> None:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(task.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare Claude and GPT models on reproducible coding tasks."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    github_parser = commands.add_parser(
        "github",
        help="Read benchmark task metadata through the GitHub REST API.",
    )
    github_commands = github_parser.add_subparsers(
        dest="github_command",
        required=True,
    )

    fetch = github_commands.add_parser(
        "fetch-issue",
        help="Convert one GitHub issue into a task manifest.",
    )
    fetch.add_argument("--repo", required=True, help="Repository as OWNER/REPOSITORY")
    fetch.add_argument("--number", required=True, type=int)
    fetch.add_argument("--test-command", required=True)
    fetch.add_argument("--setup-command")
    fetch.add_argument("--output", required=True)

    list_issues = github_commands.add_parser(
        "list-issues",
        help="List issue candidates from a repository.",
    )
    list_issues.add_argument("--repo", required=True)
    list_issues.add_argument("--label")
    list_issues.add_argument("--state", choices=("open", "closed", "all"), default="open")
    list_issues.add_argument("--limit", type=int, default=20)

    compare = commands.add_parser(
        "compare",
        help="Run one Claude model and one GPT model on the same task.",
    )
    compare.add_argument("task", help="Path to a task JSON manifest")
    compare.add_argument("--workspace", required=True)
    compare.add_argument(
        "--openai-model",
        default=os.getenv("OPENAI_MODEL") or "gpt-5.6-luna",
        help="OpenAI model ID (default: gpt-5.6-luna)",
    )
    compare.add_argument(
        "--anthropic-model",
        default=os.getenv("ANTHROPIC_MODEL"),
        help="Claude model ID, or set ANTHROPIC_MODEL",
    )
    compare.add_argument(
        "--openai-reasoning-effort",
        choices=("none", "low", "medium", "high", "xhigh", "max"),
        default=os.getenv("OPENAI_REASONING_EFFORT") or "medium",
        help="Reasoning effort sent to GPT-5.6 Luna (default: medium)",
    )
    compare.add_argument("--timeout", type=int, default=300)
    compare.add_argument("--output", required=True)

    compare_local = commands.add_parser(
        "compare-local",
        help="Compare local Codex and Claude CLIs without passing API keys.",
    )
    compare_local.add_argument("task", help="Path to a task JSON manifest")
    compare_local.add_argument("--workspace", required=True)
    compare_local.add_argument(
        "--codex-model",
        default=os.getenv("CODEX_MODEL") or "gpt-5.6-luna",
        help="Model passed to codex exec (default: gpt-5.6-luna)",
    )
    compare_local.add_argument(
        "--claude-model",
        default=os.getenv("CLAUDE_MODEL") or "sonnet",
        help="Model or alias passed to Claude Code (default: sonnet)",
    )
    compare_local.add_argument("--timeout", type=int, default=300)
    compare_local.add_argument("--output", required=True)

    report = commands.add_parser(
        "report",
        help="Render a JSON benchmark result as Markdown.",
    )
    report.add_argument("result", help="Path to a result JSON file")
    report.add_argument("--output")
    report.add_argument(
        "--public",
        action="store_true",
        help="Exclude prompts, patches, test output, and error details",
    )

    report_batch = commands.add_parser(
        "report-batch",
        help="Render several result JSON files as one sanitized Markdown report.",
    )
    report_batch.add_argument("results", nargs="+", help="Result JSON files")
    report_batch.add_argument("--output", required=True)

    chart = commands.add_parser(
        "chart",
        help="Render measured benchmark results as an SVG chart.",
    )
    chart.add_argument("result", help="Path to a result JSON file")
    chart.add_argument("--output", required=True)
    return parser


def _run(args: argparse.Namespace) -> int:
    if args.command == "github" and args.github_command == "fetch-issue":
        client = GitHubClient()
        issue = client.get_issue(args.repo, args.number)
        task = client.issue_to_task(
            args.repo,
            issue,
            test_command=args.test_command,
            setup_command=args.setup_command,
        )
        _write_task(task, args.output)
        print(f"Wrote task {task.task_id} to {args.output}")
        return 0

    if args.command == "github" and args.github_command == "list-issues":
        client = GitHubClient()
        issues = client.list_issues(
            args.repo,
            label=args.label,
            state=args.state,
            limit=args.limit,
        )
        print(json.dumps(issues, indent=2, ensure_ascii=False))
        return 0

    if args.command == "compare":
        if not args.anthropic_model:
            raise ValueError(
                "Set ANTHROPIC_MODEL or pass --anthropic-model with the exact Claude model ID"
            )
        task = _read_task(args.task)
        providers = [
            make_provider(
                "openai",
                args.openai_model,
                reasoning_effort=args.openai_reasoning_effort,
            ),
            make_provider("anthropic", args.anthropic_model),
        ]
        results = compare_models(
            task,
            args.workspace,
            providers,
            timeout=args.timeout,
        )
        write_json(build_payload(task, results), args.output)
        print(f"Wrote comparison results to {args.output}")
        return 0

    if args.command == "compare-local":
        task = _read_task(args.task)
        providers = [
            make_cli_provider("codex", args.codex_model, timeout=args.timeout),
            make_cli_provider("claude", args.claude_model, timeout=args.timeout),
        ]
        results = compare_models(
            task,
            args.workspace,
            providers,
            timeout=args.timeout,
        )
        write_json(build_payload(task, results), args.output)
        print(f"Wrote local CLI comparison results to {args.output}")
        return 0

    if args.command == "chart":
        write_svg(read_json(args.result), args.output)
        print(f"Wrote SVG chart to {args.output}")
        return 0

    if args.command == "report":
        payload = read_json(args.result)
        markdown = render_public_markdown(payload) if args.public else render_markdown(payload)
        if args.output:
            path = Path(args.output)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(markdown, encoding="utf-8")
            print(f"Wrote Markdown report to {args.output}")
        else:
            print(markdown)
        return 0

    if args.command == "report-batch":
        markdown = render_public_batch_markdown(
            [read_json(path) for path in args.results]
        )
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(markdown, encoding="utf-8")
        print(f"Wrote batch Markdown report to {args.output}")
        return 0

    raise ValueError("Unknown command")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return _run(args)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
