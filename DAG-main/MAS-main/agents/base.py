from abc import ABC, abstractmethod
from typing import Dict, Any

class Agent(ABC):
    def __init__(self, name: str):
        self.name = name

    # @abstractmethod
    def preprocess(self, task_input: str) -> Dict[str, Any]:
        """LLM → structured input"""
        pass

    # @abstractmethod
    def call_tool(self, processed_input: Dict[str, Any]) -> Any:
        """Deterministic tool execution"""
        pass

    def postprocess(self, tool_output: Any) -> str:
        """LLM → final answer"""
        return str(tool_output)

    def run(self, task_input: str) -> str:
        processed_input = self.preprocess(task_input)
        tool_output = self.call_tool(processed_input)
        return self.postprocess(tool_output)