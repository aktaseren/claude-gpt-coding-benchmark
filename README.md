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
      --openai-model YOUR_OPENAI_MODEL_ID \
      --anthropic-model YOUR_CLAUDE_MODEL_ID \
      --output results/presidio-issue-1.json

Render a human-readable report:

    coding-benchmark report results/presidio-issue-1.json \
      --output results/presidio-issue-1.md

Model IDs are passed explicitly because availability changes by account and
provider. For OpenAI, use a current model ID from the official model catalog.
The runner uses the OpenAI Responses API and the Anthropic Messages API.

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
