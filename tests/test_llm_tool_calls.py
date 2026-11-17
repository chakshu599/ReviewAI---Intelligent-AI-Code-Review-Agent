import json
from types import SimpleNamespace

from reviewai.core.config import Settings
from reviewai.core.llm_client import GroqLLMClient


class ToolCall:
    id = "call-1"
    function = SimpleNamespace(name="security_scan", arguments="{}")

    def model_dump(self, exclude_none=True):
        return {
            "id": self.id,
            "type": "function",
            "function": {"name": self.function.name, "arguments": self.function.arguments},
        }


class CompletionSequence:
    def __init__(self):
        self.requests = []

    def create(self, **request):
        self.requests.append(request)
        if "tools" in request:
            message = SimpleNamespace(content=None, tool_calls=[ToolCall()])
        else:
            message = SimpleNamespace(content=json.dumps({"summary": "Validated final response.", "findings": []}), tool_calls=[])
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def test_groq_tool_calls_use_only_supplied_tools_and_validated_handler(monkeypatch):
    sequence = CompletionSequence()

    class FakeGroq:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=sequence)

    import sys
    monkeypatch.setitem(sys.modules, "groq", SimpleNamespace(Groq=FakeGroq))
    client = GroqLLMClient(Settings("test-key", "model", 1, 0, 10000, 10, 5000, None))
    allowed = {"security_scan"}
    received = []

    def handler(name, arguments):
        assert name in allowed
        assert arguments == {}
        received.append(name)
        return [{"finding_id": "F-1"}]

    result = client.complete_json(
        "system",
        "review",
        tools=[{"type": "function", "function": {"name": "security_scan"}}],
        tool_handler=handler,
    )
    assert result["summary"] == "Validated final response."
    assert received == ["security_scan"]
    assert sequence.requests[0]["tool_choice"] == "auto"
    final_request = sequence.requests[-1]
    assert "response_format" in final_request
    assert "tools" not in final_request
    assert final_request["messages"][-1]["role"] == "tool"
