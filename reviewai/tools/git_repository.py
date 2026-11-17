"""Optional local-working-tree diff helper backed by GitPython."""

import re
from pathlib import Path

from git import Repo

from reviewai.core.config import get_settings
from reviewai.utils.error_handler import ReviewAIError


class GitRepositoryError(ReviewAIError):
    """Local Git repository or base reference is invalid."""


def create_working_tree_diff(repository_path: str | Path, base_ref: str = "HEAD") -> str:
    """Return a bounded diff against a validated local ref; no submitted code is executed."""
    if not re.fullmatch(r"(?:HEAD|[0-9a-fA-F]{7,40}|[A-Za-z0-9][A-Za-z0-9._/-]{0,180})", base_ref):
        raise GitRepositoryError("Base ref must be HEAD, a commit SHA, or a simple branch name.")
    if ".." in base_ref or base_ref.endswith((".", "/")):
        raise GitRepositoryError("Base ref contains an unsupported Git revision expression.")
    try:
        repo = Repo(repository_path, search_parent_directories=True)
        diff = repo.git.diff(base_ref, "--")
    except Exception as exc:
        # GitPython surfaces several platform-specific command and path exceptions.
        raise GitRepositoryError("Could not read a diff from that local Git repository.") from exc
    if len(diff.encode("utf-8")) > get_settings().max_diff_bytes:
        raise GitRepositoryError("Local Git diff exceeds the configured input size limit.")
    if not diff.strip():
        raise GitRepositoryError("The local working tree has no diff against the selected base ref.")
    return diff
