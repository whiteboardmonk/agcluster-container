# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AgCluster Container is a containerized runtime for Claude Agent SDK instances with a REST API for managing agent sessions. It allows Claude agents to run in isolated Docker containers with configurable tools and resources, accessible via Web UI and HTTP API.

**Key Concept**: Users bring their own Anthropic API keys (BYOK), and AgCluster creates persistent Docker containers per conversation running Claude SDK agents with configurable tools and resources. The system supports preset agent configurations (code-assistant, research-agent, data-analysis, fullstack-team) and custom inline configs. Containers are reused across messages in the same conversation thread, maintaining context.

## Architecture

```
Web UI / API Client
  ↓ POST /api/agents/launch (create session with config)
  ↓ POST /api/agents/{session_id}/chat (send messages)
AgCluster API (FastAPI)
  ↓ Creates Docker container with session
  ↓ HTTP communication (http://{container_ip}:3000)
Agent Container (Claude SDK)
  ↓ ClaudeSDKClient initialized with session ID
  ↓ Executes tools in /workspace
  ↓ Streams responses via HTTP
AgCluster API
  ↓ Streams Claude SDK events as JSON
  ↓ Returns to client
```

### Session Management Flow

```
Container Startup
  ↓
AgentServer.__init__()
  ↓
AgentServer.initialize_sdk()
  ↓ Creates ClaudeSDKClient(options)
  ↓ Enters context manager (session created)
  ↓ Session ID: e.g., "b28c5a6a-0f94-4840-8eb9-34f5e69c0641"
  ↓
WebSocket Server Ready
  ↓
[Query 1] client.query() → client.receive_messages()
[Query 2] client.query() → client.receive_messages() [same session]
[Query N] client.query() → client.receive_messages() [same session]
  ↓
Container Shutdown
  ↓
SDK context manager cleanup
```

### Core Components

1. **FastAPI API Layer** (`src/agcluster/container/api/`)
   - Claude-native chat endpoint (`/api/agents/{session_id}/chat`)
   - Agent configuration endpoints (`/api/configs`, `/api/agents/launch`)
   - Session management endpoints (`/api/agents/sessions`)
   - File operations API (`/api/files`)
   - Manages container lifecycle
   - Streams Claude SDK events as JSON

2. **Configuration System** (`src/agcluster/container/models/agent_config.py`, `src/agcluster/container/core/config_loader.py`)
   - YAML-based agent presets in `configs/presets/`
   - 4 built-in presets: code-assistant, research-agent, data-analysis, fullstack-team
   - Supports inline custom configurations
   - Validates tools, resources, prompts, and sub-agents
   - Multi-agent orchestration support

3. **Session Manager** (`src/agcluster/container/core/session_manager.py`)
   - Maps conversation IDs and session IDs to containers
   - Stores agent configuration with each session
   - Manages container lifecycle per conversation
   - Background cleanup of idle sessions (30 min timeout)
   - Prevents resource leaks through automatic cleanup

4. **Container Manager** (`src/agcluster/container/core/container_manager.py`)
   - Creates/stops Docker containers dynamically with config-based resources
   - Uses lazy Docker client initialization (important: allows API to start without Docker)
   - Manages WebSocket connections to containers
   - Tracks active containers in-memory
   - Applies CPU, memory, and storage limits from configs

5. **Agent Server** (`container/agent_server.py`)
   - Runs inside each Docker container
   - WebSocket server on port 8765
   - Wraps Claude Agent SDK with configurable tools
   - Processes queries with configured tools (Bash, Read, Write, Grep, Task, WebFetch, NotebookEdit, TodoWrite)
   - Supports sub-agent delegation for multi-agent workflows

