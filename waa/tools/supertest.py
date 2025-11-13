import json
import subprocess
from pathlib import Path
from typing import Dict, Any

from ..tool import Tool, ToolArgument
from ..env import AgentEnvironment


class SupertestInitTool(Tool):
    def __init__(self):
        super().__init__("supertest.init")
        self.main_folder = "."
        self.timeout = 30

    def initialize(self, env: AgentEnvironment):
        self.main_folder = Path(env.get_working_dir())
        timeout = env.get_config_value("supertest.timeout")
        if timeout is not None:
            self.timeout = timeout

    def description(self) -> str:
        return """`supertest.init` - Initialize Jest and Supertest for API testing. \
This will update package.json with Jest and Supertest dependencies and add test scripts. \
Jest is a JavaScript testing framework, and Supertest is used for HTTP assertions."""

    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            package_json_path = self.main_folder / "package.json"

            if package_json_path.exists():
                with open(package_json_path, "r") as f:
                    package_json = json.load(f)
            else:
                package_json = {
                    "name": "waa-workspace",
                    "version": "1.0.0",
                    "main": "index.js",
                    "scripts": {},
                    "dependencies": {},
                    "devDependencies": {}
                }

            if "devDependencies" not in package_json:
                package_json["devDependencies"] = {}

            package_json["devDependencies"]["jest"] = "^29.7.0"
            package_json["devDependencies"]["supertest"] = "^6.3.3"

            if "scripts" not in package_json:
                package_json["scripts"] = {}

            package_json["scripts"]["test"] = "jest tests/"
            package_json["scripts"]["test:api"] = "jest tests/api.test.js"
            package_json["scripts"]["test:watch"] = "jest tests/ --watch"
            package_json["scripts"]["test:coverage"] = "jest tests/ --coverage"

            with open(package_json_path, "w") as f:
                json.dump(package_json, f, indent=2)

            install_result = subprocess.run(
                ["npm", "install"],
                cwd=self.main_folder,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            if install_result.returncode != 0:
                return {
                    "ok": False,
                    "data": {
                        "stdout": install_result.stdout,
                        "stderr": install_result.stderr,
                    },
                    "error": f"npm install failed: {install_result.stderr}"
                }

            return {
                "ok": True,
                "data": {
                    "package_updated": str(package_json_path),
                    "install_stdout": install_result.stdout,
                    "message": "Jest and Supertest initialized successfully"
                },
                "error": None
            }

        except subprocess.TimeoutExpired as e:
            return {
                "ok": False,
                "data": None,
                "error": f"Installation timed out: {str(e)}"
            }
        except Exception as e:
            return {
                "ok": False,
                "data": None,
                "error": f"Failed to initialize Supertest: {str(e)}"
            }


class SupertestRunTool(Tool):
    def __init__(self):
        super().__init__("supertest.run")
        self.schema.register_argument(
            ToolArgument("test_file", "The test file to run, defaults to 'tests/api.test.js'", False, str)
        )
        self.schema.register_argument(
            ToolArgument("verbose", "Run tests in verbose mode", False, bool)
        )
        self.main_folder = "."
        self.timeout = 60

    def initialize(self, env: AgentEnvironment):
        self.main_folder = Path(env.get_working_dir())
        timeout = env.get_config_value("supertest.timeout")
        if timeout is not None:
            self.timeout = timeout

    def description(self) -> str:
        return """`supertest.run` - Run Jest/Supertest API tests. \
Executes API tests using Jest and Supertest. These tests validate RESTful API endpoints. \
You can optionally specify a test file (defaults to 'tests/api.test.js') and verbose mode. \
Returns test results including pass/fail status, number of tests, and any error messages."""

    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            test_file = input.get("test_file", "tests/api.test.js")
            verbose = input.get("verbose", False)

            cmd = ["npm", "test", "--", test_file]

            if verbose:
                cmd.append("--verbose")

            result = subprocess.run(
                cmd,
                cwd=self.main_folder,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            passed = result.returncode == 0
            output_lines = result.stdout.split('\n') + result.stderr.split('\n')

            summary = {
                "tests": 0,
                "passed": 0,
                "failed": 0,
                "suites": 0
            }

            for line in output_lines:
                line = line.strip()

                if "Test Suites:" in line:
                    parts = line.split(",")
                    for part in parts:
                        if "passed" in part:
                            nums = [int(s) for s in part.split() if s.isdigit()]
                            if nums:
                                summary["suites"] = nums[0]

                elif "Tests:" in line:
                    parts = line.split(",")
                    for part in parts:
                        if "passed" in part:
                            nums = [int(s) for s in part.split() if s.isdigit()]
                            if nums:
                                summary["passed"] = nums[0]
                        elif "failed" in part:
                            nums = [int(s) for s in part.split() if s.isdigit()]
                            if nums:
                                summary["failed"] = nums[0]

            summary["tests"] = summary["passed"] + summary["failed"]

            return {
                "ok": True,
                "data": {
                    "passed": passed,
                    "return_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "summary": summary,
                    "test_file": test_file,
                    "message": "API tests passed" if passed else "API tests failed"
                },
                "error": None if passed else "Some API tests failed"
            }

        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "data": None,
                "error": f"Jest tests timed out after {self.timeout} seconds"
            }
        except FileNotFoundError:
            return {
                "ok": False,
                "data": None,
                "error": "npm or jest not found. Make sure Node.js and Jest are installed."
            }
        except Exception as e:
            return {
                "ok": False,
                "data": None,
                "error": f"Failed to run API tests: {str(e)}"
            }
