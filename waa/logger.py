from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import json


class Logger:
    def __init__(self, log_path: Path, debug: bool = False):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.debug = debug

        with open(self.log_path, 'w') as f:
            f.write(f"=== WAA Agent Log ===\n")
            f.write(f"Started: {datetime.now().isoformat()}\n")
            f.write(f"{'=' * 80}\n\n")

    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"[{timestamp}] [{level}] {message}"
        with open(self.log_path, 'a') as f:
            f.write(f"{message}\n")
        if self.debug:
            print(message)

    def log_system_prompt(self, prompt: str):
        self.log("=" * 80, "INFO")
        self.log("SYSTEM PROMPT", "INFO")
        self.log("-" * 80, "INFO")
        with open(self.log_path, 'a') as f:
            f.write(f"{prompt}\n")
        self.log("=" * 80, "INFO")
        self.log("", "INFO")

    def log_user_instruction(self, instruction: str):
        self.log("=" * 80, "INFO")
        self.log("USER INSTRUCTION", "INFO")
        self.log("-" * 80, "INFO")
        with open(self.log_path, 'a') as f:
            f.write(f"{instruction}\n")
        self.log("=" * 80, "INFO")
        self.log("", "INFO")

    def log_llm_query(self, turn: int, message_count: int):
        self.log(f">>> Turn {turn}: Querying LLM with {message_count} messages in history", "INFO")

    def log_llm_response(self, turn: int, response: str):
        self.log("-" * 80, "INFO")
        self.log(f"LLM RESPONSE (Turn {turn})", "INFO")
        self.log("-" * 80, "INFO")
        with open(self.log_path, 'a') as f:
            f.write(f"{response}\n")
        self.log("-" * 80, "INFO")
        self.log("", "INFO")

    def log_tool_call(self, tool_name: str, arguments: Dict[str, Any]):
        self.log(f">>> Executing tool: {tool_name}", "INFO")
        self.log(f"    Arguments: {json.dumps(arguments, indent=2)}", "DEBUG")

    def log_tool_result(self, tool_name: str, result: Any, error: Optional[str] = None):
        if error:
            self.log(f"<<< Tool {tool_name} FAILED: {error}", "ERROR")
        else:
            self.log(f"<<< Tool {tool_name} completed successfully", "INFO")
            if result:
                self.log(f"    Result: {json.dumps(result, indent=2)}", "DEBUG")
        self.log("", "INFO")

    def log_termination(self, turn: int, reason: str):
        self.log("=" * 80, "INFO")
        self.log(f"AGENT TERMINATED - {reason}", "INFO")
        self.log(f"Total turns: {turn}", "INFO")
        self.log("=" * 80, "INFO")

    def log_error(self, error: str, exception: Optional[Exception] = None):
        self.log(f"ERROR: {error}", "ERROR")
        if exception:
            self.log(f"Exception: {str(exception)}", "ERROR")

    def log_warning(self, warning: str):
        self.log(warning, "WARNING")

    def log_debug(self, message: str):
        self.log(message, "DEBUG")
