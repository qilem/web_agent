from pathlib import Path
from typing import Dict, Any

class AgentEnvironment:
    def __init__(self, working_dir: Path, config: Dict[str, Any]):
        self.working_dir = working_dir
        self.config = config

    def get_config(self) -> Dict[str, Any]:
        return self.config

    def get_config_value(self, key: str, default: Any = None) -> Any:
        key_parts = key.split(".")
        current_dict = self.config
        for part in key_parts:
            if part not in current_dict:
                return default
            current_dict = current_dict[part]
        return current_dict

    def get_working_dir(self) -> Path:
        return self.working_dir
