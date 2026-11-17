"""Groq provider adapter with bounded retries and strict JSON decoding."""

import json
import time
from collections.abc import Callable
from typing import Any

from reviewai.core.config import Settings, get_settings
from reviewai.utils.error_handler import ConfigurationError, LLMAnalysisError


class GroqLLMClient:
    """Minimal provider boundary; replace this class to add another LLM provider."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.groq_api_key:
            raise ConfigurationError(
                "GROQ_API_KEY is not configured. Add it to .env to run AI analysis; deterministic checks remain available."
            )
        try:
            from groq import Groq

            self._client = Groq(
                api_key=self.settings.groq_api_key,
                timeout=self.settings.groq_timeout_seconds,
                max_retries=0,
            )
        except ImportError as exc:
            raise ConfigurationError("Install project dependencies before running AI analysis.") from exc

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict[str, Any]] | None = None,
        tool_handler: Callable[[str, dict[str, Any]], Any] | None = None,
    ) -> dict[str, Any]:
        """Call Groq with optional allowlisted function tools and bounded retries."""
        last_error: Exception | None = None
        attempts = self.settings.groq_max_retries + 1
        for attempt in range(attempts):
            try:
                messages: list[dict[str, Any]] = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
                tool_rounds = 0
                used_tool = False
                tool_results: dict[tuple[str, str], Any] = {}
                while True:
                    request: dict[str, Any] = {
                        "model": self.settings.groq_model,
                        "temperature": 0.1,
                        "max_tokens": 5000,
                        "messages": messages,
                    }
                    if tools and tool_handler and tool_rounds < 3:
                        request.update(tools=tools, tool_choice="auto")
                    else:
                        request["response_format"] = {"type": "json_object"}
                    response = self._client.chat.completions.create(**request)
                    message = response.choices[0].message
                    calls = getattr(message, "tool_calls", None) or []
                    if calls:
                        if not tools or tool_handler is None or tool_rounds >= 3:
                            raise ValueError("The model requested a tool outside the permitted workflow.")
                        messages.append({
                            "role": "assistant",
                            "content": message.content,
                            "tool_calls": [call.model_dump(exclude_none=True) for call in calls],
                        })
                        for call in calls:
                            name = call.function.name
                            arguments = json.loads(call.function.arguments or "{}")
                            if not isinstance(arguments, dict):
                                raise ValueError("Tool arguments must be a JSON object.")
                            cache_key = (name, json.dumps(arguments, sort_keys=True))
                            if cache_key not in tool_results:
                                tool_results[cache_key] = tool_handler(name, arguments)
                            output = tool_results[cache_key]
                            messages.append({
                                "role": "tool",
                                "tool_call_id": call.id,
                                "content": json.dumps(output, ensure_ascii=False),
                            })
                        tool_rounds += 1
                        used_tool = True
                        continue
                    content = message.content
                    if not content and used_tool:
                        # Ask for the final validated shape after tool results.
                        messages.append({"role": "user", "content": "Return the final required JSON object now."})
                        request["messages"] = messages
                        request.pop("tools", None)
                        request.pop("tool_choice", None)
                        request["response_format"] = {"type": "json_object"}
                        response = self._client.chat.completions.create(**request)
                        content = response.choices[0].message.content
                    if not content:
                        raise ValueError("The model returned an empty response.")
                    decoded = json.loads(content)
                    if not isinstance(decoded, dict):
                        raise ValueError("Expected a JSON object.")
                    return decoded
            except Exception as exc:  # Provider exceptions vary across SDK versions.
                last_error = exc
                if attempt + 1 < attempts:
                    time.sleep(min(2**attempt, 4))
        raise LLMAnalysisError(
            "Groq analysis failed after the configured retry limit. Check model availability, network access, and API quota."
        ) from last_error
