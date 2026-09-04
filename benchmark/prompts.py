from .models import BenchmarkTask


SYSTEM_INSTRUCTIONS = """You are a careful software engineer participating in a
reproducible coding benchmark. Solve only the requested task. Inspect the
provided repository snapshot, preserve unrelated behavior, and do not change
tests unless the task explicitly asks for it.

Return only one unified git diff inside a diff code fence. The diff must be
relative to the repository root and must be directly applicable with git apply.
If no change is needed, return an empty diff. Do not include explanations
outside the diff."""


def build_prompt(task: BenchmarkTask, workspace_snapshot: str) -> str:
    return (
        f"Task: {task.title}\n\n"
        f"Instructions:\n{task.prompt}\n\n"
        "Repository snapshot follows. Use it as the only source of project "
        "context for this run.\n\n"
        f"{workspace_snapshot}"
    )
