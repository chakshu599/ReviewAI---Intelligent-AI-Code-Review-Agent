"""Fixed, validated review-tool pipeline with explicit AI failure reporting."""

from dataclasses import dataclass
from typing import Callable

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from reviewai.agents.code_review_agent import CodeReviewAgent
from reviewai.agents.security_agent import SecurityAgent
from reviewai.agents.test_analysis_agent import TestAnalysisAgent
from reviewai.core.schemas import Finding, ParsedDiff, ReviewReport
from reviewai.tools.code_analyzer import analyze_code
from reviewai.tools.diff_parser import parse_git_diff
from reviewai.tools.report_generator import generate_report
from reviewai.utils.error_handler import ReviewAIError


class DiffToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    diff_text: str = Field(min_length=1)
    source: str = Field(default="diff", max_length=80)


class ParsedDiffToolInput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")
    parsed: ParsedDiff


class ReportToolInput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")
    parsed: ParsedDiff
    findings: list[Finding]
    summary: str = Field(min_length=10, max_length=2500)


@dataclass(frozen=True)
class AnalysisResult:
    report: ReviewReport
    warning: str | None
    tool_trace: tuple[str, ...]


class ReviewToolRegistry:
    """Allowlist of in-process tools; never dispatch model-provided code or shell commands."""

    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., object]] = {
            "parse_git_diff": self._parse,
            "analyze_code": self._analyze,
            "security_scan": SecurityAgent().analyze,
            "test_gap_analysis": TestAnalysisAgent().analyze,
            "generate_report": self._generate,
        }

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._tools)

    def invoke(self, name: str, payload: dict[str, object]) -> object:
        """Validate arguments for a known function before invocation."""
        if name == "parse_git_diff":
            args = DiffToolInput.model_validate(payload)
            return self._tools[name](args.diff_text, args.source)
        if name in {"analyze_code", "security_scan", "test_gap_analysis"}:
            args = ParsedDiffToolInput.model_validate(payload)
            return self._tools[name](args.parsed)
        if name == "generate_report":
            args = ReportToolInput.model_validate(payload)
            return self._tools[name](args.parsed, args.findings, args.summary)
        raise ValueError(f"Tool is not allowlisted: {name}")

    @staticmethod
    def _parse(diff_text: str, source: str) -> ParsedDiff:
        return parse_git_diff(diff_text, source=source)

    @staticmethod
    def _analyze(parsed: ParsedDiff) -> list[Finding]:
        return analyze_code(parsed)

    @staticmethod
    def _generate(parsed: ParsedDiff, findings: list[Finding], summary: str) -> ReviewReport:
        return generate_report(parsed, findings, summary)


class ReviewOrchestrator:
    """Run deterministic tools, semantic review, validation, and report creation."""

    def __init__(self, review_agent: CodeReviewAgent | None = None, registry: ReviewToolRegistry | None = None) -> None:
        self.review_agent = review_agent
        self.registry = registry or ReviewToolRegistry()

    def run(self, diff_text: str, source: str = "diff") -> AnalysisResult:
        parsed = self.registry.invoke("parse_git_diff", {"diff_text": diff_text, "source": source})
        assert isinstance(parsed, ParsedDiff)
        trace = ["parse_git_diff"]
        deterministic: list[Finding] = []
        for name in ("analyze_code", "security_scan", "test_gap_analysis"):
            result = self.registry.invoke(name, {"parsed": parsed})
            assert isinstance(result, list)
            deterministic.extend(result)
            trace.append(name)

        warning: str | None = None
        mode = "AI-assisted"
        try:
            agent = self.review_agent or CodeReviewAgent()
            summary, semantic_findings = agent.review(parsed, deterministic)
            findings = deterministic + semantic_findings
        except (ReviewAIError, ValidationError, ValueError) as exc:
            # Keep deterministic evidence available, but label the limited result honestly.
            mode = "Deterministic only"
            warning = str(exc) if isinstance(exc, ReviewAIError) else "The LLM returned invalid structured data; only deterministic checks are shown."
            summary = "AI semantic analysis was unavailable. The report contains only conservative deterministic checks; this is not a complete code review."
            findings = deterministic
        report = self.registry.invoke(
            "generate_report",
            {"parsed": parsed, "findings": findings, "summary": summary},
        )
        assert isinstance(report, ReviewReport)
        if mode != "AI-assisted":
            report = report.model_copy(update={"analysis_mode": mode})
        trace.extend(["semantic_review" if mode == "AI-assisted" else "semantic_review_unavailable", "generate_report"])
        return AnalysisResult(report=report, warning=warning, tool_trace=tuple(trace))
