"""Input validation for untrusted diffs and public GitHub references."""

import re
from urllib.parse import urlparse

from reviewai.core.config import get_settings
from reviewai.core.schemas import ParsedDiff


class InputValidationError(ValueError):
    """Raised when input cannot safely be reviewed."""


def validate_diff_text(diff_text: str) -> str:
    """Validate byte size and basic unified-diff shape without executing input."""
    if not isinstance(diff_text, str) or not diff_text.strip():
        raise InputValidationError("The diff is empty. Paste or upload a unified diff.")
    encoded_size = len(diff_text.encode("utf-8"))
    if encoded_size > get_settings().max_diff_bytes:
        raise InputValidationError(
            f"Diff is {encoded_size:,} bytes; the limit is {get_settings().max_diff_bytes:,} bytes."
        )
    if not ("diff --git " in diff_text or "--- " in diff_text and "+++ " in diff_text):
        raise InputValidationError("Input does not look like a unified Git diff.")
    return diff_text


def validate_upload(filename: str, payload: bytes) -> str:
    """Accept only bounded UTF-8 .diff/.patch uploads."""
    if not filename.lower().endswith((".diff", ".patch")):
        raise InputValidationError("Only .diff and .patch files are supported.")
    if len(payload) > get_settings().max_diff_bytes:
        raise InputValidationError("Uploaded diff exceeds the configured size limit.")
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InputValidationError("Diff files must be UTF-8 text.") from exc
    return validate_diff_text(text)


def validate_github_reference(repository_url: str, revision: str) -> tuple[str, str, str]:
    """Allow only canonical public github.com owner/repository and a SHA or PR number."""
    parsed = urlparse(repository_url.strip())
    try:
        port = parsed.port
    except ValueError as exc:
        raise InputValidationError("Repository URL contains an invalid port.") from exc
    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or port
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise InputValidationError("Use a public HTTPS URL on github.com.")
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) != 2 or any(part in {".", ".."} for part in parts):
        raise InputValidationError("Repository URL must be https://github.com/OWNER/REPOSITORY.")
    owner, repository = parts
    repository = repository.removesuffix(".git")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", owner) or not re.fullmatch(
        r"[A-Za-z0-9_.-]{1,100}", repository
    ):
        raise InputValidationError("Repository URL contains an invalid owner or repository name.")
    revision = revision.strip()
    if revision.lower().startswith("pr:"):
        pull_number = revision[3:]
        if not pull_number.isdigit() or int(pull_number) < 1:
            raise InputValidationError("PR reference must use PR:<positive number>.")
        return owner, repository, f"pr:{int(pull_number)}"
    if not re.fullmatch(r"[0-9a-fA-F]{7,40}", revision):
        raise InputValidationError("Revision must be a commit SHA (7–40 hex characters) or PR:<number>.")
    return owner, repository, revision.lower()


def validate_parsed_diff(parsed: ParsedDiff) -> ParsedDiff:
    """Enforce a file-count limit after parsing."""
    limit = get_settings().max_files
    if len(parsed.files) > limit:
        raise InputValidationError(f"Diff contains {len(parsed.files)} files; the limit is {limit}.")
    return parsed
