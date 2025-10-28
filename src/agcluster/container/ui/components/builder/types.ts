/**
 * TypeScript types matching backend AgentConfig models
 * Mirrors: src/agcluster/container/models/agent_config.py
 */

// MCP Server Configuration Types

export interface McpStdioServerConfig {
  type?: 'stdio';
  command: string;
  args?: string[];
  env?: Record<string, string>;
}

export interface McpSseServerConfig {
  type: 'sse';
  url: string;
  headers?: Record<string, string>;
}

export interface McpHttpServerConfig {
  type: 'http';
  url: string;
  headers?: Record<string, string>;
}

export type McpServerConfig = McpStdioServerConfig | McpSseServerConfig | McpHttpServerConfig;

// System Prompt Configuration

export interface SystemPromptPreset {
  type: 'preset';
  preset: 'claude_code';
  append?: string;
}

export type SystemPrompt = string | SystemPromptPreset;

// Sub-agent Definition for Multi-Agent Orchestration

export interface AgentDefinition {
  description: string; // When to use this agent
  prompt: string; // Agent's system prompt
  tools?: string[]; // Allowed tools (inherits from parent if omitted)
  model?: 'sonnet' | 'opus' | 'haiku' | 'inherit';
}

// Resource Limits

export interface ResourceLimits {
  cpu_quota?: number; // CPU quota in microseconds (100000 = 1 CPU)
  memory_limit?: string; // e.g., '4g', '512m'
  storage_limit?: string; // e.g., '10g', '1g'
}

// Main Agent Configuration

export interface AgentConfig {
  // Metadata
  id: string;
  name: string;
  description?: string;
  version?: string;

  // Core Claude SDK options
  allowed_tools: string[];
  system_prompt?: SystemPrompt;
  mcp_servers?: Record<string, McpServerConfig>;
  permission_mode?: 'default' | 'acceptEdits' | 'plan' | 'bypassPermissions';

  // Multi-agent support
  agents?: Record<string, AgentDefinition>;

  // Resource limits
  resource_limits?: ResourceLimits;

  // Advanced options
  max_turns?: number;
  model?: string;
  cwd?: string;
  env?: Record<string, string>;
  setting_sources?: ('user' | 'project' | 'local')[];

  // Metadata (read-only from backend)
  created_at?: string;
  updated_at?: string;
}

// Available tools list

export const AVAILABLE_TOOLS = [
  'Bash',
  'Read',
  'Write',
  'Edit',
  'Grep',
  'Glob',
  'Task',
  'WebFetch',
  'WebSearch',
  'TodoWrite',
  'NotebookEdit',
  'BashOutput',
  'KillBash',
  'ExitPlanMode',
  'ListMcpResources',
  'ReadMcpResource',
] as const;

export type AvailableTool = typeof AVAILABLE_TOOLS[number];

// Tool metadata for UI

export interface ToolMetadata {
  name: string;
  description: string;
  category: 'file' | 'shell' | 'network' | 'agent' | 'mcp' | 'other';
}

export const TOOL_METADATA: Record<string, ToolMetadata> = {
  Bash: { name: 'Bash', description: 'Execute shell commands', category: 'shell' },
  Read: { name: 'Read', description: 'Read file contents', category: 'file' },
  Write: { name: 'Write', description: 'Write files', category: 'file' },
  Edit: { name: 'Edit', description: 'Edit existing files', category: 'file' },
  Grep: { name: 'Grep', description: 'Search file contents', category: 'file' },
  Glob: { name: 'Glob', description: 'Find files by pattern', category: 'file' },
  Task: { name: 'Task', description: 'Delegate to sub-agents', category: 'agent' },
  WebFetch: { name: 'WebFetch', description: 'Fetch web pages', category: 'network' },
  WebSearch: { name: 'WebSearch', description: 'Search the web', category: 'network' },
  TodoWrite: { name: 'TodoWrite', description: 'Manage task lists', category: 'other' },
  NotebookEdit: { name: 'NotebookEdit', description: 'Edit Jupyter notebooks', category: 'file' },
  BashOutput: { name: 'BashOutput', description: 'Get background bash output', category: 'shell' },
  KillBash: { name: 'KillBash', description: 'Kill background bash', category: 'shell' },
  ExitPlanMode: { name: 'ExitPlanMode', description: 'Exit planning mode', category: 'agent' },
  ListMcpResources: { name: 'ListMcpResources', description: 'List MCP resources', category: 'mcp' },
  ReadMcpResource: { name: 'ReadMcpResource', description: 'Read MCP resource', category: 'mcp' },
};

// Helper type: check if system prompt is preset

export function isSystemPromptPreset(prompt: SystemPrompt | undefined): prompt is SystemPromptPreset {
  return typeof prompt === 'object' && prompt !== null && 'type' in prompt && prompt.type === 'preset';
}

// Default config factory

export function createDefaultConfig(): AgentConfig {
  return {
    id: '',
    name: '',
    description: '',
    version: '1.0.0',
    allowed_tools: [],
    system_prompt: '',
    permission_mode: 'acceptEdits',
    resource_limits: {
      cpu_quota: 200000, // 2 CPUs
      memory_limit: '4g',
      storage_limit: '10g',
    },
    max_turns: 100,
    mcp_servers: {},
    env: {},
  };
}

// Default sub-agent factory

export function createDefaultSubAgent(): AgentDefinition {
  return {
    description: '',
    prompt: '',
    tools: [],
    model: 'sonnet',
  };
}

// Default MCP server factory

export function createDefaultMcpServer(type: 'stdio' | 'sse' | 'http' = 'stdio'): McpServerConfig {
  if (type === 'stdio') {
    return {
      type: 'stdio',
      command: '',
      args: [],
      env: {},
    };
  } else if (type === 'sse') {
    return {
      type: 'sse',
      url: '',
      headers: {},
    };
  } else {
    return {
      type: 'http',
      url: '',
      headers: {},
    };
  }
}
