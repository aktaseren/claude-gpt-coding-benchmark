from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Protocol

from .models import ModelResponse
from .prompts import SYSTEM_INSTRUCTIONS


LOCAL_CLI_OUTPUT_INSTRUCTIONS = """Before returning, validate the diff mentally:
use correct unified-diff hunk counts, include a space prefix on unchanged lines,
and emit no explanation or trailing prose. Keep the patch as small as possible."""


class ProviderError(RuntimeError):
    """Raised when a model provider cannot produce a response."""


class ModelProvider(Protocol):
    provider: str
    model: str

    def generate(self, prompt: str) -> ModelResponse:
        ...


def parse_model_ref(value: str) -> tuple[str, str]:
    provider, separator, model = value.partition(":")
    if not separator or not provider or not model:
        raise ValueError(
            "Model reference must use PROVIDER:MODEL, for example "
            "openai:gpt-model-id"
        )
    provider = provider.lower()
    if provider not in {"openai", "anthropic"}:
        raise ValueError("Only the openai and anthropic providers are supported")
    return provider, model


def _usage_value(usage: Any, name: str) -> int | None:
    if usage is None:
        return None
    value = getattr(usage, name, None)
    if value is None and isinstance(usage, dict):
        value = usage.get(name)
    return int(value) if value is not None else None


class OpenAIProvider:
    provider = "openai"

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        reasoning_effort: str | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.reasoning_effort = reasoning_effort

    def generate(self, prompt: str) -> ModelResponse:
        if not self.api_key:
            raise ProviderError("OPENAI_API_KEY is not set")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ProviderError(
                "Install the OpenAI SDK with: python -m pip install openai"
            ) from exc

        try:
            client = OpenAI(api_key=self.api_key)
            request: dict[str, Any] = {
                "model": self.model,
                "instructions": SYSTEM_INSTRUCTIONS,
                "input": prompt,
                "store": False,
            }
            if self.reasoning_effort:
                request["reasoning"] = {"effort": self.reasoning_effort}
            response = client.responses.create(**request)
        except Exception as exc:
            raise ProviderError(f"OpenAI request failed: {exc}") from exc

        text = str(getattr(response, "output_text", "") or "")
        usage = getattr(response, "usage", None)
        return ModelResponse(
            text=text,
            input_tokens=_usage_value(usage, "input_tokens"),
            output_tokens=_usage_value(usage, "output_tokens"),
        )


