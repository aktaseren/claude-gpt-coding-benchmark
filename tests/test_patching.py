from benchmark.patching import extract_unified_diff


def test_extract_unified_diff_from_diff_fence():
    response = (
        "I made the change:\n"
        "\x60\x60\x60diff\n"
        "--- a/example.py\n"
        "+++ b/example.py\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        "+new\n"
        "\x60\x60\x60\n"
    )

    patch = extract_unified_diff(response)

    assert patch is not None
    assert patch.startswith("--- a/example.py")
    assert "+new" in patch


def test_extract_unified_diff_returns_none_for_explanation_only():
    assert extract_unified_diff("The code is already correct.") is None
