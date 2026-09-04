# Claude vs GPT Coding Benchmark

A small, reproducible benchmark for comparing Claude and GPT models on the
same coding tasks. It uses GitHub issues as task metadata, asks each provider
for a unified diff, applies each diff in an isolated copy of a repository, and
runs the same tests against both results.

The benchmark is designed to measure practical repository work rather than
produce a universal model ranking. Every result records the task, model ID,
prompt hash, patch status, test outcome, elapsed time, token usage when the
provider returns it, and test output.

## Why this is a GitHub integration

The github fetch-issue command calls the GitHub REST API and converts a
repository issue into a benchmark task. This makes the project a genuine
GitHub API integration suitable as a foundation for a GitHub Developer
Program application.

## Quick start

Use Python 3.10 or newer:

    python -m venv .venv
    source .venv/bin/activate
    python -m pip install -e ".[dev]"
    pytest

Set provider keys only in your shell or a local environment file. The
benchmark never writes keys to result files:

    export GITHUB_TOKEN=your_github_token
    export OPENAI_API_KEY=your_openai_key
    export ANTHROPIC_API_KEY=your_anthropic_key

Fetch a real issue into a task manifest:

    coding-benchmark github fetch-issue \
      --repo aktaseren/Presidio_Guardrail_POC \
      --number 1 \
      --test-command "python -m pytest -q" \
      --output tasks/presidio-issue-1.json

Run both providers against the same local checkout:

    coding-benchmark compare tasks/presidio-issue-1.json \
      --workspace /path/to/repository \
      --openai-model gpt-5.6-luna \
      --anthropic-model YOUR_CLAUDE_BALANCED_MODEL_ID \
      --output results/presidio-issue-1.json

Render a human-readable report:

    coding-benchmark report results/presidio-issue-1.json \
      --output results/presidio-issue-1.md

Generate the README chart from the measured JSON result:

    coding-benchmark chart results/presidio-issue-1.json \
      --output docs/benchmark-results.svg

The OpenAI model defaults to gpt-5.6-luna and its reasoning effort defaults to
medium. The Claude model remains configurable because the exact current model
ID depends on the Anthropic account. For this project, a current Claude
Sonnet-tier model is the intended practical peer for Luna's cost-sensitive
coding workload; that is a workload-matching choice, not an official model
equivalence claim. The runner uses the OpenAI Responses API and the Anthropic
Messages API.

## Latest comparison chart

This image is generated from an actual result JSON file. It deliberately shows
recorded patch, test, timing, and token metrics instead of combining different
units into an unsupported universal score.

![GPT-5.6 Luna vs Claude coding benchmark](docs/benchmark-results.svg?v=token-usage-fix)

The current public run uses the repository's calculator demo task. Both local
CLIs passed the same test; the sanitized summary is available in
[docs/local-cli-comparison.md](docs/local-cli-comparison.md). Raw result JSON,
prompts, patches, test output, and credentials remain local and ignored.

Claude input-token totals include uncached, cache-read, and cache-created input
reported for the selected model. Claude Code's top-level `input_tokens` field
only contains the uncached portion.

For local authenticated CLIs, use:

    coding-benchmark compare-local examples/demo_task.json \
      --workspace /path/to/this/repository \
      --codex-model gpt-5.6-luna \
      --claude-model sonnet \
      --output results/local-cli-demo.json

## Two popular public repositories

The repository also includes two focused synthetic regression tasks on pinned
public snapshots: Click's long-option parser and Requests' case-insensitive
header mapping. The task snapshots include only the relevant source file, and
the hidden assertions are supplied through the test command.

![Click comparison](docs/popular-click.svg?v=token-usage-fix)

![Requests comparison](docs/popular-requests.svg?v=token-usage-fix)

The sanitized combined result is in
[docs/popular-repo-comparison.md](docs/popular-repo-comparison.md). To rerun
the cases locally:

    coding-benchmark compare-local examples/popular_tasks/click-option-parser.json \
      --workspace /tmp/benchmark-popular-repos/click \
      --codex-model gpt-5.6-luna \
      --claude-model sonnet \
      --output results/click-local.json

    coding-benchmark compare-local examples/popular_tasks/requests-case-insensitive-dict.json \
      --workspace /tmp/benchmark-popular-repos/requests \
      --codex-model gpt-5.6-luna \
      --claude-model sonnet \
      --output results/requests-local.json

    coding-benchmark chart results/click-local.json \
      --output docs/popular-click.svg

    coding-benchmark chart results/requests-local.json \
      --output docs/popular-requests.svg

    coding-benchmark report-batch results/click-local.json results/requests-local.json \
      --output docs/popular-repo-comparison.md

## Task manifest

A task is a JSON document:

    {
      "task_id": "calculator-001",
      "title": "Fix subtraction",
      "prompt": "Make the calculator return the correct subtraction result.",
      "test_command": "python -m pytest -q",
      "setup_command": null,
      "source": {
        "kind": "github_issue",
        "repository": "owner/repository",
        "issue": 123,
        "url": "https://github.com/owner/repository/issues/123"
      }
    }

The workspace must be a local Git repository. The test command is parsed with
the shlex module and runs without a shell, which keeps task execution
predictable. Only use task manifests and repositories you trust.

## Fairness and safety

* Both providers receive the same task prompt and workspace snapshot.
* Each patch is evaluated in a fresh temporary copy.
* Tests are run with a timeout and their output is truncated in reports.
* Secret-like files such as .env, private keys, and credential files are
  excluded from the workspace snapshot.
* A passing test is evidence of task success, not proof of overall code
  quality. Add task-specific tests and review results before publishing them.
* Do not use private source code or API keys in public benchmark results.

## Current scope

The first version intentionally uses a transparent local evaluator:

1. Fetch task metadata from GitHub.
2. Give the same repository snapshot and task to Claude and GPT.
3. Extract and apply each model's unified diff.
4. Run the task's test command.
5. Save machine-readable evidence and a Markdown summary.

Future work can add GitHub App authentication, pull-request task harvesting,
containerized execution, more languages, and optional OpenAI Evals API export.