class AnthropicProvider:
    provider = "anthropic"

    def __init__(self, model: str, api_key: str | None = None) -> None:
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

    def generate(self, prompt: str) -> ModelResponse:
        if not self.api_key:
            raise ProviderError("ANTHROPIC_API_KEY is not set")
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise ProviderError(
                "Install the Anthropic SDK with: python -m pip install anthropic"
            ) from exc

        try:
            client = Anthropic(api_key=self.api_key)
            response = client.messages.create(
                model=self.model,
                max_tokens=16_000,
                system=SYSTEM_INSTRUCTIONS,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:
            raise ProviderError(f"Anthropic request failed: {exc}") from exc

        blocks = getattr(response, "content", []) or []
        text = "".join(
            str(getattr(block, "text", ""))
            for block in blocks
            if getattr(block, "type", "text") == "text"
        )
        usage = getattr(response, "usage", None)
        return ModelResponse(
            text=text,
            input_tokens=_usage_value(usage, "input_tokens"),
            output_tokens=_usage_value(usage, "output_tokens"),
        )


SECRET_ENV_MARKERS = (
    "API_KEY",
    "ACCESS_TOKEN",
    "AUTH_TOKEN",
    "SECRET",
    "PASSWORD",
    "PRIVATE_KEY",
)


def _is_secret_environment_name(name: str) -> bool:
    upper_name = name.upper()
    return (
        any(marker in upper_name for marker in SECRET_ENV_MARKERS)
        or upper_name.endswith("_TOKEN")
        or upper_name in {"GITHUB_TOKEN", "GH_TOKEN"}
    )


def _safe_cli_environment() -> dict[str, str]:
    return {
        name: value
        for name, value in os.environ.items()
        if not _is_secret_environment_name(name)
    }


def _redact_environment_values(text: str) -> str:
    redacted = text
    for name, value in os.environ.items():
        if value and _is_secret_environment_name(name):
            redacted = redacted.replace(value, "[REDACTED]")
    return redacted


def _codex_usage(output: str) -> tuple[int | None, int | None]:
    input_tokens = None
    output_tokens = None
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "turn.completed":
            continue
        usage = event.get("usage") or {}
        input_tokens = _usage_value(usage, "input_tokens")
        output_tokens = _usage_value(usage, "output_tokens")
    return input_tokens, output_tokens


def _claude_usage(
    payload: dict[str, Any], requested_model: str
) -> tuple[int | None, int | None]:
    model_usage = payload.get("modelUsage") or {}
    requested = requested_model.lower()
    matching_usage = []
    for name, usage in model_usage.items():
        label = str(name).lower()
        canonical = str((usage or {}).get("canonicalModel", "")).lower()
        if requested in {"sonnet", "claude-sonnet"}:
            matches = "sonnet" in label or "sonnet" in canonical
        else:
            matches = requested in label or requested in canonical
        if matches:
            matching_usage.append(usage)

    usage_entries = matching_usage or list(model_usage.values())
    if usage_entries:
        input_tokens = 0
        output_tokens = 0
        saw_input = False
        saw_output = False
        for usage in usage_entries:
            uncached = _usage_value(usage, "inputTokens")
            cache_read = _usage_value(usage, "cacheReadInputTokens")
            cache_created = _usage_value(usage, "cacheCreationInputTokens")
            for value in (uncached, cache_read, cache_created):
                if value is not None:
                    input_tokens += value
                    saw_input = True
            output = _usage_value(usage, "outputTokens")
            if output is not None:
                output_tokens += output
                saw_output = True
        if saw_input or saw_output:
            return (
                input_tokens if saw_input else None,
                output_tokens if saw_output else None,
            )

    usage = payload.get("usage") or {}
    input_values = (
        _usage_value(usage, "input_tokens"),
        _usage_value(usage, "cache_read_input_tokens"),
        _usage_value(usage, "cache_creation_input_tokens"),
    )
    input_tokens = sum(value for value in input_values if value is not None)
    output_tokens = _usage_value(usage, "output_tokens")
    return (
        input_tokens if any(value is not None for value in input_values) else None,
        output_tokens,
    )


class CodexCLIProvider:
    provider = "codex-cli"

    def __init__(
        self,
        model: str,
        command: str = "codex",
        timeout: int = 600,
    ) -> None:
        self.model = model
        self.command = command
        self.timeout = timeout

    def generate(self, prompt: str) -> ModelResponse:
        with tempfile.TemporaryDirectory(prefix="coding-benchmark-codex-") as directory:
            output_path = Path(directory) / "last-message.txt"
            command = [
                self.command,
                "exec",
                "--model",
                self.model,
                "--sandbox",
                "read-only",
                "--ephemeral",
                "--skip-git-repo-check",
                "--ignore-user-config",
                "--color",
                "never",
                "--json",
                "--output-last-message",
                str(output_path),
                "-",
            ]
            completed = _run_local_cli(
                command,
                prompt,
                cwd=directory,
                timeout=self.timeout,
            )
            if output_path.is_file():
                response_text = output_path.read_text(encoding="utf-8")
            else:
                response_text = completed.stdout
            if not response_text.strip():
                raise ProviderError("Codex CLI returned no final message")
            input_tokens, output_tokens = _codex_usage(completed.stdout)
            return ModelResponse(
                text=_redact_environment_values(response_text),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )


class ClaudeCLIProvider:
    provider = "claude-cli"

    def __init__(
        self,
        model: str,
        command: str = "claude",
        timeout: int = 600,
    ) -> None:
        self.model = model
        self.command = command
        self.timeout = timeout

    def generate(self, prompt: str) -> ModelResponse:
        command = [
            self.command,
            "--print",
            "--model",
            self.model,
            "--output-format",
            "json",
            "--no-session-persistence",
            "--safe-mode",
            "--tools",
            "",
            "--permission-mode",
            "plan",
        ]
        with tempfile.TemporaryDirectory(prefix="coding-benchmark-claude-") as directory:
            completed = _run_local_cli(
                command,
                prompt,
                cwd=directory,
                timeout=self.timeout,
            )

        response_text = completed.stdout.strip()
        input_tokens = None
        output_tokens = None
        try:
            payload = json.loads(response_text)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            response_text = str(payload.get("result") or payload.get("text") or "")
            input_tokens, output_tokens = _claude_usage(payload, self.model)

        if not response_text.strip():
            raise ProviderError("Claude CLI returned no final message")
        return ModelResponse(
            text=_redact_environment_values(response_text),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )


def _run_local_cli(
    command: list[str],
    prompt: str,
    *,
    cwd: str,
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    safe_prompt = _redact_environment_values(
        SYSTEM_INSTRUCTIONS
        + "\n\n"
        + LOCAL_CLI_OUTPUT_INSTRUCTIONS
        + "\n\n"
        + prompt
    )
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=_safe_cli_environment(),
            input=safe_prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ProviderError(f"Local CLI is not installed: {command[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ProviderError(f"Local CLI timed out after {timeout} seconds") from exc

    if completed.returncode != 0:
        detail = _redact_environment_values(
            (completed.stderr or completed.stdout or "").strip()
        )
        detail = detail[-1000:] if detail else "no diagnostic output"
        raise ProviderError(
            f"Local CLI failed with exit code {completed.returncode}: {detail}"
        )
    return completed


def make_provider(
    provider: str,
    model: str,
    *,
    reasoning_effort: str | None = None,
) -> ModelProvider:
    provider = provider.lower()
    if provider == "openai":
        return OpenAIProvider(model, reasoning_effort=reasoning_effort)
    if provider == "anthropic":
        return AnthropicProvider(model)
    raise ValueError(f"Unsupported provider: {provider}")


def make_cli_provider(
    provider: str,
    model: str,
    *,
    timeout: int = 600,
) -> ModelProvider:
    provider = provider.lower()
    if provider == "codex":
        return CodexCLIProvider(model, timeout=timeout)
    if provider in {"claude", "anthropic"}:
        return ClaudeCLIProvider(model, timeout=timeout)
    raise ValueError(f"Unsupported local CLI provider: {provider}")
