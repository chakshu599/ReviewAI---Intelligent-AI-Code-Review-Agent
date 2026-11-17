"""User-safe errors and retry helpers."""


class ReviewAIError(RuntimeError):
    """Base error that can be shown without leaking credentials or internals."""


class ConfigurationError(ReviewAIError):
    """Required application configuration is missing."""


class LLMAnalysisError(ReviewAIError):
    """The model failed or returned invalid structured output."""
