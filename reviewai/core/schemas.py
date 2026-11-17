"""Strict data contracts for parsed changes and review reports."""

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Severity(StrEnum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class Category(StrEnum):
    BUG = "Bug"
    SECURITY = "Security"
    TESTING = "Testing"
    QUALITY = "Code Quality"
    PERFORMANCE = "Performance"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ChangedLine(StrictModel):
    line_number: int = Field(ge=1)
    content: str
    change_type: str = Field(pattern="^(added|deleted|context)$")


class FileChange(StrictModel):
    old_path: str | None = None
    new_path: str | None = None
    status: str = "modified"
    additions: int = Field(ge=0)
    deletions: int = Field(ge=0)
    changed_lines: list[ChangedLine]
    patch: str = ""

    @property
    def display_path(self) -> str:
        return self.new_path or self.old_path or "<unknown>"


class ParsedDiff(StrictModel):
    files: list[FileChange]
    additions: int = Field(ge=0)
    deletions: int = Field(ge=0)
    source: str = "diff"


class Finding(StrictModel):
    finding_id: str = Field(min_length=1, max_length=40)
    category: Category
    severity: Severity
    file_name: str = Field(min_length=1, max_length=500)
    line_number: int | None = Field(default=None, ge=1)
    title: str = Field(min_length=4, max_length=180)
    explanation: str = Field(min_length=10, max_length=4000)
    why_it_matters: str = Field(min_length=5, max_length=1500)
    suggested_fix: str = Field(min_length=5, max_length=2000)
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]

    @field_validator("finding_id")
    @classmethod
    def normalize_id(cls, value: str) -> str:
        return value.strip()


class SeverityCounts(StrictModel):
    critical: int = Field(ge=0)
    high: int = Field(ge=0)
    medium: int = Field(ge=0)
    low: int = Field(ge=0)


class RiskAssessment(StrictModel):
    score: int = Field(ge=0, le=100)
    level: Severity
    counts: SeverityCounts
    explanation: str = Field(min_length=10, max_length=1500)
    is_heuristic: bool = True


class ReviewReport(StrictModel):
    report_version: str = "1.0"
    summary: str = Field(min_length=10, max_length=2500)
    findings: list[Finding]
    risk: RiskAssessment
    files_reviewed: int = Field(ge=0)
    additions: int = Field(ge=0)
    deletions: int = Field(ge=0)
    analysis_mode: str = "AI-assisted"

    @field_validator("findings")
    @classmethod
    def unique_finding_ids(cls, findings: list[Finding]) -> list[Finding]:
        ids = [finding.finding_id for finding in findings]
        if len(ids) != len(set(ids)):
            raise ValueError("finding_id values must be unique")
        return findings
