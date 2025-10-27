# AgCluster UI

Full-featured web interface for the AgCluster Container platform, built with Next.js 15 and Vercel AI SDK.

**Part of the AgCluster monorepo** - The UI and API are in the same repository for easy setup and deployment. Start both with a single command!

## Features

- **Dashboard**: Launch agents from preset configurations (code-assistant, research-agent, data-analysis, fullstack-team)
- **Chat Interface**: Real-time conversation with Claude agents via Vercel AI SDK
- **Agent Builder**: Visual configuration creator (coming soon)
- **Session Management**: Monitor active containers and resources (coming soon)
- **File Viewer**: Browse and preview files created by agents (coming soon)

## Tech Stack

- **Next.js 15**: App Router with React Server Components
- **Vercel AI SDK**: Streaming chat interface with useChat hook
- **TypeScript**: Full type safety
- **Tailwind CSS**: Utility-first styling with custom theme
- **React Markdown**: Rich markdown rendering with syntax highlighting
- **Lucide React**: Beautiful icon library

## Quick Start (Monorepo)

Since the UI is part of the AgCluster monorepo, you can start both the API and UI easily:

### Option 1: Docker Compose (Recommended)

From the repository root:

```bash
# From the agcluster-container root directory
docker compose up -d
```

This starts:
- AgCluster API on `http://localhost:8000`
- AgCluster UI on `http://localhost:3000`

### Option 2: Manual (Development)

**Prerequisites:**
```bash
# Create the Docker network (one-time setup)
docker network create agcluster-container_agcluster-network

# Build the agent image (one-time setup from root directory)
docker build -t agcluster/agent:latest -f docker/Dockerfile.agent .
```

**Terminal 1 - Start Backend:**
```bash
# From the agcluster-container root directory
python -m uvicorn agcluster.container.api.main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 - Start UI:**
```bash
# From the UI directory (src/agcluster/container/ui)
npm install
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000)

### Verify Backend is Running

```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy"}
```

## Development

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

Visit [http://localhost:3000](http://localhost:3000)

If you see a "Backend Not Running" error, make sure the AgCluster API is running on port 8000 (see Prerequisites above).

## Environment Variables

Create a `.env.local` file:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Project Structure

```
ui/
├── app/
│   ├── page.tsx                  # Dashboard
│   ├── chat/[id]/page.tsx        # Chat interface
│   ├── layout.tsx                # Root layout
│   └── api/ai/chat/route.ts      # Vercel AI SDK chat endpoint
├── components/
│   ├── chat/                     # Chat UI components
│   ├── builder/                  # Agent builder components
│   ├── sessions/                 # Session management
│   └── files/                    # File explorer
├── lib/
│   ├── agcluster-provider.ts     # Custom AI SDK provider
│   └── api-client.ts             # AgCluster API client
└── package.json
```

## Usage

### 1. Enter API Key

On the dashboard, enter your Anthropic API key. It will be stored in localStorage for convenience.

### 2. Launch Agent

Click on any preset agent card to launch a new containerized agent session.

### 3. Chat

The chat interface will open automatically. Start typing to interact with your agent!

### 4. Agent Features

- **Code Assistant**: Full development tools (Bash, Read, Write, Edit, Grep)
- **Research Agent**: Web research (WebFetch, WebSearch)
- **Data Analysis**: Statistical analysis with Jupyter support (NotebookEdit)
- **Fullstack Team**: Multi-agent orchestrator with 3 specialized sub-agents

## Integration with AgCluster API

The UI communicates with the AgCluster FastAPI backend at `http://localhost:8000`:

- **GET /api/configs**: List available agent configurations
- **POST /api/agents/launch**: Launch new agent with config
- **POST /chat/completions**: OpenAI-compatible chat endpoint (via Vercel AI SDK)

## Coming Soon

- **Agent Builder**: Visual config creator with YAML export
- **Session Management**: View active sessions, resource usage, terminate containers
- **File Viewer**: Browse workspace files, syntax highlighting, download as ZIP
- **Tool Execution Panel**: Real-time display of Bash commands, file operations
- **Multi-Agent Visualization**: Color-coded messages for orchestrator + sub-agents
- **TodoWrite Integration**: Interactive task checklist display
- **Export Features**: Download conversations as Markdown, share agent configs

## Development Roadmap

See [PHASE1_COMPLETE.md](../../../../PHASE1_COMPLETE.md) for implementation status.
