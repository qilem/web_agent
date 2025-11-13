import json
import subprocess
from typing import Dict, Any

from ..tool import Tool, ToolArgument
from ..env import AgentEnvironment


class NPMInitTool(Tool):
    def __init__(self):
        super().__init__("npm.init")
        self.main_folder = "."
        self.timeout = 5

    def initialize(self, env: AgentEnvironment):
        self.main_folder = env.get_working_dir()
        timeout = env.get_config_value("server.timeout")
        if timeout is not None:
            self.timeout = timeout

    def description(self) -> str:
        return """`npm.init` - Initialize the node.js express server. \
This will initialize the server in the background."""

    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        package_json = {
            "name": "waa-workspace",
            "version": "1.0.0",
            "main": "index.js",
            "scripts": {
                "start": "nodemon index.js > .waa/server.log 2>&1 &",
                "start:sync": "nodemon index.js",
                "stop": "pkill -f 'node.*index.js' || true",
                "logs": "tail -n 20 .waa/server.log",
                "logs:follow": "tail -f .waa/server.log",
                "clean": "rm -rf .waa/server.log",
                "dev": "nodemon index.js",
                "status": "pgrep -f 'node.*index.js' && echo 'Server is running' || echo 'Server is not running'"
            },
            "author": "",
            "license": "ISC",
            "dependencies": {
                "express": "^4.18.2",
                "express-handlebars": "^7.1.2"
            },
            "devDependencies": {
                "nodemon": "^3.0.1"
            }
        }

        with open(self.main_folder / "package.json", "w") as f:
            json.dump(package_json, f)

        try:
            result = subprocess.run(
                ["npm", "install"],
                cwd=self.main_folder,
                capture_output=True,
                text=True
            )

            return {
                "ok": True,
                "data": {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode,
                    "message": "Server initialized"
                },
                "error": None
            }

        except Exception as e:
            return {
                "ok": False,
                "data": None,
                "error": str(e)
            }


class NPMStartTool(Tool):
    def __init__(self):
        super().__init__("npm.start")
        self.main_folder = "."
        self.timeout = 5

    def initialize(self, env: AgentEnvironment):
        self.main_folder = env.get_working_dir()
        timeout = env.get_config_value("server.timeout")
        if timeout is not None:
            self.timeout = timeout

    def description(self) -> str:
        return """`npm.start` - Start the node.js express server. \
This will start the dev server in the background. \
The dev server internally runs `nodemon`, which will automatically restart the server \
when you make changes to the code, or when the server crashes. \
Subsequently, you can use the `npm_status` tool to check if the server is running. \
Use the `npm_logs` tool to get the logs of the server. \
Or when you are done, you can use the `npm_stop` tool to stop the server."""

    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            check_result = subprocess.run(
                ["pgrep", "-f", "node.*index.js"],
                capture_output=True,
                text=True
            )

            if check_result.returncode == 0:
                pids = check_result.stdout.strip().split('\n')
                return {
                    "ok": False,
                    "data": {
                        "pids": pids,
                        "message": "Server is already running"
                    },
                    "error": "Server is already running with PIDs: " + ", ".join(pids)
                }

            result = subprocess.run(
                ["npm", "run", "start"],
                cwd=self.main_folder,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            return {
                "ok": True,
                "data": {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode,
                    "message": "Server start command executed"
                },
                "error": None
            }
        except subprocess.TimeoutExpired:
            return {
                "ok": True,
                "data": {
                    "stdout": "",
                    "stderr": "",
                    "return_code": None,
                    "message": "Server started in background (timeout expected)"
                },
                "error": None
            }
        except Exception as e:
            return {
                "ok": False,
                "data": None,
                "error": str(e)
            }


class NPMStopTool(Tool):
    def __init__(self):
        super().__init__("npm.stop")
        self.main_folder = "."
        self.timeout = 5

    def initialize(self, env: AgentEnvironment):
        self.main_folder = env.get_working_dir()
        timeout = env.get_config_value("server.timeout")
        if timeout is not None:
            self.timeout = timeout

    def description(self) -> str:
        return """`npm.stop` - Stop the running node.js express server. \
This will kill all node processes running index.js. \
If no server is running, this command will succeed silently."""

    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                ["npm", "run", "stop"],
                cwd=self.main_folder,
                capture_output=True,
                text=True
            )

            return {
                "ok": True,
                "data": {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode,
                    "message": "Server stop command executed"
                },
                "error": None
            }
        except Exception as e:
            return {
                "ok": False,
                "data": None,
                "error": str(e)
            }


class NPMStatusTool(Tool):
    def __init__(self):
        super().__init__("npm.status")
        self.main_folder = "."
        self.timeout = 5

    def initialize(self, env: AgentEnvironment):
        self.main_folder = env.get_working_dir()
        timeout = env.get_config_value("server.timeout")
        if timeout is not None:
            self.timeout = timeout

    def description(self) -> str:
        return """`npm.status` - Check if the node.js express server is running. \
Returns the process IDs if the server is running, or indicates that it's not running."""

    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                ["pgrep", "-f", "node.*index.js"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                return {
                    "ok": True,
                    "data": {
                        "running": True,
                        "pids": pids,
                        "message": "Server is running"
                    },
                    "error": None
                }
            else:
                return {
                    "ok": True,
                    "data": {
                        "running": False,
                        "pids": [],
                        "message": "Server is not running"
                    },
                    "error": None
                }
        except Exception as e:
            return {
                "ok": False,
                "data": None,
                "error": str(e)
            }

class NPMLogsTool(Tool):
    def __init__(self):
        super().__init__("npm.logs")
        self.schema.register_argument(ToolArgument("lines", "The number of lines to get, default to 20", False, int))
        self.main_folder = "."
        self.timeout = 5

    def initialize(self, env: AgentEnvironment):
        self.main_folder = env.get_working_dir()
        timeout = env.get_config_value("server.timeout")
        if timeout is not None:
            self.timeout = timeout

    def description(self) -> str:
        return """`npm.logs` - Get the last 20 lines of the server logs. \
This reads from the .waa/server.log file where all server output is redirected. \
You can specify the number of lines to get with the argument `lines`, default to 20."""

    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            lines = input.get("lines", 20)
            result = subprocess.run(
                ["tail",  "-n", f"{lines}", f"{self.main_folder}/.waa/server.log"],
                cwd=self.main_folder,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            return {
                "ok": True,
                "data": {
                    "logs": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode,
                    "message": f"Retrieved last {lines} lines of server logs"
                },
                "error": None
            }
        except Exception as e:
            return {
                "ok": False,
                "data": None,
                "error": str(e)
            }
