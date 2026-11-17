"""Finding normalization and downloadable report rendering."""

import json
import re
from collections.abc import Iterable

from reviewai.core.risk_scoring import calculate_risk
from reviewai.core.schemas import Finding, ParsedDiff, ReviewReport


def deduplicate_findings(findings: Iterable[Finding]) -> list[Finding]:
    """Remove duplicates using location/category/title, keeping the strongest signal."""
    selected: dict[tuple[object, ...], Finding] = {}
    for finding in findings:
        key = (
            finding.category,
            finding.file_name.casefold().replace("\\", "/"),
            finding.line_number,
            re.sub(r"\W+", " ", finding.title.casefold()).strip(),
        )
        previous = selected.get(key)
        if previous is None or finding.confidence > previous.confidence:
            selected[key] = finding
    ordered = sorted(selected.values(), key=lambda item: (item.file_name, item.line_number or 0, item.category.value, item.title))
    return [finding.model_copy(update={"finding_id": f"F-{index:03d}"}) for index, finding in enumerate(ordered, 1)]


def generate_report(parsed: ParsedDiff, findings: Iterable[Finding], summary: str) -> ReviewReport:
    """Construct the final validated report from deterministic and AI findings."""
    normalized = deduplicate_findings(findings)
    return ReviewReport(
        summary=summary,
        findings=normalized,
        risk=calculate_risk(normalized),
        files_reviewed=len(parsed.files),
        additions=parsed.additions,
        deletions=parsed.deletions,
    )


def report_as_json(report: ReviewReport) -> str:
    return report.model_dump_json(indent=2)


def report_as_markdown(report: ReviewReport) -> str:
    lines = [
        "# ReviewAI Code Review",
        "",
        f"**Risk:** {report.risk.level.value} ({report.risk.score}/100, heuristic)",
        f"**Files:** {report.files_reviewed} · **Additions:** {report.additions} · **Deletions:** {report.deletions}",
        "",
        "> This score prioritizes review effort. It is not a verified security assessment.",
        "",
        "## Summary",
        "",
        report.summary,
        "",
        "## Findings",
    ]
    if not report.findings:
        lines.extend(["", "No actionable findings were returned. This does not prove the change is bug-free or secure."])
    for finding in report.findings:
        location = f"{finding.file_name}:{finding.line_number}" if finding.line_number else finding.file_name
        lines.extend([
            "",
            f"### [{finding.severity.value}] {finding.title}",
            "",
            f"- **ID:** {finding.finding_id} · **Category:** {finding.category.value} · **Location:** `{location}` · **Confidence:** {finding.confidence:.0%}",
            f"- **Issue:** {finding.explanation}",
            f"- **Why it matters:** {finding.why_it_matters}",
            f"- **Suggested fix:** {finding.suggested_fix}",
        ])
    lines.extend(["", "## Risk method", "", report.risk.explanation, ""])
    return "\n".join(lines)
