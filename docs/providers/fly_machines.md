# Fly Machines Provider

The Fly Machines provider enables AgCluster to deploy Claude Agent SDK containers on Fly.io's infrastructure using the Machines API.

## Overview

**Platform:** Fly.io Machines
**Communication:** HTTP/SSE over IPv6 private network
**Pricing:** Pay-as-you-go compute (billed per second)
**Provider ID:** `fly_machines`

### Key Features

- **Ephemeral Compute**: Create and destroy machines on-demand
- **Global Edge Deployment**: Deploy to 30+ regions worldwide
- **IPv6 Native Networking**: Private IPv6 networking between machines
- **Fast Cold Starts**: Machines start in <2 seconds
- **Per-Second Billing**: Only pay for compute time used
- **Built-in Health Checks**: HTTP health monitoring included

## Prerequisites

### 1. Fly.io Account

Create a free Fly.io account:

```bash
# Install flyctl CLI
curl -L https://fly.io/install.sh | sh

# Sign up or login
flyctl auth signup
# or
flyctl auth login
```

### 2. Create Fly App

Create a Fly app to host your agent machines:

```bash
flyctl apps create agcluster-agents

# Note: App name must be globally unique
```

### 3. Push Agent Image to Fly Registry

Build and push the agent Docker image to Fly's registry:

```bash
# Build locally
docker build -t agcluster/agent:latest -f docker/Dockerfile.agent .

# Tag for Fly registry
docker tag agcluster/agent:latest registry.fly.io/agcluster-agents:latest

# Login to Fly registry
flyctl auth docker

# Push image
docker push registry.fly.io/agcluster-agents:latest
```

### 4. Get API Token

Generate a Fly API token:

```bash
flyctl auth token
```

This token is used for authenticating with the Fly Machines API.

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Fly.io Configuration
FLY_API_TOKEN=your_fly_api_token_here
FLY_APP_NAME=agcluster-agents
FLY_REGION=iad  # Optional: default region
FLY_IMAGE=registry.fly.io/agcluster-agents:latest
```

### Provider Configuration

Create a provider config in your agent configuration YAML:

```yaml
# configs/presets/code-assistant-fly.yaml
id: code-assistant-fly
name: Code Assistant (Fly.io)
description: Full-stack development agent on Fly.io
platform: fly_machines  # Use Fly provider
allowed_tools:
  - Bash
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Task
  - TodoWrite
system_prompt: "You are a full-stack development assistant..."
permission_mode: acceptEdits
resource_limits:
  cpu_quota: 200000  # 2 CPUs
  memory_limit: 4g
  storage_limit: 10g
max_turns: 100
platform_credentials:
  fly_region: sjc  # Optional: override default region
```

## Usage

### Launch Agent with Fly Provider

```bash
curl -X POST http://localhost:8000/api/agents/launch \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "YOUR_ANTHROPIC_API_KEY",
    "config_id": "code-assistant-fly",
    "platform": "fly_machines",
    "platform_credentials": {
      "fly_api_token": "YOUR_FLY_TOKEN",
      "fly_app_name": "agcluster-agents",
      "fly_region": "iad"
    }
  }'
```

Response:

```json
{
  "session_id": "conv-abc123...",
  "agent_id": "agent-xyz789...",
  "container_id": "machine-4d3f2e1a",
  "endpoint_url": "http://[fdaa:0:1da6:a7b:7b:6f9a:c582:2]:3000",
  "status": "running",
  "platform": "fly_machines",
  "metadata": {
    "machine_name": "agcluster-agent-xyz789",
    "agent_id": "agent-xyz789",
    "session_id": "conv-abc123",
    "private_ip": "fdaa:0:1da6:a7b:7b:6f9a:c582:2",
    "region": "iad",
    "app_name": "agcluster-agents"
  }
}
```

### Send Queries

```bash
curl -X POST http://localhost:8000/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ANTHROPIC_API_KEY" \
  -H "X-Session-ID: conv-abc123..." \
  -d '{
    "model": "claude-sonnet-4.5",
    "messages": [
      {"role": "user", "content": "Create a Python Flask app"}
    ],
    "stream": true
  }'
