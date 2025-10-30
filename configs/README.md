# Agent Configuration Presets

This directory contains pre-configured agent templates that can be used to launch specialized Claude agents.

## Available Presets

### 1. Code Assistant (`code-assistant.yaml`)

**Purpose:** General-purpose software development

**Features:**
- Full access to code editing tools (Read, Write, Edit, Grep)
- Bash execution for running tests and builds
- Task delegation for complex workflows
- Follows TDD principles
- Loads project-specific instructions from CLAUDE.md

**Best For:**
- Feature development
- Bug fixing
- Code refactoring
- Writing tests
- Git operations

**Resource Allocation:** 2 CPUs, 4GB RAM

---

### 2. Research Agent (`research-agent.yaml`)

**Purpose:** Web research and information gathering

**Features:**
- WebSearch and WebFetch for internet access
- Optimized for analyzing and synthesizing information
- Creates structured reports with source citations
- Lighter resource footprint

**Best For:**
- Market research
- Technical documentation research
- Competitive analysis
- Gathering requirements
- Literature reviews

**Resource Allocation:** 1 CPU, 2GB RAM

---

### 3. Data Analysis Agent (`data-analysis.yaml`)

**Purpose:** Statistical analysis and data visualization

**Features:**
- Pandas, numpy, scipy, matplotlib support
- NotebookEdit for Jupyter-style workflows
- Bash for data processing scripts
- Optimized for exploratory data analysis

**Best For:**
- Statistical testing
- Data cleaning and transformation
- Visualization and plotting
- ML model evaluation
- Interactive data debugging

**Resource Allocation:** 2 CPUs, 6GB RAM

---

### 4. GitHub Code Review (`github-code-review.yaml`)

**Purpose:** Automated GitHub pull request reviews

**Features:**
- **MCP Integration**: Uses GitHub MCP server for API access
- Systematic code review with focus on:
  - Code quality and maintainability
  - Security vulnerabilities
  - Performance optimizations
  - Testing coverage
  - Architecture patterns
- Auto-enabled MCP tools (ListMcpResources, ReadMcpResource)
- Runtime credential injection via `mcp_env`

**Best For:**
- Automated PR reviews
- Security audits
- Code quality checks
- Architecture analysis
- Best practices enforcement

**Resource Allocation:** 1 CPU, 2GB RAM

**Usage with Credentials:**
```bash
curl -X POST http://localhost:8000/api/agents/launch \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "sk-ant-...",
    "config_id": "github-code-review",
    "mcp_env": {
      "github": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_..."
      }
    }
  }'
```

---

### 5. Full-Stack Team (`fullstack-team.yaml`)

**Purpose:** Multi-agent orchestration for complex projects

**Features:**
- **Lead Orchestrator:** Coordinates specialized sub-agents
- **Frontend Agent:** React, Next.js, Tailwind CSS specialist
- **Backend Agent:** Python, FastAPI, database expert
- **DevOps Agent:** Docker, CI/CD, deployment specialist
- Automatic task delegation based on requirements

**Best For:**
- Large feature implementations spanning frontend + backend
- Full-stack refactoring
- Setting up new projects
- Complex integrations
- Team-style development

**Resource Allocation:** 3 CPUs, 6GB RAM

---

## Using Presets

### Via API

```bash
curl -X POST http://localhost:8000/api/agents/launch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ANTHROPIC_API_KEY" \
  -d '{"config_id": "code-assistant"}'
```

### Via UI

1. Navigate to "Launch Agent"
2. Browse available presets
3. Select desired configuration
4. Click "Launch"
5. Start chatting with your agent

---

## Creating Custom Configurations

You can create your own agent configurations by:

1. **Copy an existing preset:**
   ```bash
   cp configs/presets/code-assistant.yaml ~/.agcluster/configs/my-agent.yaml
   ```

2. **Edit the configuration:**
   - Change `id` and `name`
   - Customize `system_prompt`
   - Adjust `allowed_tools` list
   - Modify `resource_limits`
   - Add MCP servers if needed

3. **Use your custom config:**
   ```bash
   curl -X POST http://localhost:8000/api/agents/launch \
     -d '{"config_id": "my-agent"}'
   ```

---

## Configuration Reference

### Required Fields
- `id`: Unique identifier (lowercase, hyphens allowed)
- `name`: Human-readable name
- `version`: Semantic version (e.g., "1.0.0")

### Core Options
- `system_prompt`: Agent's instructions (string or preset)
- `allowed_tools`: List of tools the agent can use
- `permission_mode`: How to handle permissions
  - `default`: Ask for permission
  - `acceptEdits`: Auto-approve file edits
  - `plan`: Planning mode (no execution)
  - `bypassPermissions`: Skip all permission checks (use with caution)

