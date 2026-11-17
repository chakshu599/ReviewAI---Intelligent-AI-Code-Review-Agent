"""Streamlit interface for evidence-based AI code review."""

from pathlib import Path

import streamlit as st

from reviewai.core.config import get_settings
from reviewai.core.orchestrator import ReviewOrchestrator
from reviewai.core.schemas import Category, ReviewReport, Severity
from reviewai.tools.diff_parser import parse_git_diff
from reviewai.tools.github_source import fetch_public_github_diff
from reviewai.tools.report_generator import report_as_json, report_as_markdown
from reviewai.utils.error_handler import ReviewAIError
from reviewai.utils.validators import InputValidationError, validate_diff_text, validate_upload


st.set_page_config(page_title="ReviewAI · Code Review", page_icon="🔎", layout="wide")
st.markdown(
    """
    <style>
      .stApp { background: linear-gradient(180deg, #f8fafc 0%, #f3f6fb 55%, #f8fafc 100%); }
      [data-testid="stSidebar"] { background: #101a2b; }
      [data-testid="stSidebar"] * { color: #e7eefb; }
      .hero { padding: 1.4rem 1.6rem; border-radius: 18px; color: white;
        background: linear-gradient(125deg, #101a2b, #1d3760 72%, #2867a2);
        box-shadow: 0 12px 30px rgba(20, 40, 70, .16); margin-bottom: 1rem; }
      .hero h1 { margin: 0 0 .35rem 0; font-size: 2rem; }
      .hero p { margin: 0; opacity: .84; }
      div[data-testid="stMetric"] { background: white; border: 1px solid #e6ebf2;
        padding: 1rem; border-radius: 14px; box-shadow: 0 4px 14px rgba(20,40,70,.04); }
      .stButton > button { border-radius: 10px; font-weight: 650; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _status_color(level: str) -> str:
    return {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}.get(level, "⚪")


def _render_report(report: ReviewReport, diff_text: str, warning: str | None, tool_trace: tuple[str, ...]) -> None:
    if warning:
        st.warning(f"Analysis limitation: {warning}")
    if report.analysis_mode != "AI-assisted":
        st.info("This report contains deterministic checks only. It is not a complete semantic review.")

    st.subheader("Review summary")
    st.info(report.summary)
    risk_col, critical_col, high_col, medium_col, low_col = st.columns(5)
    risk_col.metric("Heuristic risk", f"{report.risk.score}/100", delta=report.risk.level.value, delta_color="off")
    risk_col.caption("Prioritization only—not a verified security assessment")
    critical_col.metric("Critical", report.risk.counts.critical)
    high_col.metric("High", report.risk.counts.high)
    medium_col.metric("Medium", report.risk.counts.medium)
    low_col.metric("Low", report.risk.counts.low)
    st.caption(report.risk.explanation)

    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Findings")
        severity_filter = st.multiselect(
            "Filter by severity",
            [item.value for item in Severity],
            default=[item.value for item in Severity],
            key="severity_filter",
        )
        category_filter = st.selectbox(
            "Group by category",
            ["All categories", *[item.value for item in Category]],
            key="category_filter",
        )
        findings = [item for item in report.findings if item.severity.value in severity_filter]
        if category_filter != "All categories":
            findings = [item for item in findings if item.category.value == category_filter]
        if not findings:
            st.success("No findings match these filters. This does not prove the change is bug-free or secure.")
        for finding in findings:
            title = f"{_status_color(finding.severity.value)} {finding.severity.value} · {finding.title}"
            with st.expander(title, expanded=False):
                st.text(f"{finding.finding_id}  ·  {finding.category.value}  ·  {finding.file_name}" +
                        (f":{finding.line_number}" if finding.line_number else ""))
                st.caption(f"Confidence: {finding.confidence:.0%}")
                st.markdown("**Issue**")
                st.text(finding.explanation)
                st.markdown("**Why it matters**")
                st.text(finding.why_it_matters)
                st.markdown("**Suggested fix**")
                st.text(finding.suggested_fix)

    with right:
        st.subheader("Changed files")
        st.caption(f"{report.files_reviewed} files · +{report.additions} / −{report.deletions}")
        try:
            parsed = parse_git_diff(diff_text, source="display")
            for file in parsed.files:
                with st.expander(file.display_path, expanded=False):
                    st.caption(f"{file.status} · +{file.additions} / −{file.deletions}")
                    st.code(file.patch, language="diff", line_numbers=False)
        except (ValueError, InputValidationError):
            st.code(diff_text, language="diff")

    st.subheader("Export")
    json_col, markdown_col = st.columns(2)
    with json_col:
        st.download_button(
            "Download JSON report",
            data=report_as_json(report),
            file_name="reviewai-report.json",
            mime="application/json",
            use_container_width=True,
        )
    with markdown_col:
        st.download_button(
            "Download Markdown report",
            data=report_as_markdown(report),
            file_name="reviewai-report.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with st.expander("Agent workflow trace"):
        st.text(" → ".join(tool_trace))


settings = get_settings()
with st.sidebar:
    st.markdown("## 🔎 ReviewAI")
    page = st.radio("Workspace", ["Dashboard", "How it works"], label_visibility="collapsed")
    st.divider()
    st.caption("Untrusted code is analyzed as text. ReviewAI never executes submitted source code.")

st.markdown(
    '<div class="hero"><h1>Intelligent code review</h1>'
    '<p>Evidence-based feedback on bugs, security, tests, and maintainability.</p></div>',
    unsafe_allow_html=True,
)

if page == "How it works":
    st.subheader("A controlled review pipeline")
    st.write("ReviewAI parses a unified patch, runs narrow deterministic checks, requests semantic review from Groq, validates structured findings with Pydantic, then calculates an explainable heuristic risk score.")
    st.write("Tool calls are restricted to a fixed in-process allowlist. No source code is executed, no private repository is accessed, and patch contents are explicitly treated as untrusted evidence rather than instructions.")
    st.write("The risk score prioritizes review effort. It is not a verified security assessment, and an empty findings list is not proof of correctness.")
    st.write("Groq configuration is optional for static checks. Add GROQ_API_KEY to a local .env file for semantic analysis; failures are reported and deterministic-only results are labeled clearly.")
else:
    st.subheader("Project overview")
    current_result = st.session_state.get("review_result")
    if current_result:
        current_report, _, _, _ = current_result
        metrics = st.columns(4)
        metrics[0].metric("Files reviewed", current_report.files_reviewed)
        metrics[1].metric("Findings", len(current_report.findings))
        metrics[2].metric("Heuristic risk", f"{current_report.risk.score}/100")
        metrics[3].metric("Risk level", current_report.risk.level.value)
    else:
        metrics = st.columns(4)
        metrics[0].metric("Files reviewed", "—")
        metrics[1].metric("Findings", "—")
        metrics[2].metric("Heuristic risk", "—")
        metrics[3].metric("Status", "Ready")
    st.caption("Start with a pasted diff, a .diff/.patch upload, or a public GitHub commit / pull request.")

    source_mode = st.radio(
        "Review source",
        ["Paste diff", "Upload diff", "Public GitHub"],
        horizontal=True,
        key="source_mode",
    )
    diff_text: str | None = None
    if source_mode == "Paste diff":
        sample_path = Path(__file__).parent / "sample_diffs" / "python_example.diff"
        col_input, col_sample = st.columns([5, 1])
        with col_sample:
            if st.button("Load sample", use_container_width=True):
                st.session_state["diff_input"] = sample_path.read_text(encoding="utf-8")
        diff_text = st.text_area(
            "Unified Git diff",
            height=250,
            placeholder="Paste a unified Git diff here…",
            key="diff_input",
        )
    elif source_mode == "Upload diff":
        uploaded = st.file_uploader("Upload .diff or .patch", type=["diff", "patch"])
        if uploaded:
            try:
                diff_text = validate_upload(uploaded.name, uploaded.getvalue())
                st.caption(f"Loaded {uploaded.name} ({len(uploaded.getvalue()):,} bytes).")
            except InputValidationError as exc:
                st.error(str(exc))
    else:
        repo_url = st.text_input("Public GitHub repository URL", placeholder="https://github.com/owner/repository")
        revision = st.text_input("Commit SHA or pull request", placeholder="e.g. 8-char SHA or PR:42")
        st.caption("Only public github.com repositories are supported. Private repositories are rejected.")

    if st.button("Analyze code", type="primary", use_container_width=True):
        try:
            if source_mode == "Public GitHub":
                if not repo_url.strip() or not revision.strip():
                    raise InputValidationError("Enter both a public repository URL and a commit SHA or PR:<number>.")
                with st.spinner("Fetching the public GitHub diff…"):
                    diff_text = fetch_public_github_diff(repo_url, revision)
            elif source_mode == "Paste diff":
                diff_text = validate_diff_text(diff_text or "")
            if not diff_text:
                raise InputValidationError("Choose a diff file or enter a unified diff before analyzing.")
            with st.spinner("Parsing changes and running review tools…"):
                result = ReviewOrchestrator().run(diff_text, source=source_mode)
            st.session_state["review_result"] = (result.report, diff_text, result.warning, result.tool_trace)
            st.success("Review complete.")
        except (InputValidationError, ReviewAIError, ValueError) as exc:
            st.error(str(exc))
        except Exception:
            st.error("Review failed unexpectedly. No successful report was created; check application logs and configuration.")

    if st.session_state.get("review_result"):
        report, reviewed_diff, warning, trace = st.session_state["review_result"]
        _render_report(report, reviewed_diff, warning, trace)
