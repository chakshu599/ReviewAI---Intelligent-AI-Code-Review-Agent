import pytest

from reviewai.utils.validators import (
    InputValidationError,
    validate_diff_text,
    validate_github_reference,
    validate_upload,
)

DIFF = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-x\n+y\n"


def test_validate_upload_rejects_unsupported_extension_and_encoding():
    with pytest.raises(InputValidationError, match="Only .diff"):
        validate_upload("code.txt", DIFF.encode())
    with pytest.raises(InputValidationError, match="UTF-8"):
        validate_upload("bad.diff", b"\xff")


def test_validate_diff_checks_size(monkeypatch):
    from reviewai.utils import validators

    monkeypatch.setattr(validators, "get_settings", lambda: type("S", (), {"max_diff_bytes": 20, "max_files": 100})())
    with pytest.raises(InputValidationError, match="limit"):
        validate_diff_text(DIFF)


def test_github_reference_accepts_public_repo_and_supported_refs():
    assert validate_github_reference("https://github.com/acme/demo", "abcdef1234567") == (
        "acme", "demo", "abcdef1234567"
    )
    assert validate_github_reference("https://github.com/acme/demo.git", "PR:42") == (
        "acme", "demo", "pr:42"
    )


@pytest.mark.parametrize("url", [
    "http://github.com/acme/demo",
    "https://github.com.evil.example/acme/demo",
    "https://github.com/acme/demo/tree/main",
    "https://user:pass@github.com/acme/demo",
])
def test_github_reference_rejects_unsafe_urls(url):
    with pytest.raises(InputValidationError):
        validate_github_reference(url, "abcdef1234567")
