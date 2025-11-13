import shutil
from pathlib import Path
from typing import Dict, Any, List

from ..tool import Tool, ToolArgument
from ..env import AgentEnvironment

def _resolve_within(base_dir: Path, rel_path: Path) -> Path:

    abs_path = (base_dir / rel_path).resolve()
    base_dir = base_dir.resolve()
    try:
        abs_path.relative_to(base_dir)
    except Exception:

        raise ValueError("Path is outside working directory")
    return abs_path


def _load_protected_paths(env: AgentEnvironment, base_dir: Path) -> List[Path]:

    protected = env.get_config_value("protected_files", []) or []
    out: List[Path] = []
    for p in protected:
        try:
            out.append((base_dir / p).resolve())
        except Exception:
          
            pass
    return out


def _is_protected(abs_path: Path, protected_paths: List[Path]) -> bool:

    p = abs_path.resolve()
    for prot in protected_paths:
        try:
            p.relative_to(prot)
            return True
        except Exception:
            continue
    return False

class FileCreateTool(Tool):
    def __init__(self):
        super().__init__("fs.write")
        # 参数：path(str, 必填), content(str, 必填)
        self.schema.register_argument(ToolArgument("path", "File path to write", True, str))
        self.schema.register_argument(ToolArgument("content", "Content to write", True, str))
        self.working_dir: Path = Path(".")
        self.protected: List[Path] = []

    def initialize(self, env: AgentEnvironment):
        self.working_dir = Path(env.get_working_dir()).resolve()
        self.protected = _load_protected_paths(env, self.working_dir)

    def description(self) -> str:
        return "`fs.write` - Create or overwrite file (auto-create parents). Block writes to protected_files."

    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            rel = Path(input["path"])
            content: str = input["content"]
            abs_path = _resolve_within(self.working_dir, rel)

            if _is_protected(abs_path, self.protected):
                return {"ok": False, "data": None, "error": "Path is protected"}

            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_text(content, encoding="utf-8")

            return {
                "ok": True,
                "data": {"path": str(rel), "bytes": abs_path.stat().st_size},
                "error": None,
            }
        except Exception as e:
            return {"ok": False, "data": None, "error": str(e)}



class FileDeleteTool(Tool):
    def __init__(self):
        super().__init__("fs.delete")
        # 参数：path(str, 必填)
        self.schema.register_argument(ToolArgument("path", "File path to delete", True, str))
        self.working_dir: Path = Path(".")
        self.protected: List[Path] = []

    def initialize(self, env: AgentEnvironment):
        self.working_dir = Path(env.get_working_dir()).resolve()
        self.protected = _load_protected_paths(env, self.working_dir)

    def description(self) -> str:
        return "`fs.delete` - Delete a file. Block deletes to protected_files."

    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            rel = Path(input["path"])
            abs_path = _resolve_within(self.working_dir, rel)

            if _is_protected(abs_path, self.protected):
                return {"ok": False, "data": None, "error": "Path is protected"}

            if not abs_path.exists() or not abs_path.is_file():
                return {"ok": False, "data": None, "error": f"File not found: {rel}"}

            abs_path.unlink()
            return {"ok": True, "data": {"deleted": str(rel)}, "error": None}
        except Exception as e:
            return {"ok": False, "data": None, "error": str(e)}
        

        
class FileReadTool(Tool):
    def __init__(self):
        super().__init__("fs.read")
        # 参数：path(str, 必填)
        self.schema.register_argument(ToolArgument("path", "File path to read", True, str))
        self.working_dir: Path = Path(".")

    def initialize(self, env: AgentEnvironment):
        self.working_dir = Path(env.get_working_dir()).resolve()

    def description(self) -> str:
        return "`fs.read` - Read a file; returns content, size, line_count."

    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            rel = Path(input["path"])
            abs_path = _resolve_within(self.working_dir, rel)

            if not abs_path.exists() or not abs_path.is_file():
                return {"ok": False, "data": None, "error": f"File not found: {rel}"}

            content = abs_path.read_text(encoding="utf-8")
            # 行数：按换行符统计；若非空且不以 \n 结尾，则最后一行也算
            line_count = content.count("\n") + (0 if content.endswith("\n") or len(content) == 0 else 1)

            return {
                "ok": True,
                "data": {
                    "path": str(rel),
                    "content": content,
                    "size": abs_path.stat().st_size,
                    "line_count": line_count,
                },
                "error": None,
            }
        except Exception as e:
            return {"ok": False, "data": None, "error": str(e)}

class FileEditTool(Tool):
    def __init__(self):
        super().__init__("fs.edit")
        # 参数：path(str, 必填), old_text(str, 必填), new_text(str, 必填)
        self.schema.register_argument(ToolArgument("path", "File path to edit", True, str))
        self.schema.register_argument(ToolArgument("old_text", "Text to find (first occurrence)", True, str))
        self.schema.register_argument(ToolArgument("new_text", "Replacement text", True, str))
        self.working_dir: Path = Path(".")
        self.protected: List[Path] = []

    def initialize(self, env: AgentEnvironment):
        self.working_dir = Path(env.get_working_dir()).resolve()
        self.protected = _load_protected_paths(env, self.working_dir)

    def description(self) -> str:
        return "`fs.edit` - Replace first occurrence of old_text with new_text. Block edits to protected_files."

    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            rel = Path(input["path"])
            old_text: str = input["old_text"]
            new_text: str = input["new_text"]
            abs_path = _resolve_within(self.working_dir, rel)

            if _is_protected(abs_path, self.protected):
                return {"ok": False, "data": None, "error": "Path is protected"}

            if not abs_path.exists() or not abs_path.is_file():
                return {"ok": False, "data": None, "error": f"File not found: {rel}"}

            content = abs_path.read_text(encoding="utf-8")
            idx = content.find(old_text)
            if idx == -1:
                return {"ok": False, "data": {"replacements": 0}, "error": "old_text not found"}

            new_content = content[:idx] + new_text + content[idx + len(old_text):]
            abs_path.write_text(new_content, encoding="utf-8")
            return {"ok": True, "data": {"replacements": 1, "path": str(rel)}, "error": None}
        except Exception as e:
            return {"ok": False, "data": None, "error": str(e)}


