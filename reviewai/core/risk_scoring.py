"""Explainable heuristic risk scoring; never a security certification."""

from collections import Counter

from reviewai.core.schemas import Finding, RiskAssessment, Severity, SeverityCounts

_WEIGHTS = {
    Severity.CRITICAL: 40,
    Severity.HIGH: 22,
    Severity.MEDIUM: 9,
    Severity.LOW: 3,
}


def calculate_risk(findings: list[Finding]) -> RiskAssessment:
    """Score reports by severity with an explicit capped additive heuristic."""
    counts = Counter(finding.severity for finding in findings)
    score = min(100, sum(_WEIGHTS[f.severity] for f in findings))
    if score >= 75:
        level = Severity.CRITICAL
    elif score >= 45:
        level = Severity.HIGH
    elif score >= 15:
        level = Severity.MEDIUM
    else:
        level = Severity.LOW
    count_model = SeverityCounts(
        critical=counts[Severity.CRITICAL],
        high=counts[Severity.HIGH],
        medium=counts[Severity.MEDIUM],
        low=counts[Severity.LOW],
    )
    if not findings:
        explanation = "No actionable findings were returned. This heuristic score is not proof that the change is bug-free or secure."
    else:
        explanation = (
            f"Heuristic score {score}/100: Critical findings add 40, High 22, Medium 9, "
            "and Low 3 points, capped at 100. This prioritizes review effort; it is not a verified security assessment."
        )
    return RiskAssessment(score=score, level=level, counts=count_model, explanation=explanation, is_heuristic=True)
