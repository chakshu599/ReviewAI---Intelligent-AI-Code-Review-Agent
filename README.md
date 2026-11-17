# ReviewAI — Intelligent AI Code Review Agent

ReviewAI reviews unified Git diffs and reports evidence-based potential bugs, security risks, test gaps, code-quality concerns, performance issues, and maintainability risks. It accepts pasted diffs, `.diff`/`.patch` uploads, and public GitHub commit or pull-request references. Submitted source is treated as untrusted text and is never executed. **A clean report is not proof that code is bug-free or secure.**

## Architecture and workflow

`app.py` provides the Streamlit dashboard and JSON/Markdown exports. `reviewai/core` owns configuration, strict Pydantic contracts, the Groq provider boundary, orchestration, and the explainable risk heuristic. `reviewai/tools` parses unified patches, runs added-line security and quality checks, detects possible test gaps, fetches public GitHub diffs, and formats reports. `reviewai/agents` contains semantic, security, and test-analysis entry points. `reviewai/utils` validates uploads and repository references. GitHub diffs use the public REST API (private repositories are rejected); GitPython also provides a bounded local working-tree diff helper.

The controller validates input → parses files/hunks → runs deterministic checks → asks Groq for semantic feedback → validates findings with Pydantic → deduplicates and normalizes locations → calculates a risk score → renders/downloads the report. The Groq agent can call only the allowlisted read-only analysis tools (`analyze_code`, `security_scan`, `test_gap_analysis`), with empty, validated arguments. Parsing and report generation remain controller-owned tools. There is no shell tool or code execution. The risk score adds 40/22/9/3 points per Critical/High/Medium/Low finding, capped at 100; it is a prioritization heuristic, not a verified security assessment.

## Run locally

Requires Python 3.11+ and Git. Create an environment, install dependencies, copy `.env.example` to `.env`, then set `GROQ_API_KEY` (never commit `.env`). `GROQ_MODEL` defaults to `llama-3.3-70b-versatile`; set it to a model currently enabled for your Groq account. Optional settings include `GROQ_TIMEOUT_SECONDS`, `GROQ_MAX_RETRIES`, `MAX_DIFF_BYTES`, `MAX_FILES`, `MAX_LLM_CONTEXT_CHARS`, and `GITHUB_TOKEN` (for GitHub API rate limits; public repositories only).

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
# Edit .env and add GROQ_API_KEY
streamlit run app.py
```

On minimal Debian/Kali images where `ensurepip` is unavailable, create the environment with `python -m venv --without-pip .venv`, then install into it with `python -m pip --python .venv/bin/python install -r requirements.txt` (use `.venv\Scripts\python.exe` on Windows).

Run automated tests with `pytest -q`. Without a Groq key, deterministic checks still produce a clearly labeled limited report; Groq failures and invalid model output are surfaced rather than presented as successful AI analysis. Inputs are limited by `MAX_DIFF_BYTES` and `MAX_FILES`; GitHub access is restricted to public `github.com` URLs and commit SHAs or `PR:<number>` references.

## Validation notes

- **What went wrong / how it was handled:** pytest initially treated the public `test_gap_analysis` tool as a test because its module/function names match pytest discovery; the tool is now explicitly excluded from collection. Hunk-count validation exposed a malformed fixture, and the GitPython integration test caught an unsupported keyword being forwarded as a Git CLI option; both were fixed and covered by tests. The OS Python was externally managed and lacked `ensurepip`, so dependencies were installed into a workspace `.venv` instead of system-wide.
- **Tests actually run:** `.venv/bin/python -m pytest -q` — **29 passed** (Python 3.13.14, 1.43 s).
- **Local UI smoke test:** Streamlit loaded in a browser; loading and analyzing `sample_diffs/python_example.diff` produced an explicit deterministic-only report because no `GROQ_API_KEY` was configured. It showed a High SQL interpolation finding and a Low test-gap prompt, with a 25/100 Medium heuristic score. The live Groq API path was not exercised without credentials.

## Limitations and next steps

Static rules are intentionally narrow and can miss issues or raise false positives; semantic accuracy depends on the selected model and the provided diff context. GitHub API diff availability and rate limits apply. The test-gap result is a prompt to investigate, not proof of missing coverage. Next: add repository-specific context/configurable rules, richer language-aware static analysis, line-level inline comments, and CI integration with human review gates.
