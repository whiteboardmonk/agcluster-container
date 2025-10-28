# AgCluster Container

<div align="center">

[![Docker](https://img.shields.io/badge/docker-required-blue)]()
[![UI](https://img.shields.io/badge/UI-Next.js%2015-black)]()
[![Python](https://img.shields.io/badge/python-3.11+-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

[Features](#features) • [Quick Start](#quick-start) • [Web UI](#web-ui) • [Agent Configurations](#agent-configurations) • [API Reference](#api-reference)

</div>

---

## Overview

**AgCluster Container** is a self-hosted platform for running [Claude Agent SDK](https://docs.claude.com/en/api/agent-sdk/overview) instances with a web dashboard and REST API. Each agent runs in an isolated Docker container with configurable tools and resources.

**What it provides:**
- Web UI for monitoring agent execution and managing files
- REST API with Claude SDK capabilities
- Docker-based isolation per session
- Preset agent configurations for common tasks
- File upload, preview, and download

**Current Status:** Alpha (v0.3.0)

---

## Features

### Core Capabilities

- **Claude Agent SDK** - Full agent capabilities via REST API
- **Tool Suite** - Bash, Read, Write, Edit, Grep, Glob, Task, WebFetch, WebSearch, NotebookEdit, TodoWrite
- **BYOK** - Users provide their own Anthropic API keys (never stored)
- **SSE Streaming** - Real-time Server-Sent Events for agent responses
- **Multi-Session** - Multiple concurrent sessions with container isolation
- **Security** - Path traversal protection, session auth, CORS whitelist, file size limits

### Agent Configuration System

- **Preset Configurations** - 4 ready-to-use templates:
  - `code-assistant` - Full-stack development
  - `research-agent` - Web research and analysis
  - `data-analysis` - Statistical analysis with Jupyter
  - `fullstack-team` - Multi-agent orchestration with sub-agents
- **Custom Configurations** - Define agents with specific tools and limits
- **Tool Specialization** - Configure which tools each agent can access
- **Resource Management** - Per-agent CPU, memory, storage limits

### File Operations

- **Upload** - Drag-and-drop file upload to agent workspaces (50MB per file)
- **Browse** - Tree view of workspace files
- **Preview** - Syntax-highlighted code with Monaco editor
- **Download** - Individual files or entire workspace as ZIP
- **Image Support** - Direct preview of PNG, JPG, GIF, etc.

### Web UI

- **Dashboard** - Launch agents from preset configurations
- **Real-time Chat** - SSE streaming with tool execution visibility
- **File Explorer** - Browse, preview, and manage workspace files
- **File Upload** - Drag-and-drop upload with path validation
- **Tool Timeline** - View Bash commands, file operations in real-time
- **Task Tracking** - TodoWrite integration with status summaries
- **Session Management** - Monitor and control active containers

---

## Quick Start

### Prerequisites

- Docker & Docker Compose - [Install Docker](https://docs.docker.com/get-docker/)
- Anthropic API Key - [Get one here](https://console.anthropic.com/)
- Python 3.11+ (optional, for local development)

### 1. Clone and Setup

```bash
git clone https://github.com/whiteboardmonk/agcluster-container.git
cd agcluster-container

# Copy example environment file
cp .env.example .env
```

### 2. Build Docker Images

```bash
# Build with docker compose (recommended)
docker compose build

# Or build individually:
# docker build -t agcluster/agent:latest -f docker/Dockerfile.agent .
# docker build -t agcluster/agent-api:latest -f Dockerfile .
```

First build may take 2-3 minutes.

### 3. Start AgCluster

```bash
# Start the full stack
docker compose up -d

# Check logs
docker compose logs -f
```

AgCluster is now running at `http://localhost:8000`

### 4. Access Web UI

Open your browser to `http://localhost:3000`

1. Enter your Anthropic API key
2. Select an agent configuration (e.g., `code-assistant`)
3. Click "Launch Agent"
4. Start chatting!

### 5. Test the API

**Health Check:**
```bash
curl http://localhost:8000/health
```

**Launch an Agent:**
```bash
curl -X POST http://localhost:8000/api/agents/launch \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "YOUR_ANTHROPIC_API_KEY",
    "config_id": "code-assistant"
  }'
# Response: {"session_id":"conv-abc123...","agent_id":"agent-xyz789","status":"running"}
```

**Send a Message:**
```bash
SESSION_ID="conv-abc123..."  # from launch response

curl -X POST http://localhost:8000/api/agents/${SESSION_ID}/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ANTHROPIC_API_KEY" \
  -d '{"message": "Hello! Tell me what tools you have access to."}'
```

---

## Agent Configurations

### Preset Agents

#### 1. Code Assistant (`code-assistant`)

Full-stack development agent

- **Tools**: Bash, Read, Write, Edit, Grep, Glob, Task, TodoWrite
- **Resources**: 2 CPUs, 4GB RAM, 10GB storage
- **Use Cases**: Feature implementation, debugging, refactoring, testing

```bash
curl -X POST http://localhost:8000/api/agents/launch \
  -H "Content-Type: application/json" \
  -d '{"api_key": "sk-ant-...","config_id": "code-assistant"}'
```

#### 2. Research Agent (`research-agent`)

Web research and information analysis

- **Tools**: WebFetch, WebSearch, Read, Write, Grep, TodoWrite
- **Resources**: 1 CPU, 2GB RAM, 5GB storage
- **Use Cases**: Research reports, source verification, information synthesis

#### 3. Data Analysis Agent (`data-analysis`)

Statistical analysis and data visualization

- **Tools**: Bash, Read, Write, Edit, Grep, Glob, NotebookEdit, TodoWrite
- **Focus**: Pandas, numpy, scipy, scikit-learn, matplotlib
- **Resources**: 2 CPUs, 6GB RAM, 15GB storage
- **Use Cases**: Exploratory data analysis, statistical testing, Jupyter workflows

#### 4. Full-Stack Team (`fullstack-team`)

Multi-agent orchestrator with specialized sub-agents

- **Main Tools**: Task, Read, Glob, Grep, TodoWrite
- **Sub-agents**: Frontend (React), Backend (Python), DevOps (Docker)
- **Resources**: 3 CPUs, 6GB RAM, 10GB storage
- **Use Cases**: Complex features requiring multiple specialists

### Custom Configurations

Create custom agents with inline configurations:

```bash
curl -X POST http://localhost:8000/api/agents/launch \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "sk-ant-...",
    "config": {
      "id": "my-custom-agent",
      "name": "My Custom Agent",
      "allowed_tools": ["Bash", "Read", "Write"],
      "system_prompt": "You are a helpful assistant specializing in...",
      "permission_mode": "acceptEdits",
      "resource_limits": {
        "cpu_quota": 100000,
        "memory_limit": "2g"
      }
    }
  }'
```

### List Available Configurations

```bash
# List all configs
curl http://localhost:8000/api/configs/

# Get specific config details
curl http://localhost:8000/api/configs/code-assistant
```

See `configs/README.md` for detailed configuration documentation.

---

## Web UI

The integrated Next.js dashboard provides a visual interface for managing agents:

### Features

**Launch Dashboard**
- Select from preset agent configurations
- View configuration details (tools, resources, prompts)
- One-click agent launching

**Chat Interface**
- Real-time streaming responses with SSE
- Tool execution visibility (Bash commands, file operations)
- Message history

**File Explorer**
- Tree view of workspace files
- File preview with syntax highlighting (Monaco editor)
- Image preview support
- Download individual files or entire workspace
- Upload files with drag-and-drop

**File Upload**
- Upload to specific directories with path validation
- Multi-file upload with progress tracking
- Overwrite protection
- File size validation (50MB per file)

**Task Tracking**
- TodoWrite integration
- Real-time task status updates
- Collapsible task panel

**Tool Timeline**
- View Bash commands in real-time
- File operations (Read, Write, Edit, Grep)
- Execution status and output

**Session Management**
- View active sessions
- Stop sessions
- Monitor resource usage

Access the UI at `http://localhost:3000` after starting with `docker compose up`.

---

## Architecture

### Platform Architecture

```
┌────────────────────────────────────────────┐
│       Web UI Dashboard (Next.js)           │
│   File explorer, chat, task tracking       │
└──────────────────┬─────────────────────────┘
                   │ HTTP/SSE
                   ▼
┌────────────────────────────────────────────┐
│     AgCluster FastAPI Backend              │
│  • Session management                      │
│  • Container lifecycle                     │
│  • File operations                         │
│  • Agent configuration                     │
└──────────────────┬─────────────────────────┘
                   │ HTTP/SSE
                   ▼
┌────────────────────────────────────────────┐
│   Isolated Agent Container (Docker)        │
│  ┌──────────────────────────────────────┐  │
│  │    Claude Agent SDK                  │  │
│  │  • Session ID: unique per container  │  │
│  │  • Tools: Bash, Read, Write, etc.    │  │
│  │  • Working dir: /workspace           │  │
│  └──────────────────────────────────────┘  │
│                                            │
│  Security: resource limits, no privileges  │
└────────────────────────────────────────────┘
```

### Multi-Session Support

Each session gets an isolated container:

```
Session 1 → Container A (code-assistant)
Session 2 → Container B (research-agent)
Session 3 → Container C (data-analysis)
...
```

---

## API Reference

### Configuration Endpoints

#### `GET /api/configs/`

List all available agent configurations.

**Response:**
```json
{
  "configs": [
    {
      "id": "code-assistant",
      "name": "Code Assistant",
      "description": "Full-stack development agent",
      "allowed_tools": ["Bash", "Read", "Write", ...],
      "has_mcp_servers": false,
      "has_sub_agents": false
    }
  ],
  "total": 4
}
```

#### `GET /api/configs/{config_id}`

Get detailed configuration for a specific agent.

### Agent Management Endpoints

#### `POST /api/agents/launch`

Launch a new agent from configuration.

**Request:**
```json
{
  "api_key": "sk-ant-...",
  "config_id": "code-assistant"
}
```

**Response:**
```json
{
  "session_id": "conv-abc123...",
  "agent_id": "agent-xyz789",
  "config_id": "code-assistant",
  "status": "running"
}
```

#### `GET /api/agents/sessions`

List all active agent sessions.

#### `GET /api/agents/sessions/{session_id}`

Get details about a specific session.

#### `DELETE /api/agents/sessions/{session_id}`

Stop and remove a session.

### Chat Endpoint

#### `POST /api/agents/{session_id}/chat`

Send messages to an active agent session.

**Headers:**
- `Authorization: Bearer YOUR_ANTHROPIC_API_KEY`
- `Content-Type: application/json`
- `Accept: text/event-stream` (for streaming)

**Request:**
```json
{
  "message": "Your message here"
}
```

**Response:**
- Streaming (SSE): Real-time tool execution updates
- Non-streaming: Complete response with final text

### File Operations Endpoints

#### `GET /api/files/{session_id}`

Browse workspace files in tree structure.

#### `GET /api/files/{session_id}/{path}`

Preview file content with syntax highlighting.

#### `POST /api/files/{session_id}/download`

Download entire workspace as ZIP.

#### `POST /api/files/{session_id}/upload`

Upload files to workspace.

**Query Parameters:**
- `target_path` (optional): Target directory
- `overwrite` (default: false): Overwrite existing files

**Request:** Multipart form data with files

**Response:**
```json
{
  "uploaded": [
    {"filename": "file1.txt", "path": "/workspace/file1.txt"}
  ]
}
```

---

## Multi-Provider Support

AgCluster supports multiple deployment platforms through a provider abstraction layer.

### Supported Providers

- **Docker** (default) - Local development and self-hosted
- **Fly Machines** - Production with 300ms boot times

### Configuration

**Docker:**
```bash
# .env
CONTAINER_PROVIDER=docker
```

**Fly Machines:**
```bash
# .env
CONTAINER_PROVIDER=fly_machines
FLY_API_TOKEN=your_token
FLY_APP_NAME=agcluster-agents
FLY_REGION=iad  # Optional
```

See [PROVIDERS.md](PROVIDERS.md) for detailed provider documentation.

---

## Configuration

### Environment Variables

Edit `.env` to configure settings:

```bash
# API Settings
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=true

# Agent Image
AGENT_IMAGE=agcluster/agent:latest

# Default Container Resources
CONTAINER_CPU_QUOTA=200000  # 2 CPUs
CONTAINER_MEMORY_LIMIT=4g
CONTAINER_STORAGE_LIMIT=10g

# Session Management
SESSION_CLEANUP_INTERVAL=300      # 5 minutes
SESSION_IDLE_TIMEOUT=1800         # 30 minutes
```

### Agent Configuration Files

Agent configurations are stored in `configs/presets/` as YAML files.

**Example structure:**
```yaml
id: my-agent
name: My Custom Agent
description: Brief description

system_prompt: |
  You are a specialist in...

allowed_tools:
  - Bash
  - Read
  - Write

resource_limits:
  cpu_quota: 200000      # 2 CPUs
  memory_limit: 4g
  storage_limit: 10g

max_turns: 100
```

See `configs/README.md` for complete documentation.

---

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/whiteboardmonk/agcluster-container.git
cd agcluster-container

# Install dependencies
pip install -r requirements.txt
pip install -e ".[dev]"

# Run locally (without Docker)
python -m agcluster.container.api.main
```

### Build Docker Images

```bash
# Build agent image
docker build -t agcluster/agent:latest -f docker/Dockerfile.agent .

# Build API image
docker build -t agcluster/agent-api:latest -f Dockerfile .

# Or build both
docker compose build
```

### Run Tests

```bash
# Install package
pip install -e ".[dev]"

# Run all tests
pytest tests/

# Run with coverage
pytest --cov=agcluster.container tests/

# Run specific categories
pytest tests/unit/           # Unit tests
pytest tests/integration/    # Integration tests
pytest tests/e2e/           # E2E tests (require Docker)
```

**Test Coverage:**
- Unit tests - Core components, providers, configuration
- Integration tests - API endpoints, file operations
- E2E tests - Full workflows with Docker containers

### Monitoring

**View logs:**
```bash
# All logs
docker compose logs -f

# API only
docker compose logs -f api

# Specific container
docker logs <container-id>
```

**Check running containers:**
```bash
docker ps | grep agcluster
```

---

## Documentation

- **[Agent Configuration](configs/README.md)** - Configuration reference
- **[Multi-Provider Setup](PROVIDERS.md)** - Deploy on Docker, Fly.io, etc.
- **[Security Audit](SECURITY_AUDIT_REPORT.md)** - Security features
- **[Web UI Guide](src/agcluster/container/ui/README.md)** - Dashboard setup

---

## Use Cases

**Self-Hosted Development Platform**
- Visual dashboard for agent monitoring
- File browser for inspecting artifacts
- Task tracking and session management

**Custom Agent Infrastructure**
- Multi-tenant agent hosting
- REST API gateway for Claude SDK
- Container orchestration

**Code Review & Analysis**
- Automated PR reviews
- Security scanning
- Documentation generation

**Data Science & Analytics**
- Jupyter-style exploration with pandas/numpy
- Statistical analysis
- Interactive data debugging

**Research & Intelligence**
- Multi-source research
- Source verification
- Competitive intelligence

---

## Roadmap

### Completed (v0.3.0)
- Integrated Web UI with Next.js 15
- File upload with drag-and-drop
- Claude-native REST API with SSE
- Session management with auto-cleanup
- Agent configuration system (4 presets)
- File operations (browse, preview, download, upload)
- Multi-provider support (Docker, Fly)
- Comprehensive test suite

### Future
- Additional agent presets
- Multi-user authentication
- Usage metering and quotas
- Monitoring and metrics
- Kubernetes deployment
- Conversation export

---

## Troubleshooting

### Container won't start

```bash
# Check Docker
docker ps

# Check logs
docker compose logs api

# Rebuild
docker compose build --no-cache
```

### Connection errors

```bash
# Check container logs
docker logs <container-id>

# Verify network
docker network inspect agcluster-container_agcluster-network
```

### Tests failing

```bash
# Reinstall dependencies
pip install -e ".[dev]"

# Run with verbose output
pytest tests/ -v
```

Need help? [Open an issue](https://github.com/whiteboardmonk/agcluster-container/issues)

---

## Security

- Containers run with minimal privileges
- Path traversal protection
- Session-based authorization
- File size limits (50MB per file)
- Network isolation
- Resource limits enforced

---

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

## License

MIT License - see [LICENSE](LICENSE)

---

**Built with ❤️ by whiteboardmonk & Claude Code. Not affiliated with or endorsed by Anthropic PBC**
