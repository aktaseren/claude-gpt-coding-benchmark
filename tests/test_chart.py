from benchmark.chart import render_svg, write_svg


def test_render_svg_has_pending_state_without_results():
    svg = render_svg({"task": {"title": "Demo task"}, "results": []})

    assert "Live benchmark pending" in svg
    assert "No live benchmark results" in svg


def test_render_svg_includes_measured_model_metrics(tmp_path):
    payload = {
        "task": {"title": "Fix calculator"},
        "results": [
            {
                "provider": "openai",
                "model": "gpt-5.6-luna",
                "tests_passed": True,
                "patch_applied": True,
                "elapsed_seconds": 1.25,
                "input_tokens": 120,
                "output_tokens": 45,
            },
            {
                "provider": "anthropic",
                "model": "claude-sonnet-test",
                "tests_passed": False,
                "patch_applied": True,
                "elapsed_seconds": 2.5,
                "input_tokens": 140,
                "output_tokens": 60,
            },
        ],
    }

    output = tmp_path / "chart.svg"
    write_svg(payload, output)
    svg = output.read_text(encoding="utf-8")

    assert "gpt-5.6-luna" in svg
    assert "claude-sonnet-test" in svg
    assert "1.25s" in svg
    assert "140" in svg
    assert "Recorded metrics only" in svg
