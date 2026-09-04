from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class BenchmarkTask:
    task_id: str
    title: str
    prompt: str
    test_command: str
    setup_command: str | None = None
    source: dict[str, Any] = field(default_factory=dict)
    max_files: int = 80
    max_file_bytes: int = 120_000
    include_paths: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "BenchmarkTask":
        required = ("task_id", "title", "prompt", "test_command")
        missing = [key for key in required if not value.get(key)]
        if missing:
            raise ValueError(
                "Task is missing required field(s): " + ", ".join(missing)
            )

        return cls(
            task_id=str(value["task_id"]),
            title=str(value["title"]),
            prompt=str(value["prompt"]),
            test_command=str(value["test_command"]),
            setup_command=value.get("setup_command"),
            source=dict(value.get("source") or {}),
            max_files=int(value.get("max_files", 80)),
            max_file_bytes=int(value.get("max_file_bytes", 120_000)),
            include_paths=tuple(str(path) for path in value.get("include_paths", ())),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ModelResponse:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


@dataclass
class ModelResult:
    provider: str
    model: str
    elapsed_seconds: float = 0.0
    patch: str = ""
    patch_applied: bool = False
    tests_passed: bool = False
    test_returncode: int | None = None
    test_output: str = ""
    input_tokens: int | None = None
    output_tokens: int | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def status(self) -> str:
        if self.tests_passed:
            return "passed"
        if self.patch_applied:
            return "tests_failed"
        if self.error:
            return "error"
        return "no_patch"
