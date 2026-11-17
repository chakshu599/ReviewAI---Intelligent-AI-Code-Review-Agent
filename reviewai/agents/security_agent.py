"""Security-analysis agent entry point."""

from reviewai.core.schemas import Finding, ParsedDiff
from reviewai.tools.static_security_scanner import security_scan


class SecurityAgent:
    def analyze(self, parsed: ParsedDiff) -> list[Finding]:
        return security_scan(parsed)
