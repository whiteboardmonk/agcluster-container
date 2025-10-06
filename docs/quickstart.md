# Quick Start Guide

Get AgCluster Container running in under 5 minutes.

## Prerequisites

1. **Docker** - [Install Docker](https://docs.docker.com/get-docker/)
2. **Docker Compose** - Usually included with Docker Desktop
3. **Anthropic API Key** - Get one at [console.anthropic.com](https://console.anthropic.com/)

## Step 1: Clone the Repository

```bash
git clone https://github.com/whiteboardmonk/agcluster-container.git
cd agcluster-container
```

## Step 2: Configure (Optional)

```bash
cp .env.example .env
# Edit .env if you want to customize settings
```

Default settings work fine for local development.

## Step 3: Start AgCluster

```bash
docker compose up -d
```

This will:
- Build the agent Docker image
- Start the AgCluster API server
- Expose the API at `http://localhost:8000`

**Verify it's running:**
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "agent_image": "agcluster/agent:latest"
}
```

## Step 4: Test with cURL

### Single Message (No Session Persistence)

```bash
curl -X POST http://localhost:8000/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ANTHROPIC_API_KEY" \
  -d '{
    "model": "claude-sonnet-4.5",
    "messages": [
      {"role": "user", "content": "What is 2+2?"}
    ],
    "stream": true
  }'
```

### Multi-Turn Conversation (With Session Persistence)

```bash
# First message - creates new session
curl -X POST http://localhost:8000/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ANTHROPIC_API_KEY" \
  -H "X-Conversation-ID: my-test-conversation" \
  -d '{
    "model": "claude-sonnet-4.5",
    "messages": [
      {"role": "user", "content": "My name is Alice"}
    ],
    "stream": true
  }'

# Second message - reuses same container and session!
curl -X POST http://localhost:8000/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ANTHROPIC_API_KEY" \
  -H "X-Conversation-ID: my-test-conversation" \
  -d '{
    "model": "claude-sonnet-4.5",
    "messages": [
      {"role": "user", "content": "What is my name?"}
    ],
    "stream": true
  }'
```

Replace `YOUR_ANTHROPIC_API_KEY` with your actual API key.

**💡 Key Points:**
- **Without** `X-Conversation-ID`: Each request gets a new container
- **With** `X-Conversation-ID`: Same conversation ID = same container = context preserved!
- The second request should respond with "Alice" since it reuses the session

## Step 5: Use with LibreChat (Recommended)

For a better chat experience, use LibreChat as the UI.

### 5a. Setup LibreChat

```bash
# In a different directory
git clone https://github.com/danny-avila/LibreChat.git
cd LibreChat
```

### 5b. Configure LibreChat

Create `librechat.yaml`:

```yaml
version: 1.1.8
cache: true

endpoints:
  custom:
    - name: "AgCluster"
      apiKey: "user_provided"
      baseURL: "http://host.docker.internal:8000"  # or http://localhost:8000
      models:
        default:
          - "claude-sonnet-4.5"
      titleConvo: true
      # Important: Send conversation ID for session persistence
      headers:
        X-Conversation-ID: "{{conversationId}}"
```

### 5c. Start LibreChat

```bash
docker compose up -d
```

### 5d. Chat!

1. Open `http://localhost:3080`
2. Select "AgCluster" from the dropdown
3. Enter your Anthropic API key
4. Start chatting!

## What's Happening Behind the Scenes?

1. **You send a message** in LibreChat
2. **LibreChat** sends POST request to AgCluster with conversation ID
3. **AgCluster Session Manager** checks if container exists for this conversation
   - If exists: Reuses the same container (context preserved!)
   - If new: Creates a Docker container with Claude Agent SDK
4. **Claude SDK** processes your message with tools (Bash, Read, Write, etc.)
5. **Responses stream back** through SSE to LibreChat
6. **You see results** in the chat UI
7. **Container stays alive** for the next message in the conversation
8. **Background task** removes containers idle for more than 30 minutes

## Verify Session Persistence

Check that agent containers persist across messages:

```bash
# View active agent containers
docker ps | grep agcluster

# Send multiple messages in LibreChat
# Notice: The same container ID appears in the logs for all messages in the conversation!

# View AgCluster logs to see session reuse
docker compose logs -f api
```

You should see:
- New containers created for new conversations: `Creating new session for conversation...`
- Containers reused for existing conversations: `Reusing existing session...`
- Same container ID used for all messages in a conversation thread

## Stop AgCluster

```bash
docker compose down
```

## Troubleshooting

### Port 8000 Already in Use

Change the port in `.env`:
```bash
API_PORT=8001
```

And update LibreChat's `baseURL` accordingly.

### Docker Socket Permission Denied

On Linux:
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Can't Connect from LibreChat

If LibreChat is running in Docker and can't reach `localhost:8000`, use:
```yaml
baseURL: "http://host.docker.internal:8000"
```

Or put both services on the same Docker network.

### Image Build Fails

Make sure you have enough disk space:
```bash
docker system df
docker system prune  # Clean up if needed
```

## Next Steps

- Read the [LibreChat Integration Guide](../librechat/README.md)
- Explore the [Architecture](architecture.md)
- Check the [API Reference](../README.md#api-reference)
- Join our community (Discord link coming soon)

## Getting Help

- GitHub Issues: [Report bugs](https://github.com/whiteboardmonk/agcluster-container/issues)
- Discussions: [Ask questions](https://github.com/whiteboardmonk/agcluster-container/discussions)