```

### Programmatic Usage

```python
from agcluster.container.core.providers import ProviderFactory, ProviderConfig

# Create provider instance
provider = ProviderFactory.create_provider(
    platform="fly_machines",
    api_token="your_fly_token",
    app_name="agcluster-agents",
    region="iad",
    image="registry.fly.io/agcluster-agents:latest"
)

# Create machine
config = ProviderConfig(
    platform="fly_machines",
    cpu_quota=200000,  # 2 CPUs
    memory_limit="4g",
    storage_limit="10g",
    allowed_tools=["Bash", "Read", "Write", "Grep"],
    system_prompt="You are a helpful AI assistant.",
    max_turns=100,
    api_key="sk-ant-...",
    platform_credentials={"fly_region": "sjc"}
)

container_info = await provider.create_container(
    session_id="session-123",
    config=config
)

print(f"Machine created: {container_info.container_id}")
print(f"Endpoint: {container_info.endpoint_url}")

# Execute query
async for message in provider.execute_query(
    container_info=container_info,
    query="Hello, world!",
    conversation_history=[]
):
    print(message)

# Cleanup
await provider.stop_container(container_info.container_id)
await provider.cleanup()
```

## Regional Deployment

Fly.io has 30+ regions worldwide. Choose the closest region for lowest latency:

### Available Regions

| Region | Location | Code |
|--------|----------|------|
| Ashburn, VA | US East | `iad` |
| San Jose, CA | US West | `sjc` |
| Los Angeles, CA | US West | `lax` |
| Chicago, IL | US Central | `ord` |
| Dallas, TX | US Central | `dfw` |
| London, UK | Europe | `lhr` |
| Paris, France | Europe | `cdg` |
| Frankfurt, Germany | Europe | `fra` |
| Tokyo, Japan | Asia | `nrt` |
| Singapore | Asia | `sin` |
| Sydney, Australia | Oceania | `syd` |

Full list: https://fly.io/docs/reference/regions/

### Region Selection

```python
# Set default region for provider
provider = ProviderFactory.create_provider(
    platform="fly_machines",
    api_token=FLY_TOKEN,
    app_name="agcluster-agents",
    region="sjc"  # Default: San Jose
)

# Override per-agent
config = ProviderConfig(
    platform="fly_machines",
    # ... other settings ...
    platform_credentials={
        "fly_region": "nrt"  # Deploy to Tokyo
    }
)
```

## Resource Limits

### CPU

CPU quota is specified in Docker units (100000 = 1 CPU) and converted to Fly CPU count:

| CPU Quota | Fly CPUs | Use Case |
|-----------|----------|----------|
| 100000 | 1 | Light tasks, research |
| 200000 | 2 | Development, analysis |
| 400000 | 4 | Heavy builds, data processing |
| 800000 | 8 | Intensive workloads |

### Memory

Specify memory limits in standard formats:

- `512m`, `512mb` = 512 MB
- `1g`, `1gb` = 1 GB (1024 MB)
- `2g` = 2 GB (2048 MB)
- `4g` = 4 GB (4096 MB)

### Pricing Example

```python
# Configuration
cpu_quota = 200000  # 2 CPUs
memory_limit = "4g"  # 4 GB RAM

# Fly.io pricing (approximate, varies by region)
# Shared CPU: $0.0000008/sec per CPU (~$2.07/mo per CPU)
# Memory: $0.0000002/sec per MB (~$0.52/mo per GB)

# Cost per second:
# 2 CPUs: 2 * $0.0000008 = $0.0000016/sec
# 4 GB: 4096 * $0.0000002 = $0.0000008/sec
# Total: $0.0000024/sec (~$6.22/mo if running 24/7)