6. **File Operations API** (`src/agcluster/container/api/files.py`)
   - Workspace file browsing (`GET /api/files/{session_id}`)
   - File content preview with syntax highlighting (`GET /api/files/{session_id}/{path}`)
   - Individual file download (`GET /api/files/{session_id}/{path}/download`)
   - Workspace ZIP download (`POST /api/files/{session_id}/download`)
   - **File upload to workspace** (`POST /api/files/{session_id}/upload`)
   - Supports text files, images (PNG/JPG preview), and binary files
   - Auto-detects file types and provides appropriate MIME types
   - Upload security: size limits (50MB/file, 200MB/request), MIME type validation, filename sanitization, path traversal protection

8. **Web UI** (`src/agcluster/container/ui/`)
   - Next.js 15 + React + TypeScript frontend
   - Real-time chat interface with AI SDK v5
   - Agent configuration builder with preset templates
   - Session management dashboard
   - File explorer with tree view, preview, and **upload support**
   - Tool execution timeline with status tracking
   - TodoWrite task tracking panel
   - Collapsible panels for tasks and tool execution
   - Monaco editor for code file viewing
   - File upload modal with drag-and-drop support
   - Responsive glassmorphic design

## Namespace Package Structure

This project uses **PEP 420 namespace packages** under the `agcluster` namespace:

```
src/
└── agcluster/              # Namespace (NO __init__.py here)
    └── container/         # This package (HAS __init__.py)
        ├── __init__.py
        ├── api/
        ├── core/
        └── models/
```

**Critical**: The `src/agcluster/` directory must NOT have an `__init__.py`. This allows other AgCluster projects (cli, dashboard) to share the namespace.

**Imports**: Always use `from agcluster.container import X`, never relative imports across the namespace boundary.

## Development Commands

### Local Development (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt
pip install -e ".[dev]"

# Run API locally
python -m uvicorn agcluster.container.api.main:app --host 0.0.0.0 --port 8000

# Run with auto-reload
python -m agcluster.container.api.main
```

### Docker Development

```bash
# Build agent image (Claude SDK container)
docker build -t agcluster/agent:latest -f docker/Dockerfile.agent .

# Build API image
docker build -t agcluster/agent-api:latest -f Dockerfile .

# Start full stack
docker compose up -d

# View logs
docker compose logs -f

# Stop everything
docker compose down
```

### Testing

**Test Suite**: Run `pytest tests/` (unit, integration, e2e markers); target 80%+ coverage locally

```bash
# Run all tests
pytest tests/

# Run specific test category
pytest tests/unit/test_translator.py -v           # 21 tests - Message translation
pytest tests/unit/test_container_manager.py       # 25 tests - Container lifecycle
pytest tests/unit/test_session_manager.py -v      # 26 tests - Session management
pytest tests/unit/test_config_loader.py           # 14 tests - Configuration loading
pytest tests/unit/test_agent_config.py            # 29 tests - Agent config models
pytest tests/integration/test_api_endpoints.py    # 13 tests - Chat completions API
pytest tests/integration/test_config_api.py       # 5 tests - Config/agent endpoints

# Run with coverage
pytest --cov=agcluster.container tests/

# Run with markers
pytest -m unit        # Unit tests only (115 tests)
pytest -m integration # Integration tests (18 tests)
```

**Test Coverage**:
- Message translation (OpenAI ↔ Claude): 21 tests
- Container lifecycle management: 25 tests
- Session management and cleanup: 26 tests
- Configuration system (models + loading): 43 tests
- API endpoints (completions, configs, agents): 18 tests
- All tests use TDD approach

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff src/ tests/

# Type check
mypy src/
```

## Critical Design Patterns

### 1. Lazy Docker Client Initialization

The `ContainerManager` uses lazy initialization to prevent crashes when Docker isn't available:

```python
class ContainerManager:
    def __init__(self):
        self._docker_client = None  # Don't initialize here!

    @property
    def docker_client(self):
        if self._docker_client is None:
            self._docker_client = docker.from_env()
        return self._docker_client
```

**Why**: Allows FastAPI to start and import successfully even when Docker isn't running, which is useful for development and testing.

### 2. Dual-Mode Session Management

AgCluster implements sophisticated session management with two modes:

