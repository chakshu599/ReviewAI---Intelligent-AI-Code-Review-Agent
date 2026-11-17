"""Heuristic test-gap prompts based on changed production code."""

from pathlib import PurePosixPath

from reviewai.core.schemas import Category, Finding, ParsedDiff, Severity

_TEST_MARKERS = ("test_", "_test.", ".spec.", ".test.", "tests/")


def test_gap_analysis(parsed: ParsedDiff) -> list[Finding]:
    """Suggest test coverage only when a production file changed without a test file."""
    changed_paths = [file.display_path.replace("\\", "/") for file in parsed.files]
    has_test_change = any(any(marker in path.lower() for marker in _TEST_MARKERS) for path in changed_paths)
    if has_test_change:
        return []
    findings: list[Finding] = []
    for file in parsed.files:
        path = file.display_path.replace("\\", "/")
        suffix = PurePosixPath(path).suffix.lower()
        if not suffix or any(marker in path.lower() for marker in _TEST_MARKERS):
            continue
        added = next((line for line in file.changed_lines if line.change_type == "added"), None)
        if not added:
            continue
        findings.append(Finding(
            finding_id=f"TST-{len(findings) + 1:03d}",
            category=Category.TESTING,
            severity=Severity.LOW,
            file_name=path,
            line_number=added.line_number,
            title="Consider adding tests for this production change",
            explanation="A production file changed, but no test file appears in this diff. The diff alone cannot establish whether coverage already exists.",
            why_it_matters="Regression tests can preserve the new behavior and expose edge cases in future changes.",
            suggested_fix="Add or update focused tests for the changed behavior, including relevant boundary and failure cases.",
            confidence=0.6,
        ))
    return findings


# Pytest's default discovery matches both this module and the public tool name.
test_gap_analysis.__test__ = False
