from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from .models import BenchmarkTask


class GitHubAPIError(RuntimeError):
    """Raised when the GitHub REST API cannot provide the requested data."""


def split_repository(repository: str) -> tuple[str, str]:
    parts = repository.strip().split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError("Repository must use the OWNER/REPOSITORY form")
    return parts[0], parts[1]


class GitHubClient:
    def __init__(
        self,
        token: str | None = None,
        api_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.api_url = (
            api_url or os.getenv("GITHUB_API_URL") or "https://api.github.com"
        ).rstrip("/")
        self.timeout = timeout

    def _get(self, path: str, query: dict[str, str] | None = None) -> Any:
        url = f"{self.api_url}{path}"
        if query:
            url += "?" + urlencode(query)

        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "claude-gpt-coding-benchmark",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        request = Request(url, headers=headers, method="GET")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise GitHubAPIError(
                f"GitHub API returned HTTP {exc.code}: {detail[:500]}"
            ) from exc
        except URLError as exc:
            raise GitHubAPIError(f"Could not reach GitHub API: {exc.reason}") from exc

    def get_issue(self, repository: str, number: int) -> dict[str, Any]:
        owner, name = split_repository(repository)
        path = f"/repos/{quote(owner)}/{quote(name)}/issues/{int(number)}"
        issue = self._get(path)
        if "pull_request" in issue:
            raise GitHubAPIError(
                f"{repository}#{number} is a pull request, not an issue"
            )
        return issue

    def list_issues(
        self,
        repository: str,
        *,
        label: str | None = None,
        state: str = "open",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        owner, name = split_repository(repository)
        query = {
            "state": state,
            "per_page": str(max(1, min(limit, 100))),
        }
        if label:
            query["labels"] = label
        path = f"/repos/{quote(owner)}/{quote(name)}/issues"
        items = self._get(path, query)
        return [item for item in items if "pull_request" not in item][:limit]

    @staticmethod
    def issue_to_task(
        repository: str,
        issue: dict[str, Any],
        *,
        test_command: str,
        setup_command: str | None = None,
    ) -> BenchmarkTask:
        number = issue.get("number")
        title = str(issue.get("title") or f"Issue {number}")
        body = str(issue.get("body") or "").strip()
        prompt = (
            "Implement the requested change described by this GitHub issue. "
            "Keep the change focused, preserve existing behavior outside the "
            "task, and make the supplied tests pass.\n\n"
            f"Issue title: {title}\n\n"
            f"Issue description:\n{body or '(No issue description was provided.)'}"
        )
        return BenchmarkTask(
            task_id=f"{repository}#{number}",
            title=title,
            prompt=prompt,
            test_command=test_command,
            setup_command=setup_command,
            source={
                "kind": "github_issue",
                "repository": repository,
                "issue": number,
                "url": issue.get("html_url"),
            },
        )
