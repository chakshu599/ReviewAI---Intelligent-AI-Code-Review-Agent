"""Test-gap analysis agent entry point."""

from reviewai.core.schemas import Finding, ParsedDiff
from reviewai.tools.test_gap_analyzer import test_gap_analysis


class TestAnalysisAgent:
    def analyze(self, parsed: ParsedDiff) -> list[Finding]:
        return test_gap_analysis(parsed)