**Session Manager** (`src/agcluster/container/core/session_manager.py`):
- Maps both conversation IDs (legacy) and session IDs (new) to persistent containers
- Stores agent configuration with each session
- Reuses same container for all messages in a conversation/session
- Background cleanup task removes idle sessions after 30 minutes
- Runs cleanup check every 5 minutes

**Two Modes**:

**Mode 1: Config-Based Sessions (New)**
1. Client calls `/api/agents/launch` with `config_id` or inline `config`
2. Returns `session_id`
3. Client sends messages to `/chat/completions` with `X-Session-ID` header
4. Container reused with config-defined tools and resources

**Mode 2: Conversation-Based (Legacy - Third-Party Clients)**
1. Client sends `X-Conversation-ID` header with each request
2. Session Manager checks if container exists for that conversation
3. If exists: Reuses container (context maintained!)
4. If new: Creates new container with default config
5. Background task cleans up inactive sessions

**Benefits**:
- ✅ Full conversation context maintained across messages
- ✅ Agent specialization via configurations
- ✅ Efficient resource usage (one container per active conversation/session)
- ✅ Automatic cleanup prevents resource leaks
- ✅ Claude SDK session persists throughout conversation
- ✅ Backward compatible with third-party clients

### 3. Agent Configuration System

AgCluster supports flexible agent configurations via YAML presets or inline configs:

**Configuration Files** (`configs/presets/*.yaml`):
- **code-assistant**: Full-stack development (Bash, Read, Write, Edit, Grep, Glob, Task, TodoWrite)
- **research-agent**: Web research (WebFetch, WebSearch, Read, Write, Grep, TodoWrite)
- **data-analysis**: Statistical analysis and Jupyter notebooks (Bash, Read, Write, Edit, Grep, Glob, NotebookEdit, TodoWrite)
- **fullstack-team**: Multi-agent orchestrator with 3 sub-agents (frontend, backend, devops)

**Config Structure**:
```yaml
id: agent-name
name: Human-readable name
description: Brief description
allowed_tools: [Bash, Read, Write, TodoWrite]
system_prompt: "You are a specialist in..."
permission_mode: acceptEdits
resource_limits:
  cpu_quota: 200000    # 2 CPUs (100000 = 1 CPU)
  memory_limit: 4g
  storage_limit: 10g
max_turns: 100
agents:  # Optional: for multi-agent orchestration
  subagent_name:
    description: "..."
    prompt: "..."
    tools: [...]
```

**Key Features**:
- ✅ Tool specialization per agent type
- ✅ Resource limits prevent runaway containers
- ✅ Multi-agent orchestration support
- ✅ TodoWrite for all presets (task tracking)
- ✅ NotebookEdit for data-analysis (Jupyter support)
- ✅ Inline custom configs via `/api/agents/launch`

**Loading Flow**:
1. `ConfigLoader.load_config(config_id)` reads YAML from `configs/presets/`
2. Validates against `AgentConfig` Pydantic model
3. Checks tool availability, resource format, sub-agent structure
4. Returns typed config object
5. Used by `ContainerManager` to create containers with correct settings

### 4. BYOK (Bring Your Own Key)

Users provide Anthropic API keys via `Authorization: Bearer <key>` header. Keys are passed to containers via environment variables but never stored.

### 5. WebSocket Communication

API ↔ Container communication uses WebSocket on port 8765:
- API sends: `{"type": "query", "content": "..."}`
- Container streams: `{"type": "message", "data": {...}}`
- Container completes: `{"type": "complete", "status": "success"}`

## Configuration

### Environment Variables

Settings are loaded via Pydantic Settings from environment variables (`.env` file):

