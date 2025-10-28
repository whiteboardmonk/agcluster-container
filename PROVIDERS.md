# AgCluster Multi-Provider Architecture

AgCluster supports running Claude Agent SDK containers across multiple platforms through a unified provider abstraction layer. This document details the architecture, supported providers, and implementation status.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Communication Protocol](#communication-protocol)
- [Supported Providers](#supported-providers)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Provider Comparison](#provider-comparison)
- [Implementation Roadmap](#implementation-roadmap)
- [Adding New Providers](#adding-new-providers)

---

## Architecture Overview

AgCluster uses a **two-component architecture**:

### 1. AgCluster FastAPI Server (Control Plane)
**What it does:**
- Receives HTTP requests from Web UI and API clients
- Manages session lifecycle and routing
- Orchestrates container creation across platforms
- Streams Claude SDK responses via SSE

**Where it runs:**
- Development: Local machine (`localhost:8000`)
- Production: Your choice of:
  - Self-hosted VPS (DigitalOcean, Linode, Hetzner)
  - Cloud VMs (AWS EC2, Google Compute, Azure)
  - Container platforms (Fly.io, Railway, Render)
  - Serverless (AWS Lambda, Modal)

### 2. Agent Containers (Execution Environments)
**What they do:**
- Run Claude Agent SDK with configurable tools
- Execute user queries in isolated environments
- Stream responses back to API via HTTP/SSE

**Where they run:**
- Controlled by `CONTAINER_PROVIDER` setting
- Options: Docker (local), Fly Machines, Cloudflare, Vercel

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│               Web UI / API Clients                       │
│          (Browser UI + HTTP API clients)                 │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTPS/SSE
                        ▼
┌─────────────────────────────────────────────────────────┐
│          AgCluster FastAPI Server (YOU HOST THIS)       │
│                                                          │
│  • Receives API requests (agents, chat, files)           │
│  • Creates agent containers on selected platform         │
│  • Manages sessions and routing                          │
│  • Streams responses back to client                      │
└───────────────────────┬─────────────────────────────────┘
                        │
            ┌───────────┴───────────┐
            │  Provider Selection    │
            │  (via CONTAINER_PROVIDER)│
            └───────────┬───────────┘
                        │
        ┌───────────────┼───────────────┬──────────────┐
        │               │               │              │
        ▼               ▼               ▼              ▼
┌──────────────┐ ┌─────────────┐ ┌────────────┐ ┌──────────────┐
│   Docker     │ │  Fly.io     │ │ Cloudflare │ │   Vercel     │
│   (Local)    │ │  Machines   │ │ Containers │ │   Sandbox    │
└──────────────┘ └─────────────┘ └────────────┘ └──────────────┘
      │                 │               │              │
      ▼                 ▼               ▼              ▼
┌──────────────┐ ┌─────────────┐ ┌────────────┐ ┌──────────────┐
│Agent         │ │Agent        │ │Agent       │ │Agent         │
│Container     │ │Container    │ │Container   │ │Container     │
│(local)       │ │(Fly infra)  │ │(CF edge)   │ │(Vercel edge) │
│Claude SDK    │ │Claude SDK   │ │Claude SDK  │ │Claude SDK    │
│+ Tools       │ │+ Tools      │ │+ Tools     │ │+ Tools       │
└──────────────┘ └─────────────┘ └────────────┘ └──────────────┘
```

---

## Communication Protocol

### Why HTTP/SSE?

AgCluster uses **HTTP POST + Server-Sent Events (SSE)** for all provider communication:

**Advantages:**
- ✅ **Universal Compatibility**: Works on all platforms (Docker, Fly, Cloudflare, Vercel)
- ✅ **Simpler Infrastructure**: Standard HTTP, no WebSocket complexity
- ✅ **Better Debugging**: HTTP logs, status codes, standard tooling
- ✅ **Platform Agnostic**: Cloudflare Workers and Vercel Sandboxes don't support WebSocket servers
- ✅ **Built-in Backpressure**: HTTP/2 flow control

**Trade-off:**
- ~5-10ms higher latency vs WebSocket (negligible compared to Claude API: 200-500ms)

### Protocol Flow

```
Client → AgCluster API → Provider
                ↓
        POST /query (HTTP)
                ↓
        Agent Container
                ↓
        SSE Stream ←──────────
        ↓
data: {"type": "thinking", "content": "..."}
data: {"type": "tool", "name": "Bash", "input": {...}}
data: {"type": "message", "content": "..."}
data: {"type": "complete", "status": "success"}
```

### Compatibility with Claude SDK Features

| Feature | HTTP/SSE Support | Notes |
|---------|------------------|-------|
| Tool Execution | ✅ Full | Tools run in container, results streamed via SSE |
| MCP Servers | ✅ Full | MCP uses stdio/HTTP, not WebSocket-dependent |
| SDK Hooks | ✅ Full | In-process callbacks, transport-agnostic |
| Session Persistence | ✅ Full | SDK session maintained in container memory |
| Streaming Output | ✅ Full | SSE designed for server→client streaming |
| Multi-turn Conversations | ✅ Full | Container persists between requests |
| User Cancellation | ✅ Full | Detected via connection close |

---

## Supported Providers

### 1. Docker (Local) ✅ Implemented

**Status:** Production-ready (default provider)

**Use Case:** Development, testing, self-hosted deployments

**Requirements:**
- Docker daemon running locally
- Docker SDK for Python (`pip install docker`)

**Configuration:**
```bash
# .env
CONTAINER_PROVIDER=docker
```

**Pros:**
- Free (local compute)
- Full control over environment
- Fast iteration for development
- No external dependencies

**Cons:**
- Requires Docker daemon
- Limited to single machine
- Manual scaling

**Cost:** Free (local compute resources)

---

### 2. Fly Machines 🚧 Planned (Week 2)

**Status:** Implementation in progress

**Use Case:** Production deployments, ephemeral workloads, fast boot times

**Requirements:**
- Fly.io account (free tier available)
- Fly API token
- Fly app created (`fly apps create agcluster-agents`)

**Configuration:**
```bash
# .env
CONTAINER_PROVIDER=fly_machines
FLY_API_TOKEN=your_token_here
FLY_APP_NAME=agcluster-agents
FLY_REGION=iad  # Optional: US East (default)
```

**Pros:**
- 300ms boot time (very fast)
- Pay-per-use pricing
- Global deployment options
- IPv6 private networking
- Can run persistent or ephemeral

**Cons:**
- Requires internet connection
- Costs money (though minimal)
- Platform-specific limitations

**Cost:** $0.0000008/second/MB RAM (~$0.05/hour for 1GB container)

**Setup Guide:** See `docs/providers/fly-machines.md`

---

### 3. Cloudflare Containers 🚧 Planned (Week 3)

**Status:** Implementation in progress

**Use Case:** Global edge deployment, low-latency worldwide

**Requirements:**
- Cloudflare account with Containers beta access
- Cloudflare API token
- Durable Objects enabled

**Configuration:**
```bash
# .env
CONTAINER_PROVIDER=cloudflare
CLOUDFLARE_API_TOKEN=your_token
CLOUDFLARE_ACCOUNT_ID=your_account_id
```

**Pros:**
- Global edge network (low latency worldwide)
- Durable Objects for state management
- Built-in DDoS protection
- Automatic scaling

**Cons:**
- Beta access required (as of 2025)
- Requires rewriting agent to JS (or using Python→JS bridge)
- Workers have 30-second CPU limit
- More complex deployment

**Cost:** Workers Paid plan ($5/month) + usage ($0.50/million requests)

**Setup Guide:** See `docs/providers/cloudflare.md`

---

### 4. Vercel Sandbox 🚧 Planned (Week 4)

**Status:** Implementation in progress

**Use Case:** Short-lived tasks, Next.js integration

**Requirements:**
- Vercel Pro account ($20/month)
- Vercel API token
- Vercel project created

**Configuration:**
```bash
# .env
CONTAINER_PROVIDER=vercel
VERCEL_TOKEN=your_token
VERCEL_PROJECT_ID=your_project_id
VERCEL_TEAM_ID=your_team_id  # Optional
```

**Pros:**
- Firecracker MicroVM isolation (secure)
- Amazon Linux 2023 base
- Integrates with Next.js ecosystem
- Fast cold starts (1-2s)

**Cons:**
- **5-hour maximum runtime** (Pro plan)
- Requires Vercel Pro subscription
- Best for short tasks only
- Auto-cleanup after timeout

**Cost:** Included in Vercel Pro plan ($20/month)

**Setup Guide:** See `docs/providers/vercel.md`

---

## Configuration

### Environment Variables

**Global Settings:**
```bash
# Provider selection (default: docker)
CONTAINER_PROVIDER=docker

# API Server (where FastAPI runs)
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false
```

**Docker Provider:**
```bash
AGENT_IMAGE=agcluster/agent:latest
CONTAINER_CPU_QUOTA=200000  # 2 CPUs (100000 = 1 CPU)
CONTAINER_MEMORY_LIMIT=4g
CONTAINER_STORAGE_LIMIT=10g
```

**Fly Machines Provider:**
```bash
FLY_API_TOKEN=your_token
FLY_APP_NAME=agcluster-agents
FLY_REGION=iad  # US East, or: lhr (London), syd (Sydney), etc.
```

**Cloudflare Provider:**
```bash
CLOUDFLARE_API_TOKEN=your_token
CLOUDFLARE_ACCOUNT_ID=your_account_id
CLOUDFLARE_NAMESPACE_ID=your_namespace  # For Durable Objects
```

**Vercel Provider:**
```bash
VERCEL_TOKEN=your_token
VERCEL_PROJECT_ID=your_project_id
VERCEL_TEAM_ID=your_team_id  # If using team
```

### Per-Session Provider Override

You can override the provider for individual sessions:

```bash
curl -X POST http://localhost:8000/api/agents/launch \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "YOUR_ANTHROPIC_API_KEY",
    "config_id": "code-assistant",
    "provider": "fly_machines"  # Override default provider
  }'
```

---

## Usage Examples

### Example 1: Local Development (Docker)

```bash
# .env
CONTAINER_PROVIDER=docker

# Start API server
docker compose up -d

# Create session
curl -X POST http://localhost:8000/api/agents/launch \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "YOUR_ANTHROPIC_API_KEY",
    "config_id": "code-assistant"
  }'

# Response
{
  "session_id": "conv-abc123",
  "agent_id": "agent-xyz",
  "provider": "docker",
  "status": "running"
}

# Chat
curl -X POST http://localhost:8000/chat/completions \
  -H "Authorization: Bearer YOUR_ANTHROPIC_API_KEY" \
  -H "X-Session-ID: conv-abc123" \
  -d '{
    "model": "claude-sonnet-4.5",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": true
  }'
```

### Example 2: Production (Fly Machines)

```bash
# .env
CONTAINER_PROVIDER=fly_machines
FLY_API_TOKEN=your_token
FLY_APP_NAME=agcluster-agents

# Deploy API to Fly
fly launch --name agcluster-api
fly deploy

# Sessions automatically use Fly Machines for agent containers
curl -X POST https://agcluster-api.fly.dev/api/agents/launch \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "YOUR_ANTHROPIC_API_KEY",
    "config_id": "data-analysis"
  }'
