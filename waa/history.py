from typing import Any, Dict, Optional
from datetime import datetime


class HistoryEntry:
    def __init__(self, role: str):
        self.role = role

    def get_content(self) -> Any:
        raise NotImplementedError("Subclasses must implement this method")

    def to_json(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.get_content(),
        }


class SystemPrompt(HistoryEntry):
    def __init__(self, prompt: str):
        super().__init__("system")
        self.prompt = prompt

    def get_content(self) -> str:
        return self.prompt


class UserInstruction(HistoryEntry):
    def __init__(self, instruction: str):
        super().__init__("user")
        self.instruction = instruction
        self.timestamp = datetime.now()

    def get_content(self) -> str:
        return self.instruction


class LLMResponse(HistoryEntry):
    def __init__(self, response: str):
        super().__init__("assistant")
        self.response = response
        self.timestamp = datetime.now()

    def get_content(self) -> str:
        return self.response

    def is_tool_call(self) -> bool:
        return "<tool_call>" in self.response

    def is_termination(self) -> bool:
        return "<terminate>" in self.response

    def is_message(self) -> bool:
        return not self.is_tool_call() and not self.is_termination()


class ToolCallResult(HistoryEntry):
    def __init__(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Any,
        error: Optional[Any] = None,
    ):
        super().__init__("tool")
        self.tool_name = tool_name
        self.arguments = arguments
        self.result = result
        self.error = error
        self.timestamp = datetime.now()

    def get_content(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result": self.result,
            "error": self.error,
        }