```bash
# src/agcluster/container/core/config.py
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=true
AGENT_IMAGE=agcluster/agent:latest

# Default container resources (used when no config specified)
CONTAINER_CPU_QUOTA=200000  # 2 CPUs
CONTAINER_MEMORY_LIMIT=4g
CONTAINER_STORAGE_LIMIT=10g

# Default agent settings
DEFAULT_SYSTEM_PROMPT="You are a helpful AI assistant."
DEFAULT_ALLOWED_TOOLS=Bash,Read,Write,Grep
DEFAULT_PERMISSION_MODE=acceptEdits
DEFAULT_MAX_TURNS=100

# Session management
SESSION_CLEANUP_INTERVAL=300      # Check every 5 minutes
SESSION_IDLE_TIMEOUT=1800         # 30 minutes idle timeout
```

### Agent Configuration Files

Agent presets are stored in `configs/presets/` as YAML files. See "Agent Configuration System" section above for structure and details. The system includes:
- ✅ 5 preset configurations (code-assistant, research-agent, data-analysis, github-code-review, fullstack-team)
- ✅ Custom inline config support via `/api/agents/launch`
- ✅ Full validation via Pydantic models
- ✅ Multi-agent orchestration (sub-agents)
- ✅ Per-agent tool specialization and resource limits (with MCP servers where configured)
- ✅ Launch-time MCP credentials (`mcp_env`) must match keys declared under each server's `env`; reserved container env vars are blocked from override

Documentation: `configs/README.md`

## Important Implementation Notes

### Claude SDK Integration

The `container/agent_server.py` uses the Claude Agent SDK with session management:

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from claude_agent_sdk.types import AssistantMessage, ToolUseBlock, TextBlock

# Initialize client once at startup (maintains session across queries)
async def initialize_sdk(self):
    options = ClaudeAgentOptions(
        cwd="/workspace",
        system_prompt=self.system_prompt,
        allowed_tools=self.allowed_tools,
        permission_mode="acceptEdits"
    )
    self.sdk_client = ClaudeSDKClient(options)
    await self.sdk_client.__aenter__()

# Process queries using the session-based client
async def process_query(self, websocket, query: str):
    await self.sdk_client.query(query)
    async for message in self.sdk_client.receive_messages():
        # Stream responses back to API
```

**Key Features**:
- ✅ Session ID tracking per container
- ✅ Persistent context across multiple queries (when container is reused)
- ✅ Configurable tool access (Bash, Read, Write, Grep, Task, WebFetch, NotebookEdit, TodoWrite)
- ✅ Multi-agent delegation support (Task tool for sub-agents)
- ✅ Proper lifecycle management via context manager

**If SDK API changes**, update:
1. Import paths in `agent_server.py`
2. Message type handling in `_format_message()`
3. Query/response methods

### Container Networking

Containers use custom bridge networking (`agcluster-container_agcluster-network`). The API:
1. Gets container IP from custom network: `container.attrs['NetworkSettings']['Networks'][network_name]['IPAddress']`
2. Waits for container readiness (3s fixed delay for WebSocket server startup)
3. Connects via WebSocket: `ws://{container_ip}:8765`

**Important**: For custom networks, IP addresses are in the `Networks` dictionary, not the root `IPAddress` field.

### OpenAI-Compatible Format

Translation layer supports OpenAI format for third-party client compatibility:

```json
{
  "id": "chatcmpl-xyz",
  "object": "chat.completion.chunk",
  "created": 1234567890,
  "model": "claude-sonnet-4.5",
  "choices": [{
    "index": 0,
    "delta": {"content": "text"},
    "finish_reason": null
  }]
}
```

## Testing the API

### Health Check
```bash
curl http://localhost:8000/health
```

### List Available Configurations
```bash
curl http://localhost:8000/api/configs/
```

### Get Specific Configuration
```bash
curl http://localhost:8000/api/configs/data-analysis
```

### Launch Agent with Config
```bash
curl -X POST http://localhost:8000/api/agents/launch \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "YOUR_ANTHROPIC_API_KEY",
    "config_id": "code-assistant"
  }'
# Returns: {"session_id": "conv-abc123...", "agent_id": "agent-xyz...", ...}
```

### Chat with Config-Based Session
```bash
curl -X POST http://localhost:8000/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ANTHROPIC_API_KEY" \
  -H "X-Session-ID: conv-abc123..." \
  -d '{
    "model": "claude-sonnet-4.5",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": true
  }'
```