```

### Example 3: Global Edge (Cloudflare)

```bash
# .env
CONTAINER_PROVIDER=cloudflare
CLOUDFLARE_API_TOKEN=your_token
CLOUDFLARE_ACCOUNT_ID=your_account

# Deploy API to any cloud
# Agent containers run on Cloudflare edge

# Sessions route to nearest edge location
```

---

## Provider Comparison

| Feature | Docker | Fly Machines | Cloudflare | Vercel |
|---------|--------|--------------|------------|--------|
| **Status** | ✅ Implemented | 🚧 Planned | 🚧 Planned | 🚧 Planned |
| **Boot Time** | 2-3s | 300ms | <100ms | 1-2s |
| **Max Runtime** | Unlimited | Unlimited | 30s (Workers) | 5 hours |
| **Cost (hourly)** | Free (local) | ~$0.05 | $5/mo + usage | $20/mo (Pro) |
| **Scaling** | Manual | Automatic | Automatic | Automatic |
| **Geographic** | Single location | Multi-region | Global edge | Multi-region |
| **Best For** | Development | Production | Low latency | Short tasks |
| **Setup Complexity** | Easy | Medium | Hard (beta) | Medium |
| **Platform Lock-in** | None | Low | Medium | Medium |

### Cost Comparison (1000 queries/day, avg 2 min each)

| Provider | Daily Cost | Monthly Cost | Notes |
|----------|------------|--------------|-------|
| Docker | $0 | $0 | Local compute (electricity cost not included) |
| Fly Machines | $1.60 | ~$50 | 1GB container, 2000 minutes/day |
| Cloudflare | $0.50 | ~$20 | Workers Paid + 1M req/month |
| Vercel | $0 | $20 | Included in Pro plan (under limits) |

---

## Implementation Roadmap

### Phase 1: Foundation ✅ (Week 1)
- [x] Provider abstraction layer (`base.py`, `factory.py`)
- [x] HTTP/SSE protocol standardization
- [ ] Refactor agent_server.py to FastAPI + SSE
- [ ] Extract DockerProvider from ContainerManager
- [ ] Refactor ContainerManager to use providers
- [ ] Backward compatibility tests

### Phase 2: Fly Machines 🚧 (Week 2)
- [ ] Implement FlyProvider
- [ ] Fly API integration (create/stop/query machines)
- [ ] Push agent image to Fly registry
- [ ] Unit + integration tests
- [ ] Documentation (`docs/providers/fly-machines.md`)

### Phase 3: Cloudflare 🚧 (Week 3)
- [ ] Implement CloudflareProvider
- [ ] Worker adapter for agent (JS or Python)
- [ ] Durable Objects for session state
- [ ] Unit + integration tests (requires beta access)
- [ ] Documentation (`docs/providers/cloudflare.md`)

### Phase 4: Vercel 🚧 (Week 4)
- [ ] Implement VercelProvider
- [ ] Vercel function adapter
- [ ] Handle 5-hour runtime limit
- [ ] Unit + integration tests (requires Pro)
- [ ] Documentation (`docs/providers/vercel.md`)

### Phase 5: Testing & Polish 🚧 (Week 5-6)
- [ ] Comprehensive test suite (200+ tests)
- [ ] Load testing (100 concurrent sessions)
- [ ] Cross-provider tests
- [ ] Provider switching/fallback
- [ ] Complete documentation

---

## Adding New Providers

Want to add support for a new platform? Here's how:

### 1. Implement ContainerProvider Interface

```python
# src/agcluster/container/core/providers/your_provider.py
from .base import ContainerProvider, ContainerInfo, ProviderConfig
import httpx

