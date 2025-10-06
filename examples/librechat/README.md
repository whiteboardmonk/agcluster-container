# LibreChat Integration Guide

This guide explains how to connect LibreChat to AgCluster for a polished chat UI with Claude agents.

## Quick Start

### 1. Start AgCluster

```bash
cd /path/to/agcluster-container
docker compose up -d
```

AgCluster API will be available at `http://localhost:8000`

### 2. Setup LibreChat

Clone and configure LibreChat:

```bash
# Clone LibreChat
git clone https://github.com/danny-avila/LibreChat.git
cd LibreChat

# Copy example config
cp librechat.example.yaml librechat.yaml
```

### 3. Configure LibreChat

Edit `librechat.yaml` to add AgCluster as a custom endpoint:

```yaml
version: 1.1.8
cache: true

endpoints:
  custom:
    - name: "AgCluster (Claude Agent)"
      apiKey: "user_provided"
      baseURL: "http://localhost:8000"
      models:
        default:
          - "claude-sonnet-4.5"
      titleConvo: true
      titleModel: "claude-sonnet-4.5"
```

You can copy the full example from `librechat.example.yaml` in this directory.

### 4. Start LibreChat

```bash
docker compose up -d
```

LibreChat will be available at `http://localhost:3080`

### 5. Use AgCluster in LibreChat

1. Open LibreChat at `http://localhost:3080`
2. Select "AgCluster (Claude Agent)" from the model dropdown
3. Enter your Anthropic API key when prompted (stored in browser)
4. Start chatting!

## How It Works

```
┌────────────────┐      ┌────────────────┐      ┌──────────────────┐
│   LibreChat    │      │   AgCluster     │      │  Docker Container│
│   (UI)         │─────▶│   API          │─────▶│  Claude SDK      │
│                │ HTTP  │                │ WS   │                  │
└────────────────┘      └────────────────┘      └──────────────────┘
```

1. You chat in LibreChat
2. LibreChat sends requests to AgCluster API (`POST /chat/completions`)
3. AgCluster creates a Docker container running Claude Agent SDK
4. Responses stream back through SSE to LibreChat
5. You see the results in the chat UI

## Configuration Options

### Custom System Prompt

To use a custom system prompt, you'll need to create a persistent agent first via AgCluster's API, then reference it in LibreChat:

```yaml
models:
  default:
    - "agent-YOUR_AGENT_ID"
```

### Multiple Instances

You can configure multiple AgCluster instances (e.g., dev, staging, production):

```yaml
endpoints:
  custom:
    - name: "AgCluster Local"
      apiKey: "user_provided"
      baseURL: "http://localhost:8000"
      models:
        default:
          - "claude-sonnet-4.5"

    - name: "AgCluster Production"
      apiKey: "user_provided"
      baseURL: "https://agcluster.yourdomain.com"
      models:
        default:
          - "claude-sonnet-4.5"
```

## Troubleshooting

### Connection Error

**Problem:** LibreChat can't connect to AgCluster

**Solution:**
- Ensure AgCluster is running: `docker ps | grep agcluster`
- Check AgCluster health: `curl http://localhost:8000/health`
- Check baseURL in `librechat.yaml` is correct

### Authentication Error

**Problem:** "Missing or invalid Authorization header"

**Solution:**
- Make sure you entered your Anthropic API key in LibreChat
- Verify the key is valid at https://console.anthropic.com/

### Streaming Not Working

**Problem:** Responses appear all at once instead of streaming

**Solution:**
- Check that `stream: true` is set in the request (default in LibreChat)
- Verify SSE headers are not being stripped by reverse proxy

### Docker Socket Permission Denied

**Problem:** AgCluster can't create containers

**Solution:**
```bash
# Add your user to docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker

# Or run AgCluster as root (not recommended for production)
sudo docker compose up -d
```

## Advanced: Cloud Deployment

### Deploy AgCluster to Cloud

```bash
# Railway
railway up

# Or Render
render deploy
```

Update LibreChat config:

```yaml
baseURL: "https://your-agcluster.railway.app"
```

### CORS Issues

If deploying to different domains, update AgCluster's CORS settings in `agcluster/api/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-librechat.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Resources

- [LibreChat Documentation](https://www.librechat.ai/docs)
- [AgCluster GitHub](https://github.com/agcluster/agcluster-container)
- [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python)
