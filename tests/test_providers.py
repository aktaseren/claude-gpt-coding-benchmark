import json
import subprocess
from pathlib import Path

import benchmark.providers as providers


def test_safe_cli_environment_removes_secret_values(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-secret")
    monkeypatch.setenv("SAFE_SETTING", "kept")

    environment = providers._safe_cli_environment()

    assert "OPENAI_API_KEY" not in environment
    assert "ANTHROPIC_API_KEY" not in environment
    assert environment["SAFE_SETTING"] == "kept"
    assert "[REDACTED]" in providers._redact_environment_values(
        "openai-secret anthropic-secret"
    )


def test_codex_cli_provider_uses_ephemeral_read_only_mode(monkeypatch):
    def fake_run(command, prompt, *, cwd, timeout):
        assert command[:2] == ["codex", "exec"]
        assert "--sandbox" in command
        assert "read-only" in command
        assert "--ephemeral" in command
        output_path = Path(command[command.index("--output-last-message") + 1])
        output_path.write_text("--- a/app.py\n+++ b/app.py\n", encoding="utf-8")
        stdout = json.dumps(
            {
                "type": "turn.completed",
                "usage": {"input_tokens": 12, "output_tokens": 8},
            }
        )
        return subprocess.CompletedProcess(command, 0, stdout, "")

    monkeypatch.setattr(providers, "_run_local_cli", fake_run)
    response = providers.CodexCLIProvider("gpt-5.6-luna").generate("task")

    assert response.text.startswith("--- a/app.py")
    assert response.input_tokens == 12
    assert response.output_tokens == 8


def test_claude_cli_provider_extracts_json_result(monkeypatch):
    def fake_run(command, prompt, *, cwd, timeout):
        assert command[:4] == ["claude", "--print", "--model", "sonnet"]
        payload = {
            "result": "--- a/app.py\n+++ b/app.py\n",
            "usage": {"input_tokens": 2, "output_tokens": 8},
            "modelUsage": {
                "claude-sonnet-4-6": {
                    "inputTokens": 4,
                    "cacheReadInputTokens": 10,
                    "cacheCreationInputTokens": 20,
                    "outputTokens": 8,
                    "canonicalModel": "claude-sonnet-4-6",
                },
                "claude-haiku-4-5": {
                    "inputTokens": 1000,
                    "outputTokens": 1000,
                    "canonicalModel": "claude-haiku-4-5",
                },
            },
        }
        return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")

    monkeypatch.setattr(providers, "_run_local_cli", fake_run)
    response = providers.ClaudeCLIProvider("sonnet").generate("task")

    assert response.text.startswith("--- a/app.py")
    assert response.input_tokens == 34
    assert response.output_tokens == 8
