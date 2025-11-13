import json
import subprocess
from pathlib import Path
from typing import Dict, Any

from ..tool import Tool, ToolArgument
from ..env import AgentEnvironment


class PlaywrightInitTool(Tool):
    def __init__(self):
        super().__init__("playwright.init")
        self.main_folder = "."
        self.timeout = 30

    def initialize(self, env: AgentEnvironment):
        self.main_folder = Path(env.get_working_dir())
        timeout = env.get_config_value("playwright.timeout")
        if timeout is not None:
            self.timeout = timeout

    def description(self) -> str:
        return """`playwright.init` - Initialize Playwright for UI testing. \
This will create a playwright.config.js file and install Playwright dependencies. \
It also updates package.json with test scripts and adds Playwright to devDependencies."""

    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            playwright_config = """/**
 * Playwright Configuration
 *
 * See https://playwright.dev/docs/test-configuration
 */

const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  testMatch: '**/ui.test.js',

  // Maximum time one test can run
  timeout: 30000,

  // Retry on failure
  retries: 0,

  // Run tests in parallel
  workers: 1,

  // Reporter to use
  reporter: 'list',

  use: {
    // Base URL for navigation
    baseURL: 'http://localhost:3000',

    // Collect trace when retrying the failed test
    trace: 'on-first-retry',

    // Screenshot on failure
    screenshot: 'only-on-failure',

    // Video on failure
    video: 'retain-on-failure',
  },

  // Browser projects
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
    },
  ],
});
"""

            config_path = self.main_folder / "playwright.config.js"
            with open(config_path, "w") as f:
                f.write(playwright_config)

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

            package_json["devDependencies"]["@playwright/test"] = "^1.40.0"

            if "scripts" not in package_json:
                package_json["scripts"] = {}

            package_json["scripts"]["test:ui"] = "playwright test tests/ui.test.js"
            package_json["scripts"]["test:ui:headed"] = "playwright test tests/ui.test.js --headed"
            package_json["scripts"]["test:ui:debug"] = "playwright test tests/ui.test.js --debug"

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

            browsers_result = subprocess.run(
                ["npx", "playwright", "install", "chromium"],
                cwd=self.main_folder,
                capture_output=True,
                text=True,
                timeout=60  # Browser installation can take longer
            )

            return {
                "ok": True,
                "data": {
                    "config_created": str(config_path),
                    "package_updated": str(package_json_path),
                    "install_stdout": install_result.stdout,
                    "browsers_stdout": browsers_result.stdout,
                    "message": "Playwright initialized successfully"
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
                "error": f"Failed to initialize Playwright: {str(e)}"
            }


class PlaywrightRunTool(Tool):
    def __init__(self):
        super().__init__("playwright.run")
        self.schema.register_argument(
            ToolArgument("test_file", "The test file to run, defaults to 'tests/ui.test.js'", False, str)
        )
        self.schema.register_argument(
            ToolArgument("headed", "Run browser in headed mode (visible)", False, bool)
        )
        self.main_folder = "."
        self.timeout = 60

    def initialize(self, env: AgentEnvironment):
        self.main_folder = Path(env.get_working_dir())
        timeout = env.get_config_value("playwright.timeout")
        if timeout is not None:
            self.timeout = timeout

    def description(self) -> str:
        return """`playwright.run` - Run Playwright UI tests. \
Executes the UI tests using Playwright. The server must be running on port 3000 before running these tests. \
You can optionally specify a test file (defaults to 'tests/ui.test.js') and whether to run in headed mode. \
Returns test results including pass/fail status and any error messages."""

    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            test_file = input.get("test_file", "tests/ui.test.js")
            headed = input.get("headed", False)

            cmd = ["npx", "playwright", "test", test_file]

            if headed:
                cmd.append("--headed")

            result = subprocess.run(
                cmd,
                cwd=self.main_folder,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            passed = result.returncode == 0
            output_lines = result.stdout.split('\n')

            summary = {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0
            }

            for line in output_lines:
                if "passed" in line.lower():
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part.isdigit():
                            if "passed" in line[:line.index(part)].lower():
                                summary["passed"] = int(part)
                            if i + 1 < len(parts) and "passed" in parts[i + 1].lower():
                                summary["passed"] = int(part)

                if "failed" in line.lower():
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part.isdigit():
                            if "failed" in line[:line.index(part)].lower():
                                summary["failed"] = int(part)

            summary["total"] = summary["passed"] + summary["failed"]

            return {
                "ok": True,
                "data": {
                    "passed": passed,
                    "return_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "summary": summary,
                    "test_file": test_file,
                    "message": "UI tests passed" if passed else "UI tests failed"
                },
                "error": None if passed else "Some UI tests failed"
            }

        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "data": None,
                "error": f"Playwright tests timed out after {self.timeout} seconds"
            }
        except FileNotFoundError:
            return {
                "ok": False,
                "data": None,
                "error": "npx or playwright not found. Make sure Node.js and Playwright are installed."
            }
        except Exception as e:
            return {
                "ok": False,
                "data": None,
                "error": f"Failed to run Playwright tests: {str(e)}"
            }
