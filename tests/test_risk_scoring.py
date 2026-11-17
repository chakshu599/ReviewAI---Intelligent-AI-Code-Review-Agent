from reviewai.core.risk_scoring import calculate_risk
from reviewai.core.schemas import Category, Finding, Severity
from reviewai.tools.report_generator import deduplicate_findings


def finding(severity=Severity.LOW, title="Possible edge case", line=3, confidence=0.7):
    return Finding(
        finding_id="temp",
        category=Category.BUG,
        severity=severity,
        file_name="src/a.py",
        line_number=line,
        title=title,
        explanation="The changed branch may skip an expected case based on this evidence.",
        why_it_matters="That behavior could cause an incorrect response for affected inputs.",
        suggested_fix="Add a boundary test and adjust the branch if the test demonstrates the issue.",
        confidence=confidence,
    )


def test_empty_risk_is_low_and_explicitly_heuristic():
    risk = calculate_risk([])
    assert risk.score == 0
    assert risk.level == Severity.LOW
    assert risk.is_heuristic is True
    assert "not proof" in risk.explanation


def test_risk_score_adds_weights_and_caps_at_100():
    risk = calculate_risk([finding(Severity.HIGH), finding(Severity.MEDIUM)])
    assert risk.score == 31
    assert risk.level == Severity.MEDIUM
    capped = calculate_risk([finding(Severity.CRITICAL)] * 3)
    assert capped.score == 100
    assert capped.level == Severity.CRITICAL


def test_duplicate_findings_keep_highest_confidence_and_receive_stable_ids():
    result = deduplicate_findings([finding(confidence=0.5), finding(confidence=0.95)])
    assert len(result) == 1
    assert result[0].confidence == 0.95
    assert result[0].finding_id == "F-001"
