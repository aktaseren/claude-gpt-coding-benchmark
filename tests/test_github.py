import json
from unittest.mock import patch

from benchmark.github import GitHubClient, split_repository


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_split_repository_rejects_invalid_values():
    assert split_repository("owner/repository") == ("owner", "repository")

    try:
        split_repository("repository")
    except ValueError as exc:
        assert "OWNER/REPOSITORY" in str(exc)
    else:
        raise AssertionError("Expected invalid repository to raise ValueError")


@patch("benchmark.github.urlopen")
def test_get_issue_uses_github_api_headers(mock_urlopen):
    mock_urlopen.return_value = FakeResponse(
        {
            "number": 7,
            "title": "Improve parsing",
            "body": "Handle empty input.",
            "html_url": "https://github.com/owner/repository/issues/7",
        }
    )

    issue = GitHubClient(
        token="test-token",
        api_url="https://api.example.test",
    ).get_issue("owner/repository", 7)

    assert issue["number"] == 7
    request = mock_urlopen.call_args.args[0]
    assert request.full_url == "https://api.example.test/repos/owner/repository/issues/7"
    assert request.get_header("Authorization") == "Bearer test-token"
    assert request.get_header("X-github-api-version") == "2022-11-28"


def test_issue_to_task_preserves_issue_context():
    task = GitHubClient.issue_to_task(
        "owner/repository",
        {
            "number": 7,
            "title": "Improve parsing",
            "body": "Handle empty input.",
            "html_url": "https://github.com/owner/repository/issues/7",
        },
        test_command="python -m pytest -q",
    )

    assert task.task_id == "owner/repository#7"
    assert "Handle empty input." in task.prompt
    assert task.source["issue"] == 7
