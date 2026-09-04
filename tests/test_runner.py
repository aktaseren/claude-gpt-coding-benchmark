import subprocess

from benchmark.models import BenchmarkTask, ModelResponse
from benchmark.runner import run_model


class FakeProvider:
    provider = "fake"
    model = "test-model"

    def generate(self, prompt):
        assert "Fix addition" in prompt
        return ModelResponse(
            text=(
                "\x60\x60\x60diff\n"
                "--- a/calculator.py\n"
                "+++ b/calculator.py\n"
                "@@ -1,2 +1,2 @@\n"
                " def add(a, b):\n"
                "-    return a - b\n"
                "+    return a + b\n"
                "\x60\x60\x60\n"
            ),
            input_tokens=100,
            output_tokens=20,
        )


def test_run_model_applies_patch_in_isolated_workspace(tmp_path):
    workspace = tmp_path / "repo"
    workspace.mkdir()
    calculator = workspace / "calculator.py"
    calculator.write_text(
        "def add(a, b):\n"
        "    return a - b\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init"], cwd=workspace, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "benchmark@example.test"],
        cwd=workspace,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Benchmark Test"],
        cwd=workspace,
        check=True,
    )
    subprocess.run(["git", "add", "calculator.py"], cwd=workspace, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial calculator"],
        cwd=workspace,
        check=True,
        capture_output=True,
    )

    task = BenchmarkTask(
        task_id="calculator-001",
        title="Fix addition",
        prompt="Make add return the sum of its arguments.",
        test_command=(
            "python -c "
            "\"from calculator import add; assert add(2, 3) == 5\""
        ),
    )

    result = run_model(task, workspace, FakeProvider(), timeout=30)

    assert result.patch_applied is True
    assert result.tests_passed is True
    assert result.input_tokens == 100
    assert result.output_tokens == 20
    assert "return a - b" in calculator.read_text(encoding="utf-8")
