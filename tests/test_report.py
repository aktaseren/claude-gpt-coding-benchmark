from benchmark.report import render_public_batch_markdown


def test_public_batch_report_excludes_private_result_fields():
    payload = {
        "task": {
            "title": "Public task",
            "source": {
                "repository": "owner/repo",
                "url": "https://github.com/owner/repo",
            },
        },
        "results": [
            {
                "provider": "codex-cli",
                "model": "gpt-5.6-luna",
                "status": "passed",
                "patch_applied": True,
                "tests_passed": True,
                "elapsed_seconds": 1.0,
                "patch": "PRIVATE PATCH CONTENT",
                "test_output": "PRIVATE TEST OUTPUT",
                "error": "PRIVATE ERROR",
            }
        ],
    }

    report = render_public_batch_markdown([payload])

    assert "owner/repo" in report
    assert "gpt-5.6-luna" in report
    assert "PRIVATE PATCH CONTENT" not in report
    assert "PRIVATE TEST OUTPUT" not in report
    assert "PRIVATE ERROR" not in report
