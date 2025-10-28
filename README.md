# AgCluster Container

<div align="center">

> 🚀 **Claude Agent Cloud**

[![Docker](https://img.shields.io/badge/docker-required-blue)]()
[![UI](https://img.shields.io/badge/UI-Next.js%2015-black)]()
[![Python](https://img.shields.io/badge/python-3.11+-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

[Why AgCluster?](#why-agcluster-container) • [Features](#features) • [Web UI](#-web-ui-dashboard) • [Quick Start](#quick-start) • [File Operations](#file-operations-api) • [Agent Configurations](#agent-configurations) • [Architecture](#architecture) • [API Reference](#api-reference)

</div>

---

## 📖 Overview

**AgCluster Container** is a self-hosted developer platform for building and managing [Claude Agent SDK](https://docs.claude.com/en/api/agent-sdk/overview) applications. Think of it as **"Claude Code in a box"** with visual management tools, real-time monitoring, and a REST API.

**🎯 What You Get**:
- 🖥️ **Integrated Web UI** - Next.js dashboard with real-time tool execution monitoring
- 🔌 **Claude-Native REST API** - Full Claude SDK capabilities via HTTP API
- 🐳 **Docker-Based Isolation** - Each agent runs in its own secure container
- 📊 **Resource Monitoring** - Live resource usage, task tracking, and session management
- ⚙️ **Visual Agent Builder** - Configure agents with preset templates or custom YAML

**🌟 The Platform Approach**: Unlike API-only solutions, AgCluster Container provides both the infrastructure layer (Claude SDK API) and the management layer (Web UI) in a single, integrated package.

### ✅ Current Status (v0.2.0)

- ✅ **Integrated Web UI** - Next.js 15 dashboard with real-time monitoring
- ✅ **Comprehensive Testing** - Backend unit and integration tests
- ✅ **File Operations** - Secure browse, preview, and download workspace files
- ✅ **Tool Execution Panel** - Real-time streaming of Bash, Read, Write, and more
- ✅ **Task Tracking** - TodoWrite integration with intelligent status summaries
- ✅ **Resource Monitoring** - Live CPU/memory/disk usage per agent container
- ✅ **Agent Configuration System** - 4 preset configs + inline config support
- ✅ **Session Management** - Persistent containers with auto-cleanup (30-min timeout)
- ✅ **Security Hardened** - Path traversal protection, session auth, CORS whitelist, zip bomb protection

---

## 🤔 Why AgCluster Container?

### Developer Platform for Claude Agent SDK

AgCluster Container is a self-hosted solution that combines:
- 🖥️ **Visual Management UI** - See tool executions in real-time, not just API responses
- 🤖 **Native Claude SDK** - Full agent harness with complete tool suite access
- 🐳 **Docker Isolation** - Multi-user ready with container-per-session
- 📊 **Built-in Monitoring** - Resource usage, task tracking, session management
- ⚙️ **Visual Configuration** - Agent builder UI with preset templates and custom configs
- 🔌 **REST API** - Full Claude SDK capabilities accessible via HTTP endpoints

---

## ✨ Features

### Core Capabilities

- 🤖 **Claude Agent SDK Access** - Full agent capabilities (same harness powering Claude Code) via REST API
- 🛠️ **Complete Tool Suite** - Bash, Read, Write, Grep, Task, WebFetch, WebSearch, NotebookEdit, TodoWrite, MCP extensibility
- 🔐 **BYOK (Bring Your Own Key)** - Users provide their own Anthropic API keys (never stored)
- 📡 **SSE Streaming Support** - Real-time Server-Sent Events streaming for all agent responses
- 🐳 **Multi-Session Isolation** - Run 10+ concurrent sessions with full container isolation
- 🔒 **Security Hardened** - Path traversal protection, session auth, CORS whitelist, zip bomb protection, minimal privileges, dropped capabilities

### Agent Configuration System

- 📋 **Preset Configurations** - 4 ready-to-use agent templates (code-assistant, research-agent, data-analysis, fullstack-team)
- ⚙️ **Custom Configurations** - Define your own agents with specific tools, prompts, and resource limits
- 🎯 **Tool Specialization** - Configure exactly which tools each agent can access
- 🤝 **Multi-Agent Orchestration** - Fullstack-team preset with 3 specialized sub-agents (frontend, backend, devops)
- 📓 **Jupyter Support** - Data-analysis preset includes NotebookEdit for reproducible analysis workflows
- 💾 **Resource Management** - Per-agent CPU, memory, and storage limits
- 🔗 **MCP Server Integration** - Configure custom Model Context Protocol servers per agent
- 📝 **Task Tracking** - All presets include TodoWrite for multi-step workflow visibility

### Session Management

- 💬 **Config-Based Sessions** - Launch agents from presets or inline configs via `/api/agents/launch`
- 🔄 **Context Preservation** - Same Claude SDK session reused across all messages
- 🧹 **Auto-Cleanup** - Background task removes idle sessions after 30 minutes
- 🎯 **Session Tracking** - List active sessions, view details, stop sessions via API
- ⚙️ **Resource Efficiency** - One container per active session, not per message
- 🔐 **Session Authorization** - API key verification prevents cross-session access

### Technical Features

- ⚡ **Adaptive Readiness Detection** - WebSocket-based container health checks for 100% reliability
- 🎯 **Session Isolation** - Each container maintains independent Claude SDK session with unique ID
- 🌐 **Custom Networking** - Bridge network isolation for security
- 📊 **Test-Driven Development** - Comprehensive test suite (212 unit + integration tests) with 66% code coverage
- 🚀 **Lazy Initialization** - Docker client lazy-loads for better development experience
- 🔄 **WebSocket Communication** - Bidirectional real-time communication between API and agents

### File Operations API

- 📁 **Workspace Browsing** - Tree view of all files created by agents
- 👁️ **File Preview** - Syntax-highlighted code viewing with Monaco editor
- 🖼️ **Image Support** - Direct preview of PNG, JPG, GIF, and other image formats
- ⬇️ **Individual Downloads** - Download any workspace file with proper MIME types
- 📦 **Workspace Export** - One-click ZIP download of entire workspace
- 🎨 **Auto-Detection** - Automatic language detection for 30+ file types
- ⚡ **Streaming Support** - Efficient handling of binary and large files

## 🚀 Quick Start

### Prerequisites

- **Docker & Docker Compose** - [Install Docker](https://docs.docker.com/get-docker/)
- **Anthropic API Key** - [Get one here](https://console.anthropic.com/)
- **Python 3.11+** - For local development (optional)

### 1️⃣ Clone and Setup

```bash
git clone https://github.com/whiteboardmonk/agcluster-container.git
cd agcluster-container

# Copy example environment file
cp .env.example .env
```

### 2️⃣ Build Docker Images

```bash
# Build both images with docker compose (recommended)
docker compose build

# Or build individually:
# docker build -t agcluster/agent:latest -f docker/Dockerfile.agent .
# docker build -t agcluster/agent-api:latest -f Dockerfile .
```

**Note:** First build may take 2-3 minutes to download base images and install dependencies.

### 3️⃣ Start AgCluster

```bash
# Start the full stack (API + Agent containers)
docker compose up -d

# Check status
docker compose logs -f
```

🎉 **AgCluster API is now running at `http://localhost:8000`**

### 4️⃣ Test the API

**Health Check:**
```bash
curl http://localhost:8000/health
# Response: {"status":"healthy","agent_image":"agcluster/agent:latest"}
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
# Save the session_id from the launch response
SESSION_ID="conv-abc123..."

curl -X POST http://localhost:8000/api/agents/${SESSION_ID}/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ANTHROPIC_API_KEY" \
  -d '{
    "message": "Hello! Tell me what tools you have access to."
  }'
```

**Streaming Response:**
```bash
curl -X POST http://localhost:8000/api/agents/${SESSION_ID}/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ANTHROPIC_API_KEY" \
  -H "Accept: text/event-stream" \
  -d '{
    "message": "Count to 10"
  }' \
  --no-buffer
```

## 🎯 Agent Configurations

AgCluster provides preset agent configurations optimized for different use cases, plus the ability to create custom configurations.

### Preset Agents

#### 1. 🔧 Code Assistant (`code-assistant`)
**Full-stack development agent with comprehensive tooling**

- **Tools**: Bash, Read, Write, Edit, Grep, Glob, Task, TodoWrite
- **System Prompt**: Claude Code preset with TDD emphasis
- **Resources**: 2 CPUs, 4GB RAM, 10GB storage
- **Use Cases**: Feature implementation, debugging, refactoring, testing

```bash
curl -X POST http://localhost:8000/api/agents/launch \
  -H "Content-Type: application/json" \
  -d '{"api_key": "sk-ant-...","config_id": "code-assistant"}'
```

#### 2. 🔍 Research Agent (`research-agent`)
**Web research and information analysis specialist**

- **Tools**: WebFetch, WebSearch, Read, Write, Grep, TodoWrite
- **Resources**: 1 CPU, 2GB RAM, 5GB storage
- **Use Cases**: Research reports, source verification, information synthesis

```bash
curl -X POST http://localhost:8000/api/agents/launch \
  -H "Content-Type: application/json" \
  -d '{"api_key": "sk-ant-...","config_id": "research-agent"}'
```

#### 3. 📊 Data Analysis Agent (`data-analysis`)
**Statistical analysis and data visualization specialist**

- **Tools**: Bash, Read, Write, Edit, Grep, Glob, NotebookEdit, TodoWrite
- **Focus**: Pandas, numpy, scipy, scikit-learn, matplotlib, seaborn
- **Resources**: 2 CPUs, 6GB RAM, 15GB storage
- **Use Cases**: Exploratory data analysis, statistical testing, Jupyter workflows, machine learning

```bash
curl -X POST http://localhost:8000/api/agents/launch \
  -H "Content-Type: application/json" \
  -d '{"api_key": "sk-ant-...","config_id": "data-analysis"}'
```

#### 4. 👥 Full-Stack Team (`fullstack-team`)
**Multi-agent orchestrator with specialized sub-agents**

- **Main Agent Tools**: Task, Read, Glob, Grep, TodoWrite
- **Sub-agents**:
  - **Frontend**: React, Next.js, Tailwind CSS (Sonnet model)
  - **Backend**: Python, FastAPI, databases (Sonnet model)
  - **DevOps**: Docker, CI/CD, deployment (Haiku model)
- **Resources**: 3 CPUs, 6GB RAM, 10GB storage
- **Use Cases**: Complex features requiring multiple specialists, coordinated team development

```bash
curl -X POST http://localhost:8000/api/agents/launch \
  -H "Content-Type: application/json" \
  -d '{"api_key": "sk-ant-...","config_id": "fullstack-team"}'
```

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

### Configuration Management

```bash
# List all available configurations
curl http://localhost:8000/api/configs/

# Get specific configuration details
curl http://localhost:8000/api/configs/code-assistant

# Response includes tools, resources, prompts, etc.
```

See `configs/README.md` for detailed configuration documentation.

---

## 🌐 Multi-Provider Support

AgCluster supports running agent containers on multiple cloud platforms through a unified provider abstraction layer.

### Supported Providers

- ✅ **Docker** (default) - Local development and self-hosted deployments
- ✅ **Fly Machines** - Production deployments with 300ms boot times
- 🚧 **Cloudflare** - Global edge deployment (planned)
- 🚧 **Vercel** - Serverless sandboxes (planned)

### Quick Start

**Docker (default):**
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
FLY_REGION=iad  # Optional: US East (default)
```

### Provider Comparison

| Provider | Boot Time | Cost (hourly) | Best For |
|----------|-----------|---------------|----------|
| **Docker** | 2-3s | Free (local) | Development, self-hosted |
| **Fly Machines** | 300ms | ~$0.05 | Production, ephemeral workloads |
| **Cloudflare** | <100ms | $5/mo + usage | Global edge, low latency |
| **Vercel** | 1-2s | $20/mo (Pro) | Short tasks, Next.js integration |

### Architecture

**Key Design:**
- AgCluster FastAPI server (control plane) can run anywhere (VPS, cloud VM, serverless)
- Agent containers run on provider of your choice (Docker, Fly, Cloudflare, Vercel)
- Communication via HTTP/SSE (universal compatibility, no WebSocket complexity)

See [PROVIDERS.md](PROVIDERS.md) for complete architecture documentation and [docs/providers/fly_machines.md](docs/providers/fly_machines.md) for Fly.io setup guide.

---

## 🏗️ Architecture

### Claude-Native Platform Architecture

AgCluster Container provides a platform for running Claude Agent SDK instances with visual management:

```
┌──────────────────────────────────────────────────────────────────┐
│                     Web UI Dashboard (Next.js)                   │
│         Real-time tool execution monitoring & file browser       │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             │ HTTP/SSE (API calls)
                             │ Authorization: Bearer ANTHROPIC_API_KEY
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                   AgCluster FastAPI Backend                      │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  KEY FEATURES: Platform Layer                             │  │
│  │  • Session management (config-based launching)            │  │
│  │  • Container lifecycle (create, monitor, cleanup)         │  │
│  │  • File operations (browse, preview, download)            │  │
│  │  • Agent configuration system (presets + custom)          │  │
│  │  • Security (session auth, path validation, CORS)         │  │
│  └────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             │ HTTP/SSE (http://container_ip:3000)
                             │ Provider abstraction (Docker/Fly/etc.)
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│    Isolated Agent Container (Docker/Fly/Cloudflare/Vercel)      │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              Agent Server (HTTP/SSE Server)                │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │        Claude Agent SDK (ClaudeSDKClient)            │  │  │
│  │  │  • Same agent harness powering Claude Code           │  │  │
│  │  │  • Session ID: unique per container                  │  │  │
│  │  │  • Full tool suite: Bash, Read, Write, Grep, MCP    │  │  │
│  │  │  • Working directory: /workspace (isolated)          │  │  │
│  │  │  • Configurable tools per agent type                 │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Security: no-new-privileges, CAP_DROP=ALL, resource limits      │
│  Network: Custom bridge (agcluster-network)                      │
└──────────────────────────────────────────────────────────────────┘
```

### Multi-Session Support

Each session gets an isolated Claude Agent SDK session in its own container:

```
Session 1 → Container A (Claude SDK Session: abc-123, code-assistant)    ┐
Session 2 → Container B (Claude SDK Session: def-456, research-agent)    ├─ All running
Session 3 → Container C (Claude SDK Session: ghi-789, data-analysis)     │  concurrently
...                                                                       │  with 100%
Session N → Container N (Claude SDK Session: xyz-000, fullstack-team)    ┘  isolation
```

**Verified:** 10+ concurrent sessions with unique session IDs and zero interference

## API Reference

### Configuration Endpoints

#### GET /api/configs/
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

#### GET /api/configs/{config_id}
Get detailed configuration for a specific agent.

**Response:**
```json
{
  "id": "code-assistant",
  "name": "Code Assistant",
  "allowed_tools": ["Bash", "Read", "Write", ...],
  "system_prompt": {...},
  "permission_mode": "acceptEdits",
  "resource_limits": {
    "cpu_quota": 200000,
    "memory_limit": "4g"
  }
}
```

### Agent Management Endpoints

#### POST /api/agents/launch
Launch a new agent from configuration.

**Request:**
```json
{
  "api_key": "sk-ant-...",
  "config_id": "code-assistant"  // Or provide inline "config"
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

#### GET /api/agents/sessions
List all active agent sessions.

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "conv-abc123",
      "agent_id": "agent-xyz789",
      "config_id": "code-assistant",
      "status": "running",
      "created_at": "2025-01-15T...",
      "last_active": "2025-01-15T..."
    }
  ],
  "total": 1
}
```

#### GET /api/agents/sessions/{session_id}
Get details about a specific session.

#### DELETE /api/agents/sessions/{session_id}
Stop and remove a session.

### Chat Endpoint

#### POST /api/agents/{session_id}/chat
Send messages to an active agent session.

**Path Parameters:**
- `session_id`: Session ID returned from `/api/agents/launch`

**Headers:**
- `Authorization: Bearer YOUR_ANTHROPIC_API_KEY`
- `Content-Type: application/json`
- `Accept: text/event-stream` (for streaming responses)

**Request Body:**
```json
{
  "message": "Your message here"
}
```

**Response:**
- **Streaming** (when `Accept: text/event-stream`): Server-Sent Events with real-time tool execution updates
- **Non-streaming**: Complete response with final text and tool results

**Example SSE Stream:**
```
data: {"type":"text","content":"Let me help you with that..."}
data: {"type":"tool_use","tool":"Bash","input":"ls -la"}
data: {"type":"tool_result","output":"total 48\ndrwxr-xr-x..."}
data: {"type":"text","content":"I found 5 files in the directory."}
data: [DONE]
```

### Utility Endpoints

#### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "agent_image": "agcluster/agent:latest"
}
```

## Configuration

### Environment Variables

Edit `.env` to configure default settings:

```bash
# API Settings
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=true

# Agent Image
AGENT_IMAGE=agcluster/agent:latest

# Default Container Resources (used when no config specified)
CONTAINER_CPU_QUOTA=200000  # 2 CPUs
CONTAINER_MEMORY_LIMIT=4g
CONTAINER_STORAGE_LIMIT=10g

# Default Agent Settings
DEFAULT_SYSTEM_PROMPT="You are a helpful AI assistant."
DEFAULT_ALLOWED_TOOLS=Bash,Read,Write,Grep
DEFAULT_PERMISSION_MODE=acceptEdits
DEFAULT_MAX_TURNS=100

# Session Management
SESSION_CLEANUP_INTERVAL=300      # Check every 5 minutes
SESSION_IDLE_TIMEOUT=1800         # 30 minutes idle timeout
```

### Agent Configuration Files

Agent configurations are stored in `configs/presets/` as YAML files. Each configuration defines:

- **Tools**: Which tools the agent can access
- **System Prompt**: Instructions and specialization
- **Resource Limits**: CPU, memory, storage constraints
- **Sub-agents**: For multi-agent orchestration (optional)
- **MCP Servers**: Custom tool servers (optional)

**Example configuration structure:**
```yaml
id: my-agent
name: My Custom Agent
description: Brief description
version: 1.0.0

system_prompt: |
  You are a specialist in...

allowed_tools:
  - Bash
  - Read
  - Write
  - TodoWrite

permission_mode: acceptEdits

resource_limits:
  cpu_quota: 200000      # 2 CPUs (100000 = 1 CPU)
  memory_limit: 4g       # 4GB RAM
  storage_limit: 10g     # 10GB disk

max_turns: 100
```

See `configs/README.md` for complete configuration documentation and examples.

## 📊 Performance

### Benchmarks

| Metric | Value |
|--------|-------|
| **Container Startup** | <3 seconds (adaptive) |
| **First Response** | 5-10 seconds |
| **Concurrent Sessions** | 10+ verified |
| **Response Time (single)** | 5-8 seconds |
| **Response Time (10 concurrent)** | 10-15 seconds each |

### Tested Scenarios

✅ **3 concurrent requests** - 100% success
✅ **5 concurrent requests** - 100% success
✅ **10 concurrent requests** - 100% success
✅ **Streaming & non-streaming** - Both work perfectly
✅ **Tool execution** - All tools functional
✅ **Session isolation** - Verified with unique session IDs

---

## 📚 Documentation

### Core Documentation
- **[Agent Configuration](configs/README.md)** - Complete configuration reference for presets and custom agents
- **[Multi-Provider Setup](PROVIDERS.md)** - Deploy on Docker, Fly.io, Cloudflare, Vercel
- **[Security Audit Report](SECURITY_AUDIT_REPORT.md)** - Security features and best practices
- **[Web UI Guide](src/agcluster/container/ui/README.md)** - Next.js dashboard setup and features

---

## 🛠️ Development

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
# Build agent image (Claude SDK container)
docker build -t agcluster/agent:latest -f docker/Dockerfile.agent .

# Build API image
docker build -t agcluster/agent-api:latest -f Dockerfile .

# Or build both with docker compose
docker compose build
```

### Run Tests

```bash
# Install package in development mode first
pip install -e ".[dev]"

# Run all tests
pytest tests/

# Run with coverage report
pytest --cov=agcluster.container tests/

# Run specific test categories
pytest tests/unit/                    # Unit tests
pytest tests/integration/             # Integration tests

# Test by component
pytest tests/unit/test_translator.py          # Message translation
pytest tests/unit/test_container_manager.py   # Container lifecycle
pytest tests/unit/test_session_manager.py     # Session management
pytest tests/unit/test_config_loader.py       # Configuration loading
pytest tests/unit/test_agent_config.py        # Agent config models
pytest tests/integration/test_api_endpoints.py # API endpoints
pytest tests/integration/test_config_api.py    # Config endpoints

# E2E tests (require Docker, marked as skipped by default)
pytest tests/e2e/ --run-skipped
```

**Test Coverage:**
- ✅ **Unit Tests** - Core components (translator, containers, sessions, configs, providers)
- ✅ **Integration Tests** - API endpoints, validation, config management
- ✅ **E2E Tests** - End-to-end workflows requiring Docker

**Test Areas:**
- Provider abstraction layer (Docker and Fly Machines)
- Container lifecycle management
- Session management with auto-cleanup
- Configuration loading and validation
- API endpoint functionality

### Monitoring & Troubleshooting

**View logs:**
```bash
# View all logs (API + agent containers)
docker compose logs -f

# View only API logs
docker compose logs -f api

# View specific agent container logs
docker logs <container-id>

# View logs with timestamps
docker compose logs -f --timestamps

# View last 100 lines
docker compose logs --tail 100
```

**Check running containers:**
```bash
# View AgCluster API and agent containers
docker ps | grep agcluster

# View all containers (including stopped)
docker ps -a | grep agcluster
```

**Monitor session activity:**
```bash
# Watch logs for session creation/reuse
docker compose logs -f api | grep -i session

# View container creation events
docker compose logs -f api | grep "Creating new session"

# View session reuse events
docker compose logs -f api | grep "Reusing existing session"
```

**Debugging tips:**
- Session management logs show when containers are created/reused
- Each agent container has unique ID visible in logs
- WebSocket connection issues appear in API logs
- Claude SDK errors appear in agent container logs

### Namespace Package Structure

This project uses **PEP 420 namespace packages** under the `agcluster` namespace:

```
src/
└── agcluster/             # Namespace (no __init__.py)
    └── container/        # This package
        ├── __init__.py
        ├── api/          # FastAPI endpoints
        ├── core/         # Core logic
        └── models/       # Pydantic models
```

**Benefits:**
- Other AgCluster projects (cli, dashboard) share the `agcluster.*` namespace
- Clean imports: `from agcluster.container import X`
- No package name conflicts
- Ecosystem-ready architecture

**Future repos:**
- `agcluster-cli` → `from agcluster.cli import Y`
- `agcluster-dashboard` → `from agcluster.dashboard import Z`

## 💡 Use Cases

### 1. **Self-Hosted Developer Platform**
Claude SDK platform with visual management:
- Visual dashboard for real-time tool execution monitoring
- File browser to inspect agent-created artifacts
- Task tracking with intelligent status summaries
- Resource monitoring and session management
- Perfect for teams wanting full control over agent infrastructure

### 2. **Custom Cloud Infrastructure**
Foundation for building custom agent orchestration platforms:
- Multi-tenant agent hosting with Docker/Fly.io/Cloudflare
- REST API gateway for Claude Agent SDK
- Session management and isolation
- Scale horizontally with container orchestration
- Bring-your-own-key billing model

### 3. **Code Review & Analysis Agents**
Deploy specialized agents for development workflows:
- Automated PR reviews with file access
- Security vulnerability scanning with tool execution
- Style guide enforcement across codebases
- Documentation generation from code analysis
- Use `code-assistant` preset for full development capabilities

### 4. **Data Science & Analytics Agents**
Python-capable agents for data tasks:
- Jupyter-style exploration with pandas/numpy (NotebookEdit tool)
- Statistical analysis with tool execution
- Data visualization and reporting
- Interactive data debugging
- Use `data-analysis` preset for optimized data workflows

### 5. **Research & Intelligence Gathering**
Web-enabled agents for information synthesis:
- Multi-source research with WebSearch and WebFetch
- Source verification and fact-checking
- Competitive intelligence gathering
- Market research automation
- Use `research-agent` preset for web-focused workflows

---

## 🗺️ Roadmap

### ✅ Completed (v1.0)
- [x] Integrated Web UI Dashboard (Next.js 15 with real-time monitoring)
- [x] Claude-native REST API with SSE streaming
- [x] Session management (persistent containers per session)
- [x] Multi-container concurrent sessions (10+ verified)
- [x] Claude Agent SDK integration with session persistence
- [x] HTTP/SSE communication for real-time streaming
- [x] Auto-cleanup of idle sessions (30-min timeout)
- [x] Security hardening (path traversal protection, session auth, CORS whitelist, zip bomb protection)
- [x] Agent configuration system with 4 preset configs
- [x] Config-based launching via /api/agents/launch
- [x] Custom agent creation with inline configs
- [x] Multi-agent orchestration (fullstack-team preset)
- [x] Jupyter notebook support (data-analysis preset with NotebookEdit)
- [x] Task tracking for all presets (TodoWrite tool)
- [x] File operations API (browse, preview, download workspace)
- [x] Multi-provider support (Docker, Fly Machines)
- [x] Comprehensive test suite with unit, integration, and E2E tests
- [x] Production-ready robustness

### 🔮 Future Enhancements
- [ ] Multi-modal input support (images, files, PDFs)
- [ ] File attachment handling for document analysis
- [ ] Additional agent presets (security-auditor, content-writer, etc.)
- [ ] Multi-user authentication and authorization
- [ ] Usage metering and quotas
- [ ] Web dashboard UI for management
- [ ] Monitoring and metrics (Prometheus/Grafana)
- [ ] Kubernetes deployment guide
- [ ] Agent marketplace and sharing
- [ ] Conversation export and history persistence

---

## 🔧 Troubleshooting

### Container won't start
```bash
# Check Docker is running
docker ps

# Check logs
docker compose logs api

# Rebuild images
docker compose build --no-cache
```

### "Connection refused" errors
**Fixed in v1.0!** If you still see this:
- Make sure you're on the latest version
- Check container logs: `docker logs <container-name>`
- Verify network connectivity: `docker network inspect agcluster-container_agcluster-network`

### API responds with 500 errors
```bash
# Check API logs
docker compose logs api

# Check agent container logs
docker ps --filter "label=agcluster=true"
docker logs <container-id>

# Verify Anthropic API key is valid
curl -X POST http://localhost:8000/health
```

### Tests failing
```bash
# Ensure virtual environment is activated (if using one)
source venv/bin/activate  # or: conda activate <your-env>

# Reinstall dependencies
pip install -e ".[dev]"

# Run tests with verbose output
pytest tests/ -v
```

### High memory usage
```bash
# Check running containers
docker ps --filter "label=agcluster=true"

# Clean up stopped containers
docker ps -a --filter "label=agcluster=true" --filter "status=exited" | xargs docker rm

# Restart API to clear state
docker compose restart api
```

Need more help? [Open an issue](https://github.com/whiteboardmonk/agcluster-container/issues)

## Security Considerations

- Containers run with minimal privileges (no-new-privileges, dropped capabilities)
- Read-only root filesystem
- Network isolation
- Resource limits enforced
- User API keys never stored on server

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

## License

MIT License - see [LICENSE](LICENSE)

## 🌐 AgCluster Ecosystem Vision

AgCluster Container is the **foundational platform layer** in the AgCluster ecosystem for building custom cloud infrastructure with Claude Agent SDK at its core.

### Current (v1.0) - v1.0 Released

✅ **agcluster-container** - Claude SDK platform with visual management *(this project)*
- Integrated Web UI Dashboard (Next.js 15) with real-time monitoring
- Claude-native REST API with full SDK capabilities
- Multi-tenant session isolation with config-based launching
- 4 preset agent configurations + custom inline configs
- File operations API for workspace management
- Multi-provider support (Docker, Fly Machines)
- 10+ concurrent sessions verified
- Comprehensive test coverage

### In Development

🚧 **Container pooling** - Session persistence and reuse across requests
🚧 **Multi-user auth** - Authentication layer with user quotas
🚧 **Monitoring & observability** - Prometheus metrics, Grafana dashboards
🚧 **Rate limiting** - Per-user/per-key request throttling

### Roadmap - Building the Ecosystem

📋 **agcluster-cli** - CLI for agent management
- Create, list, stop agents from terminal
- Stream logs and debug sessions
- Deploy agent templates

📋 **agcluster-dashboard** - Web UI for monitoring
- Real-time agent monitoring
- Usage analytics and billing
- Agent template marketplace

📋 **agcluster-registry** - MCP server marketplace
- Custom tool registry
- Community-contributed MCP servers
- Agent workflow templates

📋 **agcluster-orchestrator** - Multi-agent coordination
- Agent-to-agent communication
- Workflow orchestration
- Distributed agent clusters

### The Vision: Custom Cloud for Claude Agent SDK

Build custom cloud infrastructure for deploying, managing, and scaling Claude Agent SDK agents:

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Custom Cloud                        │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Dashboard   │  │     CLI      │  │   Registry   │     │
│  │   (Web UI)   │  │  (Terminal)  │  │  (MCP/Tools) │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         └──────────────────┴─────────────────┘             │
│                           │                                 │
│         ┌─────────────────▼─────────────────┐              │
│         │   AgCluster Container (Platform)   │              │
│         │  • Integrated Web UI Dashboard    │              │
│         │  • Claude-native REST API         │              │
│         │  • Multi-tenant isolation         │              │
│         │  • Session management             │              │
│         │  • File operations & monitoring   │              │
│         └─────────────────┬─────────────────┘              │
│                           │                                 │
│         ┌─────────────────▼─────────────────┐              │
│         │    Claude Agent SDK Instances     │              │
│         │  • Containerized agents           │              │
│         │  • Tool execution                 │              │
│         │  • MCP extensibility              │              │
│         │  • Multi-provider deployment      │              │
│         └───────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

**Target Use Cases:**
- Enterprise agent hosting platforms
- AI-powered SaaS products
- Developer tool companies
- Research institutions
- Custom agent workflows
- Self-hosted development environments

### Related Open Source Projects

- [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python) - The agent runtime powering AgCluster

## Support

- GitHub Issues: [Report bugs](https://github.com/whiteboardmonk/agcluster-container/issues)
- Discussions: [Ask questions](https://github.com/whiteboardmonk/agcluster-container/discussions)
- Discord: [Join community](#) (coming soon)

---

**Built with ❤️ by the AgCluster team**
