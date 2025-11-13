from typing import Any, Dict, List

from .env import AgentEnvironment

ToolArgumentInput = Any

class ToolArgument:
    def __init__(self, name: str, description: str, required: bool, type: Any):
        self.name = name
        self.description = description
        self.required = required
        self.type = type

    def validate(self, input: ToolArgumentInput) -> bool:
        if self.type is not None and type(input) != self.type:
            return False
        return True


class ToolSchema:
    arguments: Dict[str,ToolArgument]

    def __init__(self):
        self.arguments = {}

    def register_argument(self, argument: ToolArgument):
        self.arguments[argument.name] = argument

    def validate(self, input: Dict[str, ToolArgumentInput]) -> bool:
        for argument in self.arguments.values():
            if argument.name not in input and argument.required:
                raise ValueError(f"Argument {argument.name} is required")
            if argument.name in input and not argument.validate(input[argument.name]):
                raise ValueError(f"Argument {argument.name} is invalid")
        return True


class Tool:
    def __init__(self, name: str):
        self.name = name
        self.schema = ToolSchema()

    def initialize(self, env: AgentEnvironment):
        pass

    def description(self) -> str:
        raise NotImplementedError("Subclasses must implement this method")

    def execute(self, input: Dict[str, ToolArgumentInput]) -> Any:
        raise NotImplementedError("Subclasses must implement this method")


class ToolRegistry:
    tools: Dict[str, Tool]

    def __init__(self):
        self.tools = {}

    def register_tool(self, tool: Tool):
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> Tool:
        return self.tools[name]

    def list_tools(self) -> List[Tool]:
        return list([tool for tool in self.tools.values()])