### Available Tools
- **File Operations:** Read, Write, Edit, Grep, Glob
- **Execution:** Bash, BashOutput, KillBash
- **Web Access:** WebFetch, WebSearch
- **Workflow:** Task (for sub-agents), TodoWrite
- **Notebooks:** NotebookEdit
- **MCP:** ListMcpResources, ReadMcpResource, `mcp__*`

### Multi-Agent Support
Use the `agents` field to define sub-agents:

```yaml
agents:
  specialist-name:
    description: "When to use this agent"
    prompt: "Agent's system prompt"
    tools: ["Read", "Write"]
    model: "sonnet"  # or "opus", "haiku", "inherit"
```

### MCP Server Integration

AgCluster supports the Model Context Protocol (MCP) for integrating external tools and services. MCP servers are defined in configuration files and credentials are provided at launch time.

**Configuration Structure:**
```yaml
mcp_servers:
  github:                                          # Server name
    command: npx                                   # Executable
    args: ["-y", "@modelcontextprotocol/server-github"]  # Arguments
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: ${GITHUB_TOKEN}  # Placeholder
```

**Runtime Credentials:**

Provide actual credentials via the `mcp_env` parameter when launching agents:

```bash
curl -X POST http://localhost:8000/api/agents/launch \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "sk-ant-...",
    "config_id": "github-code-review",
    "mcp_env": {
      "github": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token_here"
      }
    }
  }'
```

**Key Features:**
- **Auto-Allow MCP Tools**: When `mcp_servers` are configured, `ListMcpResources` and `ReadMcpResource` are automatically added to `allowed_tools`
- **Environment Variable Merging**: Runtime `mcp_env` overrides config-defined placeholders
- **Multi-Provider Support**: MCP works with Docker, Fly.io, and other providers
- **Tool Discovery**: Agents can list and read available MCP resources

**Available MCP Servers:**
- `@modelcontextprotocol/server-github` - GitHub API integration
- `@modelcontextprotocol/server-filesystem` - File system access
- `@modelcontextprotocol/server-postgres` - PostgreSQL integration
- Custom MCP servers (see [MCP docs](https://modelcontextprotocol.io))

---

## Resource Limits

Adjust based on your system and workload:

```yaml
resource_limits:
  cpu_quota: 200000    # CPU quota in microseconds (200000 = 2 CPUs)
  memory_limit: "4g"   # Memory limit (e.g., "4g", "512m")
  storage_limit: "10g" # Workspace storage limit
```

---

## Best Practices

1. **Start Simple:** Begin with single-agent configs, add complexity as needed
2. **Name Clearly:** Use descriptive IDs and names
3. **Limit Tools:** Only grant necessary tools for security
4. **Set Boundaries:** Use appropriate resource limits
5. **Document Intent:** Add comments explaining agent purpose
6. **Version Control:** Track configs in git for team sharing
7. **Test Thoroughly:** Verify configs work before deploying

---

## Examples

### Minimal Config
```yaml
id: simple-assistant
name: Simple Assistant
allowed_tools: ["Read", "Write"]
permission_mode: acceptEdits
```

### With MCP Servers
```yaml
id: github-bot
name: GitHub Bot
# Note: ListMcpResources and ReadMcpResource are auto-added
# No need to explicitly list mcp__* tools
allowed_tools: ["Read", "Write"]
mcp_servers:
  github:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: ${GITHUB_TOKEN}  # Placeholder
```

Launch with actual credentials:
```bash
curl -X POST http://localhost:8000/api/agents/launch \
  -d '{
    "api_key": "sk-ant-...",
    "config_id": "github-bot",
    "mcp_env": {"github": {"GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_..."}}
  }'
```

### Multi-Agent Team
```yaml
id: qa-team
name: QA Team
allowed_tools: ["Task"]
agents:
  tester:
    description: "Writing and running tests"
    prompt: "You write comprehensive test suites"
    tools: ["Read", "Write", "Bash"]
  reviewer:
    description: "Code review and quality checks"
    prompt: "You review code for quality and best practices"
    tools: ["Read", "Grep"]
```

---

## Troubleshooting

**Agent not launching:**
- Check config ID is valid (lowercase, no spaces)
- Verify all required fields are present
- Ensure tools list contains valid tool names

**Permission errors:**
- Adjust `permission_mode` to `acceptEdits`
- Grant additional tools if needed
- Check file paths are within allowed directories

**Resource issues:**
- Increase `cpu_quota` or `memory_limit`
- Reduce complexity or number of sub-agents
- Monitor container resource usage

---

## Contributing

To add new presets:

1. Create YAML file in `configs/presets/`
2. Follow existing format and conventions
3. Document purpose and use cases
4. Test thoroughly
5. Submit PR with example usage

---

For more information, see the main project documentation.
