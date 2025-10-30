# Changelog

All notable changes to the AgCluster Container project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **MCP Server Support**: Model Context Protocol integration for external tools
  - GitHub MCP server preset (`github-code-review` configuration)
  - Auto-enable MCP tools (ListMcpResources, ReadMcpResource) when servers configured
  - Runtime credential injection via `mcp_env` parameter in launch requests
  - Environment variable merging in providers (Docker, Fly.io)
  - `mcp_env` field in LaunchRequest API model
- **GitHub Code Review Agent**: Specialized preset for automated PR reviews
  - System prompt optimized for code quality, security, performance analysis
  - MCP-based GitHub API integration for fetching PR details
  - Resource limits: 1 CPU, 2GB RAM, 5GB storage

### Fixed
- Critical bug: MCP servers defined in configs were never passed to containers
- MCP servers now properly included in AGENT_CONFIG_JSON environment variable
- Environment variable resolution for MCP server configurations

### Improved
- Provider abstraction layer now supports MCP server configs and credentials
- Configuration loading system passes MCP configs through full stack
- Session manager forwards MCP credentials to container manager
- Documentation updated with MCP usage examples and launch-time credentials

---

## [0.3.0] - 2025-01-28

### Added
- File upload functionality with drag-and-drop support in Web UI
- Upload button in chat input and file explorer
- Real-time directory path validation with debouncing (500ms)
- Multi-file upload with progress tracking and overwrite protection
- File size validation (max 50MB per file)
- `POST /api/files/{session_id}/upload` endpoint with `target_path` and `overwrite` params
- 9 end-to-end upload tests covering various scenarios
- Provider abstraction for file upload (Docker and Fly.io)

