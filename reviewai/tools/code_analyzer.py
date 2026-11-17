"""Deterministic code-change context builder and conservative quality checks."""

from reviewai.core.schemas import Category, Finding, ParsedDiff, Severity


def build_review_context(parsed: ParsedDiff, max_chars: int) -> str:
    """Serialize changed-file patches within a fixed prompt budget."""
    blocks: list[str] = []
    remaining = max_chars
    for file in parsed.files:
        block = f"FILE: {file.display_path}\nPATCH:\n{file.patch}\n"
        if len(block) > remaining:
            if remaining <= 0:
                break
            block = block[:remaining] + "\n[context truncated at configured limit]\n"
        blocks.append(block)
        remaining -= len(block)
        if remaining <= 0:
            break
    return "\n".join(blocks)


def analyze_code(parsed: ParsedDiff) -> list[Finding]:
    """Report a narrow, deterministic quality issue with direct line evidence."""
    findings: list[Finding] = []
    for file in parsed.files:
        for changed in file.changed_lines:
            if changed.change_type != "added":
                continue
            if len(changed.content) > 240 and not changed.content.lstrip().startswith(("#", "//", "*")):
                findings.append(Finding(
                    finding_id=f"QLT-{len(findings) + 1:03d}",
                    category=Category.QUALITY,
                    severity=Severity.LOW,
                    file_name=file.display_path,
                    line_number=changed.line_number,
                    title="Very long added line may be difficult to review",
                    explanation=f"The added line is {len(changed.content)} characters long, making control flow or data transformations harder to inspect.",
                    why_it_matters="Dense lines increase review effort and can hide subtle behavior, especially in security-sensitive code.",
                    suggested_fix="Consider extracting the expression into named intermediate values or splitting it into focused statements.",
                    confidence=0.76,
                ))
    return findings
