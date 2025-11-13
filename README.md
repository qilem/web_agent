# WAA (Web-App Agent)

> An autonomous LLM-powered coding agent that creates fully functional web applications from natural language instructions

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Node.js](https://img.shields.io/badge/node.js-18.x-green.svg)](https://nodejs.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## Overview

WAA (Web-App Agent) is a agentic system that autonomously designs, codes, tests, and iterates on web applications. Simply provide natural language instructions, and WAA handles the rest—from writing frontend HTML/CSS/JavaScript to implementing backend Express servers with database integration.

### Key Features

- **Autonomous Development**: End-to-end web application creation without manual coding
- **Tool-Based Architecture**: Modular tool system for file operations, testing, server management, and TODO tracking
- **Iterative Problem Solving**: Agent identifies issues, runs tests, and fixes bugs autonomously
- **Multiple LLM Support**: Compatible with Google Gemini and other language models
- **Comprehensive Testing**: Integrated Supertest (API) and Playwright (UI) testing frameworks
- **Database Integration**: Support for MySQL, SQLite, and other databases (extra credit implementation)

## Demo Projects

### 1. Personal Website
A fully responsive personal portfolio website with custom styling and animations.

**Features**:
- Responsive design with modern CSS
- Interactive animations and hover effects
- Multi-section layout (About, Skills, Projects, Contact)
- Mobile-friendly navigation

### 2. Chat Room Application
A real-time chat application with persistent message storage.

**Features**:
- Real-time message updates (polling/WebSocket)
- User identification system
- Message history
- RESTful API backend (Express.js)
- Responsive UI with modern design

### 3. Voting Website (Custom Project + Extra Credit)
An online voting platform with MySQL database integration enforcing one vote per user.

**Features**:
- MySQL database backend
- User authentication
- One vote per username constraint (unique composite index)
- Real-time vote tallying
- Poll creation and management
- Secure database connection with least-privilege user model

**Technical Highlights**:
- Custom database tool implementation for MySQL operations
- Environment-based configuration with `.env` files
- Database migration system using `INFORMATION_SCHEMA`
- Connection pooling with `mysql2/promise`
- Schema versioning and automatic seeding

## Architecture

### Agent Core (`waa/agent.py`)

The central agentic loop that orchestrates all operations:

```
Initialize → Load Instructions → Query LLM → Parse Response → Execute Tools → Repeat
```

**Key Components**:
- **Tool Registry**: Dynamic tool loading and management
- **History Management**: Conversation state tracking across iterations
- **LLM Integration**: Flexible interface for multiple LLM providers
- **Error Recovery**: Graceful error handling with retry mechanisms

### Tool System

WAA provides a rich set of tools for autonomous development:

#### File System Tools (`waa/tools/fs.py`)
- `fs.read`: Read file contents with metadata
- `fs.write`: Create or overwrite files with directory creation
- `fs.edit`: Find-and-replace editing operations
- `fs.delete`: Safe file deletion with protected file checks
- `fs.mkdir`: Directory creation with parent support
- `fs.rmdir`: Directory removal (recursive option)
- `fs.ls`: Directory listing with file metadata

**Security Features**:
- Path validation (prevents directory traversal)
- Protected file list enforcement
- Working directory confinement

#### TODO Management (`waa/tools/todo.py`)
- `todo.add`: Create tracked tasks
- `todo.list`: View pending/completed tasks
- `todo.complete`: Mark tasks as done
- `todo.remove`: Delete tasks

#### Server Management (`waa/tools/server.py`)
- `npm.init`: Initialize Node.js projects
- `npm.start`: Launch development servers
- `npm.stop`: Terminate running servers
- `npm.status`: Check server health
- `npm.logs`: View server output

#### Testing Tools
- **Supertest** (`waa/tools/supertest.py`): API endpoint testing
- **Playwright** (`waa/tools/playwright.py`): Browser-based UI testing

## Installation

### Prerequisites

- Python 3.8 or higher
- Node.js 18.x or higher (with npm)
- Git

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/waa-web-app-agent.git
   cd waa-web-app-agent
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install WAA CLI**:
   ```bash
   pip install -e .
   ```

5. **Verify installation**:
   ```bash
   waa --help
   ```

### LLM Configuration

Set up your Google Gemini API key (or other LLM provider):

```bash
export GEMINI_API_KEY="your_api_key_here"
```

For persistent configuration, add this to your `~/.bashrc` or `~/.zshrc`.

## Usage

### Basic Usage

Navigate to a project directory with a `.waa` configuration folder and run:

```bash
waa
```

Or specify a working directory:

```bash
waa --working-dir targets/personal_website
```

### Debug Mode

Watch the agent think in real-time:

```bash
waa --working-dir targets/chat_room --debug
```

### Project Structure

Every WAA project requires this structure:

```
my-project/
├── .waa/
│   ├── config.json       # Agent configuration
│   └── instruction.md    # Natural language instructions
└── (files created by agent)
```

**Example `config.json`**:
```json
{
  "max_turns": 50,
  "llm_type": "gemini",
  "model": "gemini-2.0-flash-thinking-exp",
  "allowed_tools": ["fs", "npm", "supertest", "playwright", "todo"],
  "protected_files": [".waa/config.json", ".waa/instruction.md"]
}
```

**Example `instruction.md`**:
```markdown
# Personal Website

Create a personal portfolio website with the following:
- Hero section with name and tagline
- About section with bio
- Skills section with tech stack
- Projects showcase
- Contact section with links

Style: Modern, dark theme with blue accents
Effects: Smooth scrolling, hover animations, responsive design
```


### Viewing Results

After WAA completes, start the application:

```bash
cd targets/personal_website
npm start
```

Then visit `http://localhost:3000` in your browser.

## Project Logs

WAA generates detailed logs during execution:

- **`.waa/agent.log`**: Complete agent activity log (LLM queries, tool calls, results)
- **`.waa/server.log`**: Server output when running `npm start`
- **`.waa/todo.json`**: Current TODO list state

Check `agent.log` to understand the agent's decision-making process!

## Technical Implementation

### Prompt Engineering

The system prompt teaches the LLM to:
- Use structured tool calling with JSON syntax
- Follow iterative problem-solving patterns
- Initialize projects properly (package.json, dependencies)
- Run tests and fix issues autonomously
- Terminate gracefully when complete

**Tool Call Protocol**:
```xml
<tool_call>{"tool": "fs.write", "arguments": {"path": "index.html", "content": "..."}}</tool_call>
```

**Termination Protocol**:
```xml
<terminate>
```

### History Management

The agent maintains a structured conversation history:
- `SystemPrompt`: Initial instructions and tool descriptions
- `UserInstruction`: The natural language task specification
- `LLMResponse`: Model outputs and reasoning
- `ToolCallResult`: Execution results with success/error data

This enables:
- Context preservation across iterations
- Error recovery and retry logic
- Complete audit trails for debugging

### Tool Validation

All tools implement schema-based argument validation:

```python
class FileSystemTool(Tool):
    def __init__(self):
        super().__init__("fs.write")
        self.schema.register_argument("path", str, required=True)
        self.schema.register_argument("content", str, required=True)

    def execute(self, arguments):
        # Validate arguments
        self.schema.validate(arguments)
        # Execute with error handling
        try:
            path = Path(arguments["path"])
            path.write_text(arguments["content"])
            return {"ok": True, "data": {"path": str(path)}}
        except Exception as e:
            return {"ok": False, "error": str(e)}
```

## Database Integration (Extra Credit)

The voting website demonstrates advanced database integration:

### MySQL Setup

```bash
# Install MySQL
sudo apt install -y mysql-server

# Disable autostart
sudo systemctl disable mysql
sudo systemctl start mysql
```

### Database Initialization

```sql
CREATE DATABASE IF NOT EXISTS vote_site
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'user'@'localhost' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON vote_site.* TO 'user'@'localhost';
FLUSH PRIVILEGES;
```

### Application Integration

- **Schema Management**: `server/sql/schema.sql` for table definitions
- **Connection Pooling**: `mysql2/promise` for efficient connections
- **Migration System**: Automated schema updates via `INFORMATION_SCHEMA`
- **Security**: Least-privilege user model, `.env` for credentials
- **Data Integrity**: Unique composite index for one-vote-per-user constraint

## Development

### Adding Custom Tools

1. Create a new tool file in `waa/tools/`:

```python
from waa.tool import Tool

class MyCustomTool(Tool):
    def __init__(self):
        super().__init__("my.tool")
        self.schema.register_argument("input", str, required=True)

    def description(self) -> str:
        return "Description of what the tool does"

    def execute(self, arguments: dict) -> dict:
        # Implementation
        return {"ok": True, "data": {...}}
```

2. Register in `agent.py`:

```python
from waa.tools.my_tool import MyCustomTool

def initialize_tool_registry(self):
    # ... existing tools
    self.tool_registry.register(MyCustomTool())
```


## acknowledgement

This project is based on https://github.com/machine-programming/assignment-3


---