# Actual cost is lower since machines only run during active sessions
```

## Networking

### IPv6 Private Network

Fly Machines use IPv6 for private networking:

```
Private IP: fdaa:0:1da6:a7b:7b:6f9a:c582:2
Endpoint: http://[fdaa:0:1da6:a7b:7b:6f9a:c582:2]:3000
```

### Communication Flow

```
AgCluster API
  ↓ Creates machine via Fly API
  ↓ POST https://api.machines.dev/v1/apps/{app}/machines
Fly Machine
  ↓ Starts with agent server on port 3000
  ↓ Agent listens on http://[IPv6]:3000
AgCluster API
  ↓ Sends query via HTTP POST
  ↓ POST http://[IPv6]:3000/query
  ↓ Receives SSE stream
Agent Container
  ↓ Processes query with Claude SDK
  ↓ Streams responses back
```

### Health Checks

The provider waits for HTTP health endpoint before marking machine as ready:

```
GET http://[IPv6]:3000/health

Response:
{
  "status": "healthy",
  "agent_id": "agent-xyz",
  "uptime": 15.3
}
```

## Error Handling

### Common Errors

#### 1. Invalid API Token (401)

```json
{
  "error": "Invalid Fly API token"
}
```

**Fix**: Get a valid token with `flyctl auth token`

#### 2. App Not Found (404)

```json
{
  "error": "Fly app 'agcluster-agents' not found. Create it with: flyctl apps create agcluster-agents"
}
```

**Fix**: Create the app first with `flyctl apps create`

#### 3. Image Not Found (500)

```json
{
  "error": "Fly API error (500): image not found in registry"
}
```

**Fix**: Push image to Fly registry:

```bash
docker tag agcluster/agent:latest registry.fly.io/agcluster-agents:latest
flyctl auth docker
docker push registry.fly.io/agcluster-agents:latest
```

#### 4. Machine Creation Timeout

```json
{
  "error": "Machine did not reach state 'started' within 60s"
}
```

**Fix**: Check Fly status: `flyctl status` and retry

#### 5. Health Check Timeout

Machine created but HTTP server not responding.

**Cause**: Agent container failed to start or crashed

**Debug**:

```bash
# View machine logs
flyctl logs -a agcluster-agents

# SSH into machine
flyctl ssh console -a agcluster-agents -s machine-id
```

## Monitoring

### List Active Machines

```bash
# Via Fly CLI
flyctl machines list -a agcluster-agents

# Via API
curl http://localhost:8000/api/agents/sessions
```

### View Machine Logs

```bash
# All logs for app
flyctl logs -a agcluster-agents

# Specific machine
flyctl logs -a agcluster-agents --instance machine-id
```

### Machine Metrics

```bash
# View machine status
flyctl status -a agcluster-agents

# Machine details
flyctl machines status machine-id -a agcluster-agents
```

## Performance

### Cold Start Time

- **Docker provider**: 3-5 seconds (local container startup)
- **Fly provider**: 2-4 seconds (remote machine creation + startup)

### Request Latency

Latency depends on distance to Fly region:

| Client Location | Fly Region | Avg Latency |
|----------------|------------|-------------|
| US East | iad | 5-10ms |
| US West | sjc | 5-10ms |
| Europe | lhr | 10-20ms |
| Asia | nrt | 10-20ms |

### Throughput

SSE streaming performance is comparable to Docker provider since both use HTTP/SSE:

- **Text streaming**: ~1000 tokens/sec
- **Tool execution**: Limited by network latency to Anthropic API

## Cost Optimization

### 1. Automatic Cleanup

AgCluster automatically stops machines after session ends:

```python
# Session Manager config
SESSION_IDLE_TIMEOUT=1800  # 30 minutes
SESSION_CLEANUP_INTERVAL=300  # Check every 5 minutes
```

### 2. Right-Size Resources

Match resource allocation to workload:

```yaml
# Light research tasks
cpu_quota: 100000  # 1 CPU
memory_limit: 2g

# Development work
cpu_quota: 200000  # 2 CPUs
memory_limit: 4g

