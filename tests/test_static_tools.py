from pathlib import Path

from reviewai.tools.diff_parser import parse_git_diff
from reviewai.tools.static_security_scanner import security_scan


def test_sample_diff_security_findings_are_based_on_changed_lines():
    path = Path(__file__).parents[1] / "sample_diffs" / "python_example.diff"
    findings = security_scan(parse_git_diff(path.read_text(encoding="utf-8")))
    assert findings
    assert any("SQL" in finding.title for finding in findings)
    assert all(finding.line_number for finding in findings)
