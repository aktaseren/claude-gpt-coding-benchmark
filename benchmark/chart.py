from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any


METRICS = (
    ("Tests passed (yes/no)", "tests_passed"),
    ("Patch applied (yes/no)", "patch_applied"),
    ("Elapsed seconds", "elapsed_seconds"),
    ("Input tokens", "input_tokens"),
    ("Output tokens", "output_tokens"),
)
COLORS = ("#4f46e5", "#d97706", "#059669", "#dc2626")


def _numeric_value(result: dict[str, Any], key: str) -> float | None:
    if key in {"tests_passed", "patch_applied"}:
        value = result.get(key)
        return 1.0 if value is True else 0.0 if value is False else None

    value = result.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _display_value(value: float | None, key: str) -> str:
    if value is None:
        return "n/a"
    if key in {"tests_passed", "patch_applied"}:
        return "yes" if value else "no"
    if key == "elapsed_seconds":
        return f"{value:.2f}s"
    return f"{int(value):,}"


def _model_label(result: dict[str, Any]) -> str:
    provider = str(result.get("provider", "provider"))
    model = str(result.get("model", "model"))
    return f"{provider}: {model}"


def _text(x: int, y: int, value: str, *, size: int = 14, fill: str = "#172033") -> str:
    return (
        f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" '
        f'font-size="{size}px" fill="{fill}">{escape(value)}</text>'
    )


def render_svg(payload: dict[str, Any]) -> str:
    results = list(payload.get("results", []))
    task = payload.get("task") or {}
    task_title = str(task.get("title", "Coding benchmark"))
    model_names = " vs ".join(_model_label(result) for result in results)
    title = model_names or "GPT-5.6 Luna vs Claude"

    if not results:
        return "\n".join(
            [
                '<svg xmlns="http://www.w3.org/2000/svg" role="img" '
                'aria-labelledby="title description" width="1000" height="300" '
                'viewBox="0 0 1000 300">',
                '<title id="title">GPT-5.6 Luna vs Claude benchmark pending</title>',
                '<desc id="description">No live benchmark results have been recorded yet.</desc>',
                '<rect width="1000" height="300" rx="16" fill="#f8fafc"/>',
                _text(42, 58, "GPT-5.6 Luna vs Claude", size=26),
                _text(42, 100, task_title, size=16, fill="#475569"),
                _text(42, 166, "Live benchmark pending", size=23, fill="#4f46e5"),
                _text(
                    42,
                    208,
                    "Run compare, then chart, to populate this image with measured results.",
                    size=15,
                    fill="#475569",
                ),
                "</svg>",
            ]
        )

    row_height = 25
    block_height = 48 + row_height * len(results)
    width = 1000
    height = 92 + block_height * len(METRICS) + 22
    bar_x = 460
    bar_width = 390
    value_x = 875
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-labelledby="title description" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        f'<title id="title">{escape(title)} coding benchmark</title>',
        f'<desc id="description">Measured patch, test, timing, and token metrics for the selected models.</desc>',
        f'<rect width="{width}" height="{height}" rx="16" fill="#f8fafc"/>',
        _text(28, 38, title, size=24),
        _text(28, 67, task_title, size=15, fill="#475569"),
        _text(
            28,
            88,
            "Recorded metrics only; this is not a universal model score.",
            size=13,
            fill="#64748b",
        ),
    ]

    y = 101
    for metric_title, key in METRICS:
        values = [_numeric_value(result, key) for result in results]
        available = [value for value in values if value is not None]
        maximum = max(available, default=0.0)
        parts.append(_text(28, y + 20, metric_title, size=15, fill="#334155"))

        for index, (result, value) in enumerate(zip(results, values)):
            row_y = y + 43 + row_height * index
            parts.append(
                _text(250, row_y + 4, _model_label(result), size=12, fill="#475569")
            )
            parts.append(
                f'<rect x="{bar_x}" y="{row_y - 9}" width="{bar_width}" '
                'height="14" rx="7" fill="#e2e8f0"/>'
            )
            if value is not None and maximum > 0:
                rendered_width = max(4.0, bar_width * value / maximum)
                parts.append(
                    f'<rect x="{bar_x}" y="{row_y - 9}" width="{rendered_width:.1f}" '
                    f'height="14" rx="7" fill="{COLORS[index % len(COLORS)]}"/>'
                )
            parts.append(
                _text(
                    value_x,
                    row_y + 4,
                    _display_value(value, key),
                    size=12,
                    fill="#172033",
                )
            )
        y += block_height

    parts.append("</svg>")
    return "\n".join(parts)


def write_svg(payload: dict[str, Any], output: str | Path) -> None:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_svg(payload), encoding="utf-8")