class YourProvider(ContainerProvider):
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.client = httpx.AsyncClient()

    async def create_container(self, session_id: str, config: ProviderConfig) -> ContainerInfo:
        # Call your platform's API to create container
        response = await self.client.post(
            "https://api.yourplatform.com/containers",
            headers={"Authorization": f"Bearer {self.api_token}"},
            json={
                "image": "agcluster/agent:latest",
                "env": {
                    "ANTHROPIC_API_KEY": config.api_key,
                    "ALLOWED_TOOLS": ",".join(config.allowed_tools),
                }
            }
        )
        data = response.json()
        return ContainerInfo(
            container_id=data["id"],
            endpoint_url=f"https://{data['hostname']}",
            status="running",
            platform="your_platform",
            metadata={"raw_response": data}
        )

    async def execute_query(self, container_info: ContainerInfo, query: str, history: list) -> AsyncIterator:
        # Send query via HTTP/SSE
        async with self.client.stream(
            "POST",
            f"{container_info.endpoint_url}/query",
            json={"query": query, "history": history}
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    yield json.loads(line[6:])

    # Implement other required methods...
```

### 2. Register Provider

```python
# src/agcluster/container/core/providers/__init__.py
from .your_provider import YourProvider
from .factory import ProviderFactory

# Register at module load time
ProviderFactory.register_provider("your_platform", YourProvider)
```

### 3. Add Configuration

```yaml
# configs/providers/your_platform.yaml
platform: your_platform
credentials:
  api_token: ${YOUR_PLATFORM_API_TOKEN}
```

### 4. Write Tests

```python
# tests/unit/providers/test_your_provider.py
import pytest
from agcluster.container.core.providers import YourProvider

@pytest.mark.unit
def test_create_container_mocked():
    # Unit test with mocked API
    pass

@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("YOUR_PLATFORM_API_TOKEN"), reason="Token required")
async def test_create_container_real():
    # Integration test with real API
    provider = YourProvider(api_token=os.getenv("YOUR_PLATFORM_API_TOKEN"))
    # ... test real creation
