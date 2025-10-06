# AgCluster Container

<div align="center">

> 🚀 **OpenAI-compatible API for Claude Agent SDK**

[![Tests](https://img.shields.io/badge/tests-76%20passing-brightgreen)]()
[![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen)]()
[![Docker](https://img.shields.io/badge/docker-required-blue)]()
[![Python](https://img.shields.io/badge/python-3.11+-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

[Why AgCluster?](#why-agcluster-container) • [Features](#features) • [Quick Start](#quick-start) • [Session Management](#session-management) • [Architecture](#architecture) • [Documentation](#documentation)

</div>

---

## 📖 Overview

**AgCluster Container** is an OpenAI-compatible API wrapper for [Claude Agent SDK](https://docs.claude.com/en/api/agent-sdk/overview), enabling you to use Claude's powerful agent capabilities through a familiar `/chat/completions` endpoint that works with LibreChat and any OpenAI client.

**🎯 Core Value**: Access Claude Agent SDK (the same agent harness powering Claude Code) through standard OpenAI API format—no SDK knowledge required. Each session runs in isolated Docker containers for security and multi-tenancy.

**🌟 Part of AgCluster Ecosystem**: A critical OSS component in the AgCluster ecosystem for building custom cloud infrastructure with Claude Agent SDK at its core.

### ✅ Production Ready

- ✅ **90% Test Coverage** - 76 tests passing (9 E2E tests skipped - require Docker)
- ✅ **Conversation-Based Sessions** - Persistent containers per conversation thread
- ✅ **Context Preservation** - Full conversation context maintained across messages
- ✅ **Auto-Cleanup** - Background task removes idle sessions (30-min timeout)
- ✅ **Robustness Verified** - Handles 10+ concurrent conversations
- ✅ **Battle Tested** - E2E tested with real Anthropic API keys and LibreChat

---

## 🤔 Why AgCluster Container?

**Claude Agent SDK is powerful but Python/TypeScript-specific.** AgCluster Container makes it universally accessible:

- ✅ Use with **any OpenAI client** (LibreChat, Open WebUI, custom apps)
- ✅ **No SDK knowledge required** - just send OpenAI-formatted requests
- ✅ **Full Claude Agent SDK capabilities** - Bash, file operations, web search, MCP tools
- ✅ **BYOK architecture** - users bring their own Anthropic API keys (never stored)
- ✅ **Multi-tenant ready** - isolated containers per session for security
- ✅ **Part of AgCluster ecosystem** - foundation for building custom cloud infrastructure

**What you get**: The same powerful agent capabilities that power Claude Code, accessible through a familiar OpenAI API.

---

## ✨ Features

### Core Capabilities

- 🔌 **OpenAI-Compatible API** - Standard `/chat/completions` endpoint, drop-in replacement for OpenAI API
- 🤖 **Claude Agent SDK Access** - Full agent capabilities (same harness powering Claude Code) via API
- 🛠️ **Complete Tool Suite** - Bash, Read, Write, Grep, Task, WebFetch, WebSearch, MCP extensibility
- 🎨 **LibreChat Ready** - Works out-of-the-box with LibreChat, Open WebUI, and any OpenAI client
- 🔐 **BYOK (Bring Your Own Key)** - Users provide their own Anthropic API keys (never stored)
- 📡 **OpenAI Streaming Support** - Real-time SSE streaming responses in OpenAI format (both streaming and non-streaming modes)
- 🐳 **Multi-Session Isolation** - Run 10+ concurrent sessions with full container isolation
- 🔒 **Security Hardened** - Minimal privileges, dropped capabilities, network isolation, resource limits

### Session Management

- 💬 **Conversation-Based Containers** - One persistent container per conversation thread
- 🔄 **Context Preservation** - Same Claude SDK session reused across all messages
- 🧹 **Auto-Cleanup** - Background task removes idle sessions after 30 minutes
- 📝 **Conversation ID Tracking** - LibreChat `X-Conversation-ID` header support
- ⚙️ **Resource Efficiency** - One container per active conversation, not per message

### Technical Features

- ⚡ **Adaptive Readiness Detection** - WebSocket-based container health checks for 100% reliability
- 🎯 **Session Isolation** - Each container maintains independent Claude SDK session with unique ID
- 🌐 **Custom Networking** - Bridge network isolation for security
- 📊 **Test-Driven Development** - Comprehensive test suite (76 passing tests + 9 E2E tests) with 90% code coverage
- 🚀 **Lazy Initialization** - Docker client lazy-loads for better development experience
- 🔄 **WebSocket Communication** - Bidirectional real-time communication between API and agents

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

**Send a Message:**
```bash
curl -X POST http://localhost:8000/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ANTHROPIC_API_KEY" \
  -d '{
    "model": "claude-sonnet-4.5",
    "messages": [{"role": "user", "content": "Hello! Tell me what tools you have access to."}],
    "stream": false
  }'
```

**Streaming Response:**
```bash
curl -X POST http://localhost:8000/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ANTHROPIC_API_KEY" \
  -d '{
    "model": "claude-sonnet-4.5",
    "messages": [{"role": "user", "content": "Count to 10"}],
    "stream": true
  }' \
  --no-buffer
```

### 5️⃣ Use with LibreChat

See [LibreChat Integration Guide](librechat/README.md) for detailed setup instructions.

**Quick LibreChat config:**
```yaml
endpoints:
  custom:
    - name: "AgCluster"
      apiKey: "user_provided"
      baseURL: "http://localhost:8000"
      models:
        default: ["claude-sonnet-4.5"]
```

## 🏗️ Architecture

### The API Wrapper Pattern

AgCluster Container bridges **any OpenAI client** with **Claude Agent SDK** through a translation layer:

```
┌──────────────────────────────────────────────────────────────────┐
│          LibreChat / OpenAI Client / Any Chat UI                 │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             │ POST /chat/completions (OpenAI format)
                             │ Authorization: Bearer ANTHROPIC_API_KEY
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│              AgCluster API - OpenAI → Claude Translation          │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  KEY INNOVATION: API Wrapper Layer                        │  │
│  │  • Translate OpenAI format → Claude Agent SDK messages    │  │
│  │  • Translate Claude responses → OpenAI SSE format         │  │
│  │  • Container lifecycle: create, connect, stream, cleanup  │  │
│  │  • Multi-tenant session management                        │  │
│  └────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             │ WebSocket (ws://container_ip:8765)
                             │ Bidirectional communication
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│    Isolated Docker Container (security & multi-tenancy)          │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              Agent Server (WebSocket Server)               │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │        Claude Agent SDK (ClaudeSDKClient)            │  │  │
│  │  │  • Same agent harness powering Claude Code           │  │  │
│  │  │  • Session ID: unique per container                  │  │  │
│  │  │  • Full tool suite: Bash, Read, Write, Grep, MCP    │  │  │
│  │  │  • Working directory: /workspace (isolated)          │  │  │
│  │  │  • Automatic context management                      │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Security: no-new-privileges, CAP_DROP=ALL, 2 CPU, 4GB RAM     │
│  Network: Custom bridge (agcluster-network)                      │
└──────────────────────────────────────────────────────────────────┘
```

### Multi-Session Support

Each request creates an isolated Claude Agent SDK session in its own container:

```
OpenAI Client Request 1 → Container A (Claude SDK Session: abc-123) ┐
OpenAI Client Request 2 → Container B (Claude SDK Session: def-456) ├─ All running
OpenAI Client Request 3 → Container C (Claude SDK Session: ghi-789) │  concurrently
...                                                                  │  with 100%
OpenAI Client Request 10 → Container J (Claude SDK Session: xyz-000) ┘  isolation
```

**Verified:** 10+ concurrent sessions with unique session IDs and zero interference

## API Reference

### POST /chat/completions

OpenAI-compatible chat completions endpoint.

**Headers:**
- `Authorization: Bearer YOUR_ANTHROPIC_API_KEY`
- `Content-Type: application/json`

**Request Body:**
```json
{
  "model": "claude-sonnet-4.5",
  "messages": [
    {"role": "user", "content": "Your message here"}
  ],
  "stream": true
}
```

**Response:**
- Streaming (SSE): Real-time text chunks in OpenAI format
- Non-streaming: Complete response in OpenAI format

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "agent_image": "agcluster/agent:latest"
}
```

## Configuration

Edit `.env` to configure:

```bash
# API Settings
API_HOST=0.0.0.0
API_PORT=8000

# Container Resources
CONTAINER_CPU_QUOTA=200000  # 2 CPUs
CONTAINER_MEMORY_LIMIT=4g

# Agent Defaults
DEFAULT_SYSTEM_PROMPT="You are a helpful AI assistant."
DEFAULT_ALLOWED_TOOLS=Bash,Read,Write,Grep
```

## 📊 Performance

### Benchmarks

| Metric | Value |
|--------|-------|
| **Container Startup** | <3 seconds (adaptive) |
| **First Response** | 5-10 seconds |
| **Concurrent Sessions** | 10+ verified (100% success) |
| **Response Time (single)** | 5-8 seconds |
| **Response Time (10 concurrent)** | 10-15 seconds each |
| **Test Success Rate** | 100% (76/76 passing) |

### Tested Scenarios

✅ **3 concurrent requests** - 100% success
✅ **5 concurrent requests** - 100% success
✅ **10 concurrent requests** - 100% success
✅ **Streaming & non-streaming** - Both work perfectly
✅ **Tool execution** - All tools functional
✅ **Session isolation** - Verified with unique session IDs

---

## 📚 Documentation

### Getting Started
- **[Quick Start Guide](docs/quickstart.md)** - Get up and running in 5 minutes
- **[Architecture Guide](docs/architecture.md)** - Detailed system architecture and design

### Examples & Integrations
- **[LibreChat Integration](examples/librechat/README.md)** - Step-by-step LibreChat setup with session persistence
- More examples coming soon (Open WebUI, custom clients, etc.)

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

# Run all tests (76 passing)
pytest tests/

# Run with coverage (90% coverage)
pytest --cov=agcluster.container tests/

# Run specific test categories
pytest tests/unit/                    # 63 unit tests
pytest tests/integration/             # 13 integration tests

# E2E/Robustness tests (9 tests - require Docker, marked as skipped by default)
# To run manually, remove skip marker from tests/robustness/test_concurrent_sessions.py
pytest tests/robustness/ --run-skipped
```

**Test Summary:**
- ✅ **63 Unit Tests** - Testing core components (translator, container manager, session manager)
- ✅ **13 Integration Tests** - Testing API endpoints and request validation
- ⏭️ **9 Robustness Tests** - E2E tests requiring Docker (skipped by default, run manually for full validation)

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

### 1. **Add Claude Agent SDK to Existing OpenAI Workflows**
Seamlessly integrate Claude Agent SDK into apps already using OpenAI:
- Replace OpenAI endpoint with AgCluster Container
- Get full tool execution capabilities (Bash, file ops, web search)
- No code changes required—just change the base URL
- Same request/response format, enhanced agent capabilities

### 2. **LibreChat with Claude Agent Capabilities**
Give LibreChat users access to Claude Agent SDK through familiar UI:
- Chat interface with code execution
- File operations in isolated workspaces
- Web search and data analysis
- Streaming responses with tool visibility

### 3. **Custom Cloud Infrastructure**
Foundation for building custom agent orchestration platforms:
- Multi-tenant agent hosting
- API gateway for Claude Agent SDK
- Session management and isolation
- Scale horizontally with container orchestration

### 4. **Code Review & Analysis Agents**
Deploy specialized agents for development workflows:
- Automated PR reviews with file access
- Security vulnerability scanning with tool execution
- Style guide enforcement across codebases
- Documentation generation from code analysis

### 5. **Data Science & Analytics Agents**
Python-capable agents for data tasks:
- Jupyter-style exploration with pandas/numpy
- Statistical analysis with tool execution
- Data visualization and reporting
- Interactive data debugging

---

## 🗺️ Roadmap

### ✅ Completed (v1.0)
- [x] OpenAI-compatible API with streaming and non-streaming support
- [x] Conversation-based session management (persistent containers per conversation)
- [x] Multi-container concurrent sessions (10+ verified)
- [x] Claude Agent SDK integration with session persistence
- [x] WebSocket communication for real-time streaming
- [x] Auto-cleanup of idle sessions (30-min timeout)
- [x] Security hardening (dropped capabilities, resource limits)
- [x] Comprehensive test suite (76 tests passing, 90% coverage)
- [x] Production-ready robustness

### 🔮 Future Enhancements
- [ ] Multi-modal input support (images, files, PDFs)
- [ ] File attachment handling for document analysis
- [ ] Custom agent templates and configurations
- [ ] Multi-user authentication and authorization
- [ ] Usage metering and quotas
- [ ] Web dashboard UI for management
- [ ] Monitoring and metrics (Prometheus/Grafana)
- [ ] Kubernetes deployment guide
- [ ] Custom MCP server integration
- [ ] Agent marketplace and sharing

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

AgCluster Container is the **foundational API layer** in the AgCluster ecosystem for building custom cloud infrastructure with Claude Agent SDK at its core.

### Current (v1.0) - Production Ready

✅ **agcluster-container** - OpenAI-compatible API wrapper for Claude Agent SDK *(this project)*
- Drop-in replacement for OpenAI API endpoints
- Multi-tenant session isolation
- 10+ concurrent sessions verified
- 76/76 tests passing, 90% coverage

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

Build complete custom cloud infrastructure for deploying, managing, and scaling Claude Agent SDK applications:

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
│         │   AgCluster Container (API Layer)  │              │
│         │  • OpenAI-compatible endpoints    │              │
│         │  • Multi-tenant isolation         │              │
│         │  • Session management             │              │
│         └─────────────────┬─────────────────┘              │
│                           │                                 │
│         ┌─────────────────▼─────────────────┐              │
│         │    Claude Agent SDK Instances     │              │
│         │  • Containerized agents           │              │
│         │  • Tool execution                 │              │
│         │  • MCP extensibility              │              │
│         └───────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

**Target Use Cases:**
- Enterprise agent hosting platforms
- AI-powered SaaS products
- Developer tool companies
- Research institutions
- Custom agent workflows

### Related Open Source Projects

- [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python) - The agent runtime we wrap
- [LibreChat](https://github.com/danny-avila/LibreChat) - Recommended chat UI for AgCluster

## Support

- GitHub Issues: [Report bugs](https://github.com/whiteboardmonk/agcluster-container/issues)
- Discussions: [Ask questions](https://github.com/whiteboardmonk/agcluster-container/discussions)
- Discord: [Join community](#) (coming soon)

---

**Built with ❤️ by the AgCluster team**