### Upload Files to Workspace
```bash
curl -X POST "http://localhost:8000/api/files/conv-abc123.../upload?overwrite=false" \
  -H "Authorization: Bearer YOUR_ANTHROPIC_API_KEY" \
  -F "files=@/path/to/file1.txt" \
  -F "files=@/path/to/file2.py"
# Returns: {"session_id": "conv-abc123...", "uploaded": ["file1.txt", "file2.py"], ...}
```

## Current Status

**State**: ✅ **Production Ready with Agent Configuration System**

**Core Features**:
- ✅ FastAPI endpoints (`/`, `/health`, `/api/agents/*`, `/api/configs`, `/api/files`)
- ✅ Claude-native chat API (`/api/agents/{session_id}/chat`)
- ✅ Agent configuration endpoints (`/api/configs`, `/api/agents/launch`, `/api/agents/sessions`)
- ✅ 5 preset agent configurations (adds `github-code-review` with MCP)
- ✅ Custom inline config support
- ✅ Multi-agent orchestration (fullstack-team with 3 sub-agents)
- ✅ Config-based session management with persistent containers
- ✅ Background cleanup task (30-minute idle timeout)
- ✅ Claude SDK integration with configurable tools (Bash, Read, Write, Grep, Task, WebFetch, NotebookEdit, TodoWrite)
- ✅ TodoWrite tool for all presets (task tracking)
- ✅ NotebookEdit tool for data-analysis (Jupyter support)
- ✅ MCP server support with launch-time credentials and auto-allowed MCP tools
- ✅ Docker container isolation per conversation/session
- ✅ Per-agent resource limits (CPU, memory, storage)
- ✅ Namespace package structure for modularity
- ✅ Web UI with Next.js 15 + React + TypeScript
- ✅ File operations API with security (browse, preview, download, **upload**)
- ✅ File upload with multi-provider support (Docker + Fly.io)
- ✅ Upload security: size limits, MIME validation, filename sanitization
- ✅ Session ownership validation (Authorization header required)
- ✅ Path traversal protection
- ✅ Zip bomb protection (1GB/10K files limit)
- ✅ CORS whitelist configuration
- ✅ Cryptographically secure session IDs
- ✅ Real-time tool execution tracking
- ✅ TodoWrite smart summaries in UI
- ✅ File explorer with syntax highlighting and upload button
- ✅ File upload modal with drag-and-drop support
- ✅ Monaco editor integration for code viewing

**Tested and Verified**:
- ✅ Multi-turn conversations with context preservation
- ✅ Config-based agent launching and session management
- ✅ All presets load and validate successfully (including MCP-enabled configs)
- ✅ Inline custom configuration support
- ✅ Tool specialization per agent type
- ✅ Resource limits enforcement
- ✅ Automatic session cleanup and resource management
- ✅ Docker image builds and networking
- ✅ HTTP communication and streaming
- ✅ Web UI chat interface and agent builder
- ✅ File browsing, preview, download, and **upload** (with auth)
- ✅ File upload via UI with progress tracking
- ✅ Image file preview (PNG, JPG, etc.)
- ✅ Workspace ZIP download (with size limits)
- ✅ Real-time tool event tracking
- ✅ TodoWrite intelligent task summaries
- ✅ Security fixes (path traversal, session ownership, CORS, zip bomb, upload validation)

## Future Enhancements

- Additional agent presets (security-auditor, content-writer, project-task-planner, etc.)
- Multi-user authentication and authorization
- Usage metering and quotas per API key
- Web dashboard UI for monitoring active sessions
- Kubernetes deployment support
- Agent marketplace and sharing
- Agent-to-agent communication enhancements
- Conversation export and history persistence
- Never add this to the commit message: 🤖 Generated with Claude Code                                                                                                     Co-Authored-By: Claude <noreply@anthropic.com>
- Always run ruff check src/ tests/
- Always run black --check src/ tests/
