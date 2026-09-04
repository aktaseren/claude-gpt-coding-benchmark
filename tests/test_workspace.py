from benchmark.workspace import collect_workspace


def test_workspace_snapshot_excludes_secret_files(tmp_path):
    (tmp_path / "app.py").write_text("print('safe')", encoding="utf-8")
    (tmp_path / ".env").write_text("API_KEY=do-not-send", encoding="utf-8")
    (tmp_path / "private.pem").write_text("private", encoding="utf-8")

    snapshot = collect_workspace(tmp_path)

    assert "app.py" in snapshot
    assert "safe" in snapshot
    assert ".env" not in snapshot
    assert "do-not-send" not in snapshot
    assert "private.pem" not in snapshot