class DirectoryCreateTool(Tool):
    def __init__(self):
        super().__init__("fs.mkdir")
        # 参数：path(str, 必填)
        self.schema.register_argument(ToolArgument("path", "Directory path to create", True, str))
        self.working_dir: Path = Path(".")

    def initialize(self, env: AgentEnvironment):
        self.working_dir = Path(env.get_working_dir()).resolve()

    def description(self) -> str:
        return "`fs.mkdir` - Create a directory (parents=True)."

    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            rel = Path(input["path"])
            abs_path = _resolve_within(self.working_dir, rel)
            abs_path.mkdir(parents=True, exist_ok=True)
            return {"ok": True, "data": {"created": str(rel)}, "error": None}
        except Exception as e:
            return {"ok": False, "data": None, "error": str(e)}


class DirectoryDeleteTool(Tool):
    def __init__(self):
        super().__init__("fs.rmdir")
        # 参数：path(str, 必填), recursive(bool, 可选)
        self.schema.register_argument(ToolArgument("path", "Directory path to remove", True, str))
        self.schema.register_argument(ToolArgument("recursive", "Remove recursively", False, bool))
        self.working_dir: Path = Path(".")

    def initialize(self, env: AgentEnvironment):
        self.working_dir = Path(env.get_working_dir()).resolve()

    def description(self) -> str:
        return "`fs.rmdir` - Remove a directory. If recursive=true, removes non-empty directories."

    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            rel = Path(input["path"])
            recursive: bool = input.get("recursive", False)
            abs_path = _resolve_within(self.working_dir, rel)

            if not abs_path.exists() or not abs_path.is_dir():
                return {"ok": False, "data": None, "error": f"Directory not found: {rel}"}

            if recursive:
                shutil.rmtree(abs_path)
            else:
                abs_path.rmdir()

            return {"ok": True, "data": {"removed": str(rel), "recursive": recursive}, "error": None}
        except Exception as e:
            return {"ok": False, "data": None, "error": str(e)}



class DirectoryListTool(Tool):
    def __init__(self):
        super().__init__("fs.ls")
        # 参数：path(str, 可选，默认 ".")
        self.schema.register_argument(ToolArgument("path", "Directory to list", False, str))
        self.working_dir: Path = Path(".")

    def initialize(self, env: AgentEnvironment):
        self.working_dir = Path(env.get_working_dir()).resolve()

    def description(self) -> str:
        return "`fs.ls` - List directory entries with name, type, size."

    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            rel = Path(input.get("path", "."))
            abs_path = _resolve_within(self.working_dir, rel)

            if not abs_path.exists() or not abs_path.is_dir():
                return {"ok": False, "data": None, "error": f"Directory not found: {rel}"}

            entries: List[Dict[str, Any]] = []
            for child in sorted(abs_path.iterdir()):
                entries.append({
                    "name": child.name,
                    "type": "dir" if child.is_dir() else "file",
                    "size": (child.stat().st_size if child.is_file() else 0),
                })

            return {"ok": True, "data": {"path": str(rel), "entries": entries}, "error": None}
        except Exception as e:
            return {"ok": False, "data": None, "error": str(e)}


class DirectoryTreeTool(Tool):
    def __init__(self):
        super().__init__("fs.tree")
        self.schema.register_argument(ToolArgument("path", "Root directory to tree", False, str))
        self.schema.register_argument(ToolArgument("max_depth", "Max depth to traverse", False, int))
        self.working_dir = Path(".")

    def initialize(self, env: AgentEnvironment):
        self.working_dir = Path(env.get_working_dir()).resolve()

    def description(self) -> str:
        return "`fs.tree` - Show directory tree structure up to max_depth."

    def _build_tree(self, root: Path, depth: int, max_depth: int):
        if depth > max_depth:
            return []
        nodes = []
        # 即使列目录失败也要吞掉，保证不抛异常
        try:
            for child in sorted(root.iterdir()):
                if child.is_dir():
                    nodes.append({
                        "name": child.name,
                        "type": "dir",
                        "children": self._build_tree(child, depth + 1, max_depth)
                    })
                else:
                    try:
                        size = child.stat().st_size
                    except Exception:
                        size = None
                    nodes.append({"name": child.name, "type": "file", "size": size})
        except Exception:
            pass
        return nodes

    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            rel = Path(input.get("path", "."))
            max_depth = int(input.get("max_depth", 2))

            abs_path = (self.working_dir / rel).resolve()
            try:
                # 越界校验：不抛出到外层，返回错误字典
                abs_path.relative_to(self.working_dir)
            except Exception:
                return {
                    "ok": False,
                    "data": None,
                    "error": "Path is outside working directory"
                }

            if not abs_path.exists() or not abs_path.is_dir():
                return {"ok": False, "data": None, "error": f"Directory not found: {rel}"}

            tree = self._build_tree(abs_path, 1, max_depth)
            return {"ok": True, "data": {"path": str(rel), "tree": tree}, "error": None}
        except Exception as e:
            # 兜底，绝不抛异常给 agent
            return {"ok": False, "data": None, "error": str(e)}
