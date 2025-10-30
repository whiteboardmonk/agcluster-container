/**
 * AgCluster API client
 *
 * Provides typed wrappers for all AgCluster API endpoints
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface AgentConfig {
  id: string;
  name: string;
  description: string;
  version?: string;
  system_prompt?: string;
  allowed_tools?: string[];
  permission_mode?: 'acceptEdits' | 'confirm';
  resource_limits?: {
    cpu_quota?: number;
    memory_limit?: string;
    storage_limit?: string;
  };
  max_turns?: number;
  agents?: Record<string, unknown>;
  mcp_servers?: Record<string, unknown>;
}

export interface ConfigInfo {
  id: string;
  name: string;
  description: string;
  allowed_tools: string[];
  has_mcp_servers: boolean;
  has_sub_agents: boolean;
  permission_mode: string;
}

export interface LaunchAgentRequest {
  api_key: string;
  config_id?: string;
  config?: AgentConfig;
  mcp_env?: Record<string, Record<string, string>>;
}

export interface LaunchAgentResponse {
  session_id: string;
  agent_id: string;
  container_id: string;
  config: AgentConfig;
}

export interface SessionInfo {
  session_id: string;
  container_id: string;
  created_at: string;
  last_active: string;
  config: AgentConfig;
  status: string;
}

/**
 * List all available agent configurations
 */
export async function listConfigs(): Promise<ConfigInfo[]> {
  const res = await fetch(`${API_BASE}/api/configs/`);
  if (!res.ok) throw new Error('Failed to fetch configs');
  const data = await res.json();
  return data.configs || [];
}

/**
 * Get a specific agent configuration by ID
 */
export async function getConfig(configId: string): Promise<AgentConfig> {
  const res = await fetch(`${API_BASE}/api/configs/${configId}`);
  if (!res.ok) throw new Error(`Failed to fetch config: ${configId}`);
  return res.json();
}

/**
 * Launch a new agent with config
 */
export async function launchAgent(
  request: LaunchAgentRequest
): Promise<LaunchAgentResponse> {
  const res = await fetch(`${API_BASE}/api/agents/launch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!res.ok) throw new Error('Failed to launch agent');
  return res.json();
}

/**
 * List all active sessions
 */
export async function listSessions(): Promise<SessionInfo[]> {
  const res = await fetch(`${API_BASE}/api/agents/sessions`);
  if (!res.ok) throw new Error('Failed to fetch sessions');
  const data = await res.json();
  return data.sessions || [];
}

/**
 * Get session details
 */
export async function getSession(sessionId: string): Promise<SessionInfo> {
  const res = await fetch(`${API_BASE}/api/agents/sessions/${sessionId}`);
  if (!res.ok) throw new Error(`Failed to fetch session: ${sessionId}`);
  return res.json();
}

/**
 * Terminate a session
 */
export async function terminateSession(sessionId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/agents/sessions/${sessionId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`Failed to terminate session: ${sessionId}`);
}

/**
 * Upload files to a session's workspace
 */
export interface UploadFilesRequest {
  sessionId: string;
  files: FileList | File[];
  targetPath?: string;
  overwrite?: boolean;
  apiKey: string;
}

export interface UploadFilesResponse {
  session_id: string;
  target_path: string;
  uploaded: string[];
  total_files: number;
  total_size_bytes: number;
}

export async function uploadFiles({
  sessionId,
  files,
  targetPath = '',
  overwrite = false,
  apiKey,
}: UploadFilesRequest): Promise<UploadFilesResponse> {
  const formData = new FormData();

  // Add files to form data
  Array.from(files).forEach((file) => {
    formData.append('files', file);
  });

  // Build URL with query parameters
  const url = new URL(`${API_BASE}/api/files/${sessionId}/upload`);
  if (targetPath) {
    url.searchParams.set('target_path', targetPath);
  }
  url.searchParams.set('overwrite', String(overwrite));

  const res = await fetch(url.toString(), {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
    },
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(error.detail || 'Failed to upload files');
  }

  return res.json();
}
