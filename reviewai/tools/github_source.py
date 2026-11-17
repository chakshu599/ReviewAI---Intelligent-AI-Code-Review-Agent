"""Fetch bounded diffs for public GitHub commits or pull requests."""

import httpx

from reviewai.core.config import get_settings
from reviewai.utils.error_handler import ReviewAIError
from reviewai.utils.validators import validate_github_reference


class GitHubSourceError(ReviewAIError):
    """Public GitHub reference could not be fetched."""


def fetch_public_github_diff(repository_url: str, revision: str) -> str:
    """Fetch a commit/PR diff through the public GitHub API; never clone or execute code."""
    owner, repository, ref = validate_github_reference(repository_url, revision)
    settings = get_settings()
    headers = {"Accept": "application/vnd.github.v3.diff", "User-Agent": "ReviewAI/1.0"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    base = f"https://api.github.com/repos/{owner}/{repository}"
    timeout = httpx.Timeout(15.0, connect=5.0)
    try:
        with httpx.Client(timeout=timeout, follow_redirects=False, headers=headers) as client:
            repo_response = client.get(base, headers={"Accept": "application/vnd.github+json"})
            if repo_response.status_code == 404:
                raise GitHubSourceError("Repository was not found or is not public.")
            repo_response.raise_for_status()
            if repo_response.json().get("private", True):
                raise GitHubSourceError("Private repositories are not supported.")
            if ref.startswith("pr:"):
                number = ref.split(":", 1)[1]
                endpoint = f"{base}/pulls/{number}"
            else:
                endpoint = f"{base}/commits/{ref}"
            response = client.get(endpoint, headers={"Accept": "application/vnd.github.v3.diff"})
            if response.status_code == 404:
                raise GitHubSourceError("Commit or pull request was not found in this public repository.")
            response.raise_for_status()
            content = response.text
    except GitHubSourceError:
        raise
    except (httpx.HTTPError, ValueError) as exc:
        raise GitHubSourceError("GitHub could not provide this public diff. Check the URL, revision, or API rate limit.") from exc
    if not content.strip():
        raise GitHubSourceError("GitHub returned an empty diff (the change may contain no patchable files).")
    if len(content.encode("utf-8")) > settings.max_diff_bytes:
        raise GitHubSourceError("GitHub diff exceeds the configured input size limit.")
    return content
