"""Small, evidence-based security checks on added diff lines only."""

import re

from reviewai.core.schemas import Category, Finding, ParsedDiff, Severity

_RULES: tuple[tuple[re.Pattern[str], str, Severity, str, str, str, float], ...] = (
    (
        re.compile(r"\beval\s*\("),
        "Dynamic evaluation of input",
        Severity.HIGH,
        "This added line calls eval(), which interprets a string as executable code.",
        "If the value can be influenced externally, an attacker may execute arbitrary code in the application process.",
        "Avoid eval(); parse the expected data format or use an explicit allowlist of operations.",
        0.9,
    ),
    (
        re.compile(r"\bexec\s*\("),
        "Dynamic execution of input",
        Severity.HIGH,
        "This added line calls exec(), which executes dynamically constructed code.",
        "Untrusted or insufficiently constrained input could become code execution.",
        "Replace dynamic execution with explicit dispatch to validated operations.",
        0.88,
    ),
    (
        re.compile(r"subprocess\.(?:run|Popen|call|check_output)\s*\(.*\bshell\s*=\s*True"),
        "Shell command built in application code",
        Severity.HIGH,
        "This added subprocess call enables shell interpretation.",
        "If command arguments include untrusted data, shell metacharacters can alter the executed command.",
        "Pass an argument list with shell=False and validate each argument against the expected format.",
        0.82,
    ),
    (
        re.compile(r"\.execute\s*\(\s*(?:f[\"']|[\"'].*%s)"),
        "Potentially interpolated SQL query",
        Severity.HIGH,
        "This added database call appears to construct SQL through string interpolation or formatting.",
        "Interpolated values can change query structure and expose data or permit unauthorized writes.",
        "Use the database driver's parameterized query API and pass values separately.",
        0.78,
    ),
    (
        re.compile(r"(?:innerHTML\s*=|dangerouslySetInnerHTML\s*=)"),
        "HTML inserted without an evident escaping boundary",
        Severity.MEDIUM,
        "This added assignment inserts HTML directly into a rendering sink.",
        "If the assigned value contains attacker-controlled markup, it may enable cross-site scripting.",
        "Prefer text rendering; otherwise sanitize with a well-maintained HTML sanitizer at the trust boundary.",
        0.72,
    ),
)


def security_scan(parsed: ParsedDiff) -> list[Finding]:
    """Emit findings only for matching added lines, with the matched code as evidence."""
    findings: list[Finding] = []
    for file in parsed.files:
        for changed in file.changed_lines:
            if changed.change_type != "added":
                continue
            if changed.content.lstrip().startswith(("#", "//", "/*", "*", "<!--")):
                continue
            for pattern, title, severity, explanation, impact, fix, confidence in _RULES:
                if pattern.search(changed.content):
                    findings.append(Finding(
                        finding_id=f"SEC-{len(findings) + 1:03d}",
                        category=Category.SECURITY,
                        severity=severity,
                        file_name=file.display_path,
                        line_number=changed.line_number,
                        title=title,
                        explanation=f"{explanation} Evidence: `{changed.content[:240]}`",
                        why_it_matters=impact,
                        suggested_fix=fix,
                        confidence=confidence,
                    ))
    return findings