### Fixed
- Image preview authentication (using blob fetch + object URL pattern)
- React hooks ordering issue in FileViewer (error #300)
- Binary file handling (now shows download UI instead of errors)
- Upload and download button styling to match app theme (gray)
- Content-Type validation before JSON parsing
- 10 provider base/factory tests (implemented `upload_files` abstract method)

### Improved
- Binary file UI with clickable inline download links
- Clear messaging for binary files: "This is a binary file and cannot be previewed"
- Object URL cleanup to prevent memory leaks
- Error handling with detailed validation messages

### Security
- Path validation for upload target directories
- Filename sanitization (removes dangerous characters)
- Session ownership validation for all file operations

---

## [0.2.0] - 2025-01-XX

### 🎉 Major Features

#### Integrated Web UI Dashboard
- **NEW**: Full-featured Next.js 15 web interface with real-time monitoring
- Interactive dashboard for launching agents from preset configurations
- Real-time chat interface with Server-Sent Events (SSE) streaming
- Visual agent builder with YAML preview and export
- Session management UI for monitoring active containers
- File browser with syntax highlighting and ZIP download
- Tool execution panel showing real-time Bash commands and file operations
- Task tracking with TodoWrite integration

#### Agent Configuration System
- **NEW**: YAML-based agent configuration with 4 preset templates:
  - `code-assistant`: Full-stack development with comprehensive tooling
  - `research-agent`: Web research and information synthesis
  - `data-analysis`: Statistical analysis with Jupyter notebook support
  - `fullstack-team`: Multi-agent orchestration with specialized sub-agents
- Support for inline custom configurations via API
- Per-agent resource limits (CPU, memory, storage)
- MCP server integration for custom tool servers
- Multi-agent orchestration capabilities

#### Multi-Provider Support
- **NEW**: Provider abstraction layer for multi-platform deployment
- Docker provider (local development and self-hosted)
- Fly Machines provider (production deployments)
- HTTP/SSE communication protocol for universal compatibility
- Foundation for Cloudflare and Vercel providers

#### File Operations API
- **NEW**: Complete file management system for agent workspaces
- Browse workspace files in tree structure (`GET /api/files/{session_id}`)
- Preview files with syntax highlighting and image support
- Download individual files with proper MIME types
- Export entire workspace as ZIP archive
- Path traversal protection and zip bomb mitigation

### ✨ API Enhancements

#### New Endpoints
- `POST /api/agents/launch` - Launch agents from presets or inline configs
- `GET /api/agents/sessions` - List all active agent sessions
- `GET /api/agents/sessions/{session_id}` - Get session details
- `DELETE /api/agents/sessions/{session_id}` - Stop and remove session
- `POST /api/agents/{session_id}/chat` - Claude-native chat endpoint with SSE
- `GET /api/configs/` - List available agent configurations
- `GET /api/configs/{config_id}` - Get specific configuration details
- `GET /api/files/{session_id}` - Browse workspace files
- `GET /api/files/{session_id}/{path}` - Preview file content
- `POST /api/files/{session_id}/download` - Download workspace as ZIP

#### Breaking Changes
- **REMOVED**: `/chat/completions` OpenAI-compatible endpoint
  - **Migration**: Use `/api/agents/launch` + `/api/agents/{session_id}/chat` instead
  - New approach provides better session management and configuration control
- **CHANGED**: Session management now config-based instead of conversation-ID based
  - Sessions must be explicitly launched with a configuration
  - Auto-cleanup still active (30-minute idle timeout)

### 🔒 Security Improvements
- Path traversal protection for file operations
- Session-based authorization with API key verification
- CORS whitelist configuration
- Zip bomb protection (max 100 files, 100MB limit)
- Container security hardening maintained

### 🧪 Testing & CI/CD
- **NEW**: GitHub Actions CI/CD pipeline with 3 jobs:
  - Unit tests (Python 3.11, 3.12)
  - Integration tests with Docker setup
  - Linting (ruff, black)
- Comprehensive provider tests (Docker and Fly Machines)
- E2E test suite for Claude SDK native flows
- Builder configuration API tests
- Codecov integration for coverage reporting

### 📦 Dependencies
- **NEW**: Dependabot configuration for automated dependency updates
  - Python (pip) packages
  - GitHub Actions
  - Docker images
  - npm packages (UI)

### 📚 Documentation
- **NEW**: `CLAUDE.md` - Comprehensive guide for Claude Code
- **NEW**: `PROVIDERS.md` - Multi-provider architecture documentation (653 lines)
- **NEW**: `configs/README.md` - Complete configuration reference with examples
- **NEW**: `docs/providers/fly_machines.md` - Fly.io deployment guide
- **UPDATED**: Main README with Web UI documentation and new API reference
- **UPDATED**: UI README with implemented features
- **REMOVED**: `docs/architecture.md` (content consolidated into main README)
- **REMOVED**: `docs/quickstart.md` (merged into main README Quick Start)
- **REMOVED**: `examples/librechat/` (replaced by Web UI)

### 🏗️ Architecture Changes
- Session management redesigned for config-based launching
- Provider abstraction layer with factory pattern
- Configuration loading system with preset discovery
- File operations service with security controls
- WebSocket communication replaced with HTTP/SSE (partially)

### 🐛 Bug Fixes
- Fixed container readiness detection reliability
- Improved error handling in provider implementations
- Enhanced session cleanup logic
- Resolved race conditions in concurrent session creation

### 🔧 Internal Changes
- Code formatting with Black applied to all Python files
- Linting errors resolved with ruff
- Type hints improved (mypy validation removed from CI)
- Test structure reorganized (unit, integration, e2e)
- Provider implementations refactored for consistency

---

## [0.1.0] - 2025-01-10

### Initial Release
- Basic OpenAI-compatible API wrapper for Claude Agent SDK
- Docker-based container isolation
- WebSocket communication between API and agents
- Session management with conversation IDs
- Auto-cleanup of idle sessions (30-min timeout)
- Security hardening (dropped capabilities, resource limits)
- Initial test suite (unit and integration tests)
- LibreChat integration support

[0.2.0]: https://github.com/whiteboardmonk/agcluster-container/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/whiteboardmonk/agcluster-container/releases/tag/v0.1.0
