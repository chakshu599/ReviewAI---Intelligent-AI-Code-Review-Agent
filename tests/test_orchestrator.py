from reviewai.core.orchestrator import ReviewOrchestrator
from reviewai.core.schemas import ParsedDiff
from reviewai.utils.error_handler import ConfigurationError

DIFF = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1 +1 @@
-old = 1
+new = 2
"""


class MissingKeyAgent:
    def review(self, parsed, deterministic):
        raise ConfigurationError("GROQ_API_KEY is not configured.")


def test_deterministic_fallback_is_explicit_when_llm_unavailable():
    result = ReviewOrchestrator(review_agent=MissingKeyAgent()).run(DIFF)
    assert result.report.analysis_mode == "Deterministic only"
    assert "GROQ_API_KEY" in result.warning
    assert "not a complete code review" in result.report.summary
    assert result.tool_trace[-2] == "semantic_review_unavailable"