```

### 5. Document

Create `docs/providers/your-platform.md` with:
- Setup instructions
- Cost breakdown
- Performance characteristics
- Limitations
- Example usage

---

## Troubleshooting

### Provider Not Found

```
ValueError: Unknown provider platform: xyz
```

**Solution:** Check `CONTAINER_PROVIDER` setting and ensure provider is registered.

```bash
# List available providers
python -c "from agcluster.container.core.providers import ProviderFactory; print(ProviderFactory.list_providers())"
```

### Container Creation Fails

**Docker:**
- Check Docker daemon is running: `docker ps`
- Check Docker network exists: `docker network ls | grep agcluster`

**Fly:**
- Verify API token: `fly auth whoami`
- Check app exists: `fly apps list`

**Cloudflare:**
- Verify beta access enabled
- Check API token permissions

**Vercel:**
- Ensure Vercel Pro subscription active
- Verify project ID exists

### HTTP/SSE Connection Issues

**Check endpoint accessibility:**
```bash
# Docker
curl http://localhost:3000/health

# Fly
curl https://your-agent.fly.dev/health
```

**Check SSE streaming:**
```bash
curl -N -H "Accept: text/event-stream" \
  -X POST http://localhost:3000/query \
  -d '{"query": "test"}'
```

---

## Support & Contributions

- **Issues:** https://github.com/anthropics/agcluster-container/issues
- **Discussions:** https://github.com/anthropics/agcluster-container/discussions
- **Contributing:** See `CONTRIBUTING.md`

**Questions about providers?**
- Docker: Working implementation reference
- Fly: Join Fly.io community forum
- Cloudflare: Request beta access via Cloudflare dashboard
- Vercel: Vercel Pro required

---

**Last Updated:** 2025-01-XX (Phase 1 complete, providers in progress)
