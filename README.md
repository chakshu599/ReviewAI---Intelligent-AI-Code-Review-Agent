# ReviewAI — Intelligent AI Code Review Agent

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-29%20passed-brightgreen.svg)](tests/)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-red.svg)](https://streamlit.io/)

ReviewAI analyzes unified Git diffs and reports **evidence-based** potential bugs, security risks, test gaps, code-quality concerns, performance issues, and maintainability risks. It accepts pasted diffs, `.diff`/`.patch` uploads, and public GitHub commit or pull-request references.

---

## Features

| Feature | Description |
|---------|-------------|
| **Multi-source Input** | Paste diffs, upload `.diff`/`.patch` files, or fetch from public GitHub PRs/commits |
| **Deterministic Checks** | Static analysis for security patterns, code quality, test gaps (works without API key) |
| **AI-Assisted Review** | Optional Groq-powered semantic analysis for deeper insights |
| **Risk Scoring** | Explainable heuristic scoring (Critical/High/Medium/Low) with prioritization |
| **Export Reports** | Download JSON or Markdown reports for CI/CD integration |
| **Streamlit UI** | Clean, responsive web interface with filtering and drill-down |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Streamlit UI (app.py)                    │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ReviewOrchestrator                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐  │
│  │  Validate   │ │   Parse     │ │  Determin-  │ │  Groq LLM │  │
│  │  Input      │ │  Diff       │ │  istic Chks │ │  Semantic │  │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘  │
│                              │                                    │
│                              ▼                                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                │
│  │  Pydantic   │ │ Deduplicate │ │ Risk Score  │                │
│  │  Validate   │ │ & Normalize │ │  (0-100)    │                │
│  └─────────────┘ └─────────────┘ └─────────────┘                │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Report Generator                           │
│                    (JSON / Markdown / UI)                       │
└─────────────────────────────────────────────────────────────────┘
```

**Key Design Principles:**
- **No code execution** — Submitted diffs are analyzed as text only
- **Allowlisted tools** — Groq agent can only call read-only analysis functions
- **Pydantic contracts** — All findings validated against strict schemas
- **Explainable scoring** — Risk score shows exactly how points were calculated

---

## Quick Start

### Prerequisites
- Python 3.11+
- Git
- [Groq API key](https://console.groq.com/keys) (optional, for AI-assisted review)

### Installation

```bash
# Clone the repository
git clone https://github.com/chakshu599/ReviewAI---Intelligent-AI-Code-Review-Agent.git
cd ReviewAI---Intelligent-AI-Code-Review-Agent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### Run the App

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | — | **Required** for AI-assisted review |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model to use |
| `GROQ_TIMEOUT_SECONDS` | `30` | Request timeout |
| `GROQ_MAX_RETRIES` | `2` | Max retry attempts |
| `MAX_DIFF_BYTES` | `50000` | Max diff size to process |
| `MAX_FILES` | `20` | Max files per diff |
| `MAX_LLM_CONTEXT_CHARS` | `12000` | Context window for LLM |
| `GITHUB_TOKEN` | — | GitHub PAT for higher rate limits (public repos only) |

---

## Usage

### 1. Paste a Diff
Copy any unified Git diff and paste it into the text area.

### 2. Upload a File
Upload a `.diff` or `.patch` file (max 50KB by default).

### 3. Fetch from GitHub
Enter a public GitHub repository URL and a commit SHA or `PR:<number>`.

### Example Diff
```diff
@@ -10,7 +10,7 @@ def get_user(user_id):
     cursor = conn.cursor()
-    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
+    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
     return cursor.fetchone()
```
**Finding**: `HIGH` — SQL Injection via string interpolation

---

## Project Structure

```
reviewai/
├── agents/              # Semantic analysis agents
│   ├── code_review_agent.py
│   ├── security_agent.py
│   └── test_analysis_agent.py
├── core/                # Core orchestration & contracts
│   ├── config.py        # Settings management
│   ├── llm_client.py    # Groq API wrapper
│   ├── orchestrator.py  # Main pipeline
│   ├── risk_scoring.py  # Heuristic risk calculation
│   └── schemas.py       # Pydantic models
├── tools/               # Deterministic analysis tools
│   ├── code_analyzer.py
│   ├── diff_parser.py
│   ├── github_source.py
│   ├── report_generator.py
│   ├── static_security_scanner.py
│   └── test_gap_analyzer.py
└── utils/               # Validators & error handling
    ├── error_handler.py
    └── validators.py
```

---

## Running Tests

```bash
# Run all tests
pytest -q

# Run with coverage
pytest --cov=reviewai --cov-report=html

# Run specific test file
pytest tests/test_orchestrator.py -v
```

**Current status**: 29 tests passing (Python 3.13)

---

## Example Output

### Risk Score Breakdown
| Severity | Points | Count | Subtotal |
|----------|--------|-------|----------|
| Critical | 40 | 0 | 0 |
| High | 22 | 1 | 22 |
| Medium | 9 | 2 | 18 |
| Low | 3 | 3 | 9 |
| **Total** | | | **49/100** |

### Finding Categories
- **Security**: SQL injection, XSS, path traversal, hardcoded secrets
- **Bugs**: Null dereference, off-by-one, resource leaks
- **Performance**: N+1 queries, inefficient loops, missing indexes
- **Maintainability**: Complex functions, duplicate code, missing docs
- **Test Gaps**: Uncovered branches, missing edge cases

---

## Limitations

- Static rules are intentionally narrow — may miss issues or raise false positives
- Semantic accuracy depends on the selected Groq model and diff context
- GitHub API: public repos only, rate limits apply without token
- Test-gap analysis is a prompt to investigate, not proof of missing coverage
- No private repository access (by design)

---

## Roadmap

- [ ] Repository-specific configuration & custom rules
- [ ] Language-aware static analysis (TypeScript, Go, Rust, etc.)
- [ ] Line-level inline comments in diff view
- [ ] CI/CD integration (GitHub Actions, GitLab CI)
- [ ] Human review gates & approval workflow
- [ ] SARIF export for security tooling integration

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes and add tests
4. Run tests: `pytest -q`
5. Submit a Pull Request

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Security

Found a security issue? Please report it privately via [GitHub Security Advisories](https://github.com/chakshu599/ReviewAI---Intelligent-AI-Code-Review-Agent/security/advisories/new).

---

**Built with**: Python, Streamlit, Pydantic, Groq, GitPython
