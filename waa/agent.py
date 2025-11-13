import os
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import re
from .llm import LanguageModel, GeminiLanguageModel, MockLanguageModel
from .tool import ToolRegistry
from .history import HistoryEntry, SystemPrompt, UserInstruction, LLMResponse, ToolCallResult
from .logger import Logger
from .env import AgentEnvironment


class Agent:
    working_dir: Path
    llm: LanguageModel
    tool_registry: ToolRegistry
    config: Dict[str, Any]
    max_turns: int
    history: List[HistoryEntry]
    logger: Logger
    env: AgentEnvironment
    debug: bool

    def __init__(self, working_dir: Path, debug: bool = False):
        self.working_dir = working_dir
        self.config = None
        self.debug = debug
        self.llm = None
        self.tool_registry = None
        self.max_turns = 0
        self.history = []
        self.logger = None
        self.env = None

    def initialize_environment(self):
        config_path = self.working_dir / ".waa" / "config.json"
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, 'r') as f:
            self.config = json.load(f)

        self.env = AgentEnvironment(self.working_dir, self.config)
        self.max_turns = self.env.get_config_value("max_turns", 50)

    def initialize_llm(self):
        llm_type = self.config.get("llm_type", "mock")
        if llm_type == "gemini":
            model_name = self.config.get("model", "gemini-2.0-flash-thinking-exp-01-21")
            api_key = self.config.get("api_key", os.getenv("GEMINI_API_KEY"))
            return GeminiLanguageModel(model_name=model_name, api_key=api_key)
        elif llm_type == "mock":
            responses = self.config.get("mock_responses")
            return MockLanguageModel(responses=responses)
        else:
            raise ValueError(f"Unknown llm_type: {llm_type}. Use 'gemini' or 'mock'.")

    def _extract_text_for_entry(self, entry):

        try:
            from .history import ToolCallResult as _TCR
            if isinstance(entry, _TCR):
        
                tool_name = getattr(entry, "tool_name", "?")
                result = getattr(entry, "result", None)
                error = getattr(entry, "error", None)
                if error:
                    return f"[Tool:{tool_name}] (error) {error}"
                else:
             
                    try:
                        import json as _json
                        if isinstance(result, (dict, list)):
                            return f"[Tool:{tool_name}] {_json.dumps(result)}"
                    except Exception:
                        pass
                    return f"[Tool:{tool_name}] {result}"
        except Exception:
            pass

     
        try:
            content = entry.get_content()
            if isinstance(content, (dict, list)):
                import json as _json
                return _json.dumps(content)
            return str(content)
        except Exception:
      
            try:
                return str(entry)
            except Exception:
                return ""

    def _history_to_messages(self):

        messages = []
        from .history import SystemPrompt as _SP, UserInstruction as _UI, LLMResponse as _LR, ToolCallResult as _TCR

        for entry in self.history:
            text = self._extract_text_for_entry(entry)
            if isinstance(entry, _SP):
                messages.append({"role": "system", "content": text})
            elif isinstance(entry, _UI):
                messages.append({"role": "user", "content": text})
            elif isinstance(entry, _LR):
                messages.append({"role": "assistant", "content": text})
            elif isinstance(entry, _TCR):
                messages.append({"role": "system", "content": text})
            else:
                messages.append({"role": "system", "content": text})
        return messages

    def initialize_logger(self):
        log_path = self.working_dir / ".waa" / "agent.log"
        if log_path.exists():
            raise RuntimeError(f"Log file already exists: {log_path}. Remove it to start a new run.")

        self.logger = Logger(log_path, self.debug)
        self.logger.log("Agent initialization started")
        self.logger.log(f"Working directory: {self.working_dir}")
        self.logger.log(f"Debug mode: {self.debug}")
        self.logger.log(f"Max turns: {self.max_turns}")

    def initialize_tool_registry(self):
        self.tool_registry = ToolRegistry()
        allowed_tools = self.env.get_config_value("allowed_tools", None)
        from .tools import server
        from .tools import supertest
        from .tools import playwright
        from .tools import fs
        from .tools import todo
        from .tool import Tool

        def load_tools_from(mod):

            tools = []
            try:
                if hasattr(mod, "get_tools") and callable(mod.get_tools):
                    tools = mod.get_tools()
                    return tools

                if hasattr(mod, "TOOLS"):
                    tools = getattr(mod, "TOOLS")
                    return tools

                for name in dir(mod):
                    obj = getattr(mod, name)
                    if isinstance(obj, type) and issubclass(obj, Tool) and obj is not Tool:
                        try:
                            inst = obj()
                            tools.append(inst)
                        except Exception:
                            pass
            except Exception as e:
                if self.logger:
                    self.logger.log(f"Failed to load tools from {mod.__name__}: {e}")
            return tools

        all_tools = []
        for mod in (server, supertest, playwright, fs, todo):
            all_tools.extend(load_tools_from(mod))

        for tool in all_tools:
            name = getattr(tool, "name", None)
            if not name:
                if self.logger:
                    self.logger.log("Skip a tool without name")
                continue

            if (allowed_tools is not None) and (name not in allowed_tools):
                if self.logger:
                    self.logger.log(f"Skipped tool (not allowed): {name}")
                continue


            try:
                tool.initialize(self.env)
            except Exception as e:
                if self.logger:
                    self.logger.log(f"Tool initialize failed: {name}: {e}")


            try:
                self.tool_registry.register_tool(tool)
                if self.logger:
                    self.logger.log(f"Registered tool: {name}")
            except Exception as e:
                if self.logger:
                    self.logger.log(f"Register tool failed: {name}: {e}")

    def load_system_prompt(self):

            system_text = """You are WAA (Web-App Agent). Follow this protocol EXACTLY.

# OUTPUT MODE (Hard Rules)
- On every turn, you MUST output **only one** of the following:
  1) <tool_call>{"tool":"TOOL_NAME","arguments":{...}}</tool_call>
  2) <terminate>
- Output nothing else. No prose, no markdown, no comments.
- The JSON inside <tool_call> MUST be valid: double quotes only, no trailing commas.
- If a step needs multiple actions, split them across multiple turns (one tool call per turn).

# SAFETY & FILE RULES
- All paths must be inside the working directory; never use path traversal (e.g., "../").
- Do not modify or delete protected files (the environment provides that list).
- If an action would violate these rules, choose a safe alternative (e.g., read instead of write, or skip).

# TOOL USAGE
- Use only tools that are permitted in this run (from the environment's allowed tools).
- Prefer small, incremental edits: fs.read → fs.edit/fs.write, and verify as needed.
- Use server/test tools only if they are available and relevant.

# STRATEGY
- Derive requirements strictly from the user instruction in history.
- Take concrete steps toward completion. Keep changes minimal but functional.
- Stop with <terminate> once the task is complete (and tests pass if applicable).

# EXAMPLES (format only; adapt names/paths to the actual task)

## Example A: Create a file (turn N)
<tool_call>{"tool":"fs.write","arguments":{"path":"index.html","content":"<!doctype html><meta charset=\\"utf-8\\">"}}</tool_call>

## Example B: Read → then Edit (two turns)
# Turn N
<tool_call>{"tool":"fs.read","arguments":{"path":"index.html"}}</tool_call>
# Turn N+1
<tool_call>{"tool":"fs.edit","arguments":{"path":"index.html","old_text":"Old","new_text":"New"}}</tool_call>

## Example C: Make a directory, list it (two turns)
# Turn N
<tool_call>{"tool":"fs.mkdir","arguments":{"path":"assets/images"}}</tool_call>
# Turn N+1
<tool_call>{"tool":"fs.ls","arguments":{"path":"assets"}}</tool_call>

## Example D: Start a simple server (three turns; only if npm.* tools are allowed)
# Turn N
<tool_call>{"tool":"npm.init","arguments":{}}</tool_call>
# Turn N+1
<tool_call>{"tool":"npm.start","arguments":{}}</tool_call>
# Turn N+2
<tool_call>{"tool":"npm.status","arguments":{}}</tool_call>

## Example E: Handle protected paths safely
# If you need to view a protected file, read it (allowed); avoid write/delete.
<tool_call>{"tool":"fs.read","arguments":{"path":".waa/instruction.md"}}</tool_call>

## Example F: Finish when done
<terminate>

# REMINDERS
- ONE tool call per turn, or <terminate>.
- No extra text around tool calls—ever.
- Ensure JSON is valid; escape quotes properly in string content.
- Use only the tools actually allowed by the environment.

Return only <tool_call>...</tool_call> or <terminate>.
"""


            sp = SystemPrompt(system_text)  

            self.history.append(sp)
            if self.logger:
                self.logger.log("System prompt loaded into history")

    def load_instruction(self):
        instr_path = self.working_dir / ".waa" / "instruction.md"
        if not instr_path.exists():
            raise FileNotFoundError(f"Instruction file not found: {instr_path}")
        content = instr_path.read_text(encoding="utf-8")

 
        ui = UserInstruction(content)
        self.history.append(ui)

        if self.logger:
            self.logger.log("User instruction loaded into history")

    def initialize(self):
        self.initialize_environment()

        self.initialize_llm()
        self.llm = self.initialize_llm()
        self.initialize_logger()
        self.initialize_tool_registry()

        self.load_system_prompt()
        self.load_instruction()

    def query_llm(self, turn: int):
        messages = self._history_to_messages()

        if self.logger:
            self.logger.log_llm_query(messages, len(messages))

        resp_text = self.llm.generate(messages)


        if self.logger:
            self.logger.log_llm_response(resp_text, len(resp_text))


        self.history.append(LLMResponse(response=resp_text))
        return resp_text

    def execute_tool(self, tool_call: Dict[str, Any]):
        tool_name = tool_call.get("tool")
        arguments = tool_call.get("arguments", {})

     
        if not tool_name:
            tcr = ToolCallResult(
                tool_name="(missing)",
                arguments=arguments,
                result=None,
                error="Missing 'tool' in tool_call"
            )
            self.history.append(tcr)
            if self.logger:
                self.logger.log("[Tool ERR] missing tool name in tool_call")
            return tcr

  
        try:
            tool = self.tool_registry.get_tool(tool_name)
        except KeyError:
            tcr = ToolCallResult(
                tool_name=tool_name,
                arguments=arguments,
                result=None,
                error=f"Unknown tool: {tool_name}"
            )
            self.history.append(tcr)
            if self.logger:
                self.logger.log(f"[Tool ERR] Unknown tool: {tool_name}")
            return tcr

        try:
            tool.schema.validate(arguments)
        except Exception as e:
            tcr = ToolCallResult(
                tool_name=tool_name,
                arguments=arguments,
                result=None,
                error=f"Invalid arguments: {e}"
            )
            self.history.append(tcr)
            if self.logger:
                self.logger.log(f"[Tool ERR] {tool_name} invalid args: {e}")
            return tcr

        try:
            result = tool.execute(arguments)
            tcr = ToolCallResult(
                tool_name=tool_name,
                arguments=arguments,
                result=result,
                error=None
            )
            self.history.append(tcr)
            if self.logger:
                # 简要记录成功
                preview = str(result)
                if len(preview) > 300:
                    preview = preview[:300] + "...(truncated)"
                self.logger.log(f"[Tool OK] {tool_name} -> {preview}")
            return tcr
        except Exception as e:
            tcr = ToolCallResult(
                tool_name=tool_name,
                arguments=arguments,
                result=None,
                error=f"{type(e).__name__}: {e}"
            )
            self.history.append(tcr)
            if self.logger:
                self.logger.log(f"[Tool ERR] {tool_name} -> {tcr.error}")
            return tcr

    def run(self):
        self.initialize_environment()
        self.llm = self.initialize_llm()  # 别忘了赋值！
        self.initialize_logger()
        self.initialize_tool_registry()
        self.load_system_prompt()
        self.load_instruction()

        tool_pat = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL)

        for turn in range(1, self.max_turns + 1):
            resp_text = self.query_llm(turn)

            if "<terminate>" in resp_text:
                if self.logger:
                    self.logger.log(f"Terminate at turn {turn}")
                break

            m = tool_pat.search(resp_text)
            if m:
                json_str = m.group(1).strip()
                try:
                    call_obj = json.loads(json_str)
                except Exception as e:
                
                    tcr = ToolCallResult(
                        tool_name="(parse_error)",
                        arguments={"raw": json_str},
                        result="",
                        error=f"Invalid tool_call JSON: {type(e).__name__}: {e}"
                    )
                    self.history.append(tcr)
                    if self.logger:
                        self.logger.log(tcr.error)
                    continue

                self.execute_tool(call_obj)
                continue

            if self.logger:
                self.logger.log("LLM output had no <tool_call> or <terminate>. Stopping.")
            break
        else:
            if self.logger:
                self.logger.log(f"Reached max_turns={self.max_turns} without termination.")
