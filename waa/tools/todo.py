import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from ..tool import Tool, ToolArgument
from ..env import AgentEnvironment

def _now_iso() -> str:
    # 用到的时间值不参与断言，简单返回 ISO 字符串
    return datetime.now().isoformat(timespec="seconds")


def _load_todos(path: Path) -> List[Dict[str, Any]]:
    try:
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        # 文件损坏等异常时，按空列表处理（工具层自己给出错误/覆盖写入）
        return []


def _save_todos(path: Path, todos: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)


def _next_id(todos: List[Dict[str, Any]]) -> int:
    max_id = 0
    for t in todos:
        try:
            i = int(t.get("id", 0))
            if i > max_id:
                max_id = i
        except Exception:
            continue
    return max_id + 1

class TodoAddTool(Tool):
    def __init__(self):
        super().__init__("todo.add")

        self.schema.register_argument(ToolArgument("description", "Todo description", True, str))
        self.working_dir: Path = Path(".")
        self.todo_path: Path = Path(".")

    def initialize(self, env: AgentEnvironment):
        self.working_dir = Path(env.get_working_dir()).resolve()
        self.todo_path = (self.working_dir / ".waa" / "todo.json").resolve()

    def description(self) -> str:
        return "`todo.add` - Add a new TODO item. Args: description (str)."

    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            desc = input.get("description")
            if not isinstance(desc, str) or not desc.strip():
                return {"ok": False, "data": None, "error": "description must be a non-empty string"}

            todos = _load_todos(self.todo_path)
            new_id = _next_id(todos)
            item = {
                "id": new_id,
                "description": desc,
                "status": "pending",
                "created_at": _now_iso(),
            }
            todos.append(item)
            _save_todos(self.todo_path, todos)
            return {"ok": True, "data": {"id": new_id}, "error": None}
        except Exception as e:
            return {"ok": False, "data": None, "error": str(e)}


class TodoListTool(Tool):
    def __init__(self):
        super().__init__("todo.list")
        # 可选参数：status ('pending'|'completed'|'all')，默认 'all'
        self.schema.register_argument(ToolArgument("status", "Filter by status", False, str))
        self.working_dir: Path = Path(".")
        self.todo_path: Path = Path(".")

    def initialize(self, env: AgentEnvironment):
        self.working_dir = Path(env.get_working_dir()).resolve()
        self.todo_path = (self.working_dir / ".waa" / "todo.json").resolve()

    def description(self) -> str:
        return "`todo.list` - List TODO items. Optional arg: status ('pending'|'completed'|'all'; default 'all')."

    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            status = input.get("status", "all")
            if not isinstance(status, str):
                return {"ok": False, "data": None, "error": "status must be a string"}
            status = status.lower()
            if status not in {"pending", "completed", "all"}:
                return {"ok": False, "data": None, "error": "status must be 'pending', 'completed', or 'all'"}

            todos = _load_todos(self.todo_path)
            if status == "all":
                filtered = todos
            else:
                filtered = [t for t in todos if t.get("status") == status]

            return {
                "ok": True,
                "data": {"count": len(filtered), "todos": filtered},
                "error": None,
            }
        except Exception as e:
            return {"ok": False, "data": None, "error": str(e)}


class TodoCompleteTool(Tool):
    def __init__(self):
        super().__init__("todo.complete")
        # 必选：id (int)
        self.schema.register_argument(ToolArgument("id", "Todo id to complete", True, int))
        self.working_dir: Path = Path(".")
        self.todo_path: Path = Path(".")

    def initialize(self, env: AgentEnvironment):
        self.working_dir = Path(env.get_working_dir()).resolve()
        self.todo_path = (self.working_dir / ".waa" / "todo.json").resolve()

    def description(self) -> str:
        return "`todo.complete` - Mark a TODO as completed. Args: id (int)."

    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            todo_id = input.get("id")
            if not isinstance(todo_id, int):
                return {"ok": False, "data": None, "error": "id must be an integer"}

            todos = _load_todos(self.todo_path)
            found: Optional[Dict[str, Any]] = None
            for t in todos:
                if t.get("id") == todo_id:
                    found = t
                    break

            if not found:
                return {"ok": False, "data": None, "error": f"Todo id {todo_id} not found"}

            # 幂等地标记为 completed
            found["status"] = "completed"
            found["completed_at"] = _now_iso()
            _save_todos(self.todo_path, todos)

            return {"ok": True, "data": {"id": todo_id}, "error": None}
        except Exception as e:
            return {"ok": False, "data": None, "error": str(e)}



class TodoRemoveTool(Tool):
    def __init__(self):
        super().__init__("todo.remove")
        # 必选：id (int)
        self.schema.register_argument(ToolArgument("id", "Todo id to remove", True, int))
        self.working_dir: Path = Path(".")
        self.todo_path: Path = Path(".")

    def initialize(self, env: AgentEnvironment):
        self.working_dir = Path(env.get_working_dir()).resolve()
        self.todo_path = (self.working_dir / ".waa" / "todo.json").resolve()

    def description(self) -> str:
        return "`todo.remove` - Remove a TODO item. Args: id (int)."

    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            todo_id = input.get("id")
            if not isinstance(todo_id, int):
                return {"ok": False, "data": None, "error": "id must be an integer"}

            todos = _load_todos(self.todo_path)
            new_todos = [t for t in todos if t.get("id") != todo_id]

            if len(new_todos) == len(todos):
                return {"ok": False, "data": None, "error": f"Todo id {todo_id} not found"}

            _save_todos(self.todo_path, new_todos)
            return {"ok": True, "data": {"removed_id": todo_id}, "error": None}
        except Exception as e:
            return {"ok": False, "data": None, "error": str(e)}