# Data processing
cpu_quota: 400000  # 4 CPUs
memory_limit: 8g
```

### 3. Regional Pricing

Some regions have lower pricing. Check current rates:

```bash
flyctl pricing
```

### 4. Shared CPUs vs. Dedicated

For most workloads, shared CPUs (default) are sufficient and cheaper.

## Limitations

### Current Limitations

1. **No Persistent Storage**: Machines are ephemeral, workspace is lost on stop
2. **No Auto-scaling**: One machine per session (no horizontal scaling)
3. **IPv6 Only**: Private networking uses IPv6
4. **No GPU Support**: Fly Machines don't support GPUs yet
5. **Image Size**: Agent image must be <10 GB

### Future Enhancements

- [ ] Persistent volumes for workspace
- [ ] Multi-machine sessions for distributed workloads
- [ ] IPv4 networking option
- [ ] GPU support when available
- [ ] Image layer caching for faster deploys

## Troubleshooting

### Machine Won't Start

```bash
# Check app status
flyctl status -a agcluster-agents

# View recent events
flyctl logs -a agcluster-agents --recent

# Try creating machine manually
flyctl machines run registry.fly.io/agcluster-agents:latest \
  --app agcluster-agents \
  --region iad
```

### Connection Refused

**Symptom**: `execute_query` fails with connection error

**Causes**:
1. Machine not fully started
2. Agent server crashed
3. Firewall blocking IPv6

**Fix**:
```bash
# SSH into machine
flyctl ssh console -a agcluster-agents -s machine-id

# Check if server is running
ps aux | grep agent_server
netstat -tlnp | grep 3000

# View server logs
tail -f /var/log/agent_server.log
```

### High Latency

**Symptom**: Slow response times

**Causes**:
1. Machine in distant region
2. Network congestion
3. Anthropic API latency

**Fix**:
```yaml
# Use closer region
platform_credentials:
  fly_region: iad  # Use closest to your location

# Monitor latency
flyctl ping -a agcluster-agents
```

## Security

### API Token Security

**Never commit tokens to git:**

```bash
# .gitignore
.env
*.token
```

**Use environment variables:**

```python
import os
FLY_API_TOKEN = os.getenv("FLY_API_TOKEN")
```

### Network Security

- **Private IPv6**: Machines are on private Fly network
- **No Public Access**: Machines not exposed to internet by default
- **TLS**: All Fly API communication uses HTTPS

### Container Security

- **Ephemeral**: Machines destroyed after use
- **Isolated**: Each session gets separate machine
- **No Privileges**: Containers run without elevated privileges

## Best Practices

1. **Use Regions Wisely**: Deploy to region closest to users
2. **Monitor Costs**: Track machine usage with Fly dashboard
3. **Cleanup Promptly**: Stop machines when sessions end
4. **Right-Size Resources**: Don't over-provision CPU/memory
5. **Cache Images**: Push agent image once, reuse many times
6. **Handle Errors**: Implement retry logic for transient failures
7. **Log Everything**: Enable verbose logging for debugging
8. **Test Locally First**: Use Docker provider for development

## Example: Multi-Region Setup

Deploy agents to multiple regions for global coverage:

```python
regions = ["iad", "lhr", "nrt", "syd"]

providers = {
    region: ProviderFactory.create_provider(
        platform="fly_machines",
        api_token=FLY_TOKEN,
        app_name=f"agcluster-{region}",
        region=region
    )
    for region in regions
}

# Route user to closest region
user_region = get_user_region(user_ip)
provider = providers[user_region]

# Create machine
container_info = await provider.create_container(
    session_id=session_id,
    config=config
)
```

## Support

- **Fly.io Docs**: https://fly.io/docs/machines/
- **Fly.io Community**: https://community.fly.io/
- **AgCluster Issues**: https://github.com/yourusername/agcluster-container/issues

---

**Next Steps**:
- Try the [Cloudflare Workers provider](./cloudflare_workers.md) for serverless deployment
- Learn about [multi-provider orchestration](../multi-provider.md)
- Read the [provider development guide](../development/providers.md)
