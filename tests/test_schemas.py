import pytest
from pydantic import ValidationError

from reviewai.core.schemas import Category, Finding, ReviewReport, Severity


def valid_finding(**overrides):
    data = {
        "finding_id": "F-1",
        "category": Category.BUG,
        "severity": Severity.MEDIUM,
        "file_name": "src/example.py",
        "line_number": 4,
        "title": "Incorrect boundary check",
        "explanation": "The changed comparison excludes the valid final item.",
        "why_it_matters": "Users cannot retrieve that item from the collection.",
        "suggested_fix": "Use an inclusive comparison and add a final-item test.",
        "confidence": 0.9,
    }
    data.update(overrides)
    return Finding.model_validate(data)


def test_finding_accepts_valid_structured_response():
    finding = valid_finding()
    assert finding.category == Category.BUG
    assert finding.confidence == 0.9


def test_finding_rejects_invalid_severity_and_extra_fields():
    with pytest.raises(ValidationError):
        valid_finding(severity="Urgent")
    with pytest.raises(ValidationError):
        valid_finding(extra_field="not allowed")


def test_review_report_rejects_duplicate_ids():
    from reviewai.core.schemas import RiskAssessment, SeverityCounts

    risk = RiskAssessment(
        score=0,
        level=Severity.LOW,
        counts=SeverityCounts(critical=0, high=0, medium=0, low=0),
        explanation="No findings were found by the heuristic calculation.",
    )
    with pytest.raises(ValidationError, match="must be unique"):
        ReviewReport(
            summary="A sufficiently long summary for this test report.",
            findings=[valid_finding(), valid_finding()],
            risk=risk,
            files_reviewed=1,
            additions=1,
            deletions=0,
        )
