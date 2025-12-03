'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, Plus, Trash2, Server } from 'lucide-react';
import { McpServerConfig, createDefaultMcpServer } from './types';

interface MCPServerEditorProps {
  servers: Record<string, McpServerConfig> | undefined;
  onChange: (servers: Record<string, McpServerConfig> | undefined) => void;
}

export function MCPServerEditor({ servers, onChange }: MCPServerEditorProps) {
  const [expandedServers, setExpandedServers] = useState<Set<string>>(new Set());

  const serverEntries = servers ? Object.entries(servers) : [];

  const handleAddServer = () => {
    const newKey = `server-${Date.now()}`;
    const newServers = {
      ...(servers || {}),
      [newKey]: createDefaultMcpServer('stdio'),
    };
    onChange(newServers);
    setExpandedServers(new Set([...expandedServers, newKey]));
  };

  const handleRemoveServer = (key: string) => {
    if (!servers) return;
    const newServers = { ...servers };
    delete newServers[key];
    onChange(Object.keys(newServers).length > 0 ? newServers : undefined);
  };

  const handleRenameServer = (oldKey: string, newKey: string) => {
    if (!servers || !newKey || newKey === oldKey) return;
    if (newKey in servers) {
      alert('A server with this name already exists');
      return;
    }

    const newServers: Record<string, McpServerConfig> = {};
    for (const [k, v] of Object.entries(servers)) {
      newServers[k === oldKey ? newKey : k] = v;
    }
    onChange(newServers);
  };

  const handleUpdateServer = (key: string, server: McpServerConfig) => {
    if (!servers) return;
    onChange({ ...servers, [key]: server });
  };

  const toggleExpanded = (key: string) => {
    const newExpanded = new Set(expandedServers);
    newExpanded.has(key) ? newExpanded.delete(key) : newExpanded.add(key);
    setExpandedServers(newExpanded);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Server className="w-5 h-5" />
            MCP Servers
          </h3>
          <p className="text-sm text-gray-400 mt-1">
            Configure Model Context Protocol servers for external tool integrations
          </p>
        </div>
        <button
          type="button"
          onClick={handleAddServer}
          className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded transition-colors text-sm"
        >
          <Plus className="w-4 h-4" />
          Add MCP Server
        </button>
      </div>

      {serverEntries.length === 0 && (
        <div className="p-6 border-2 border-dashed border-gray-700 rounded-lg text-center">
          <Server className="w-12 h-12 mx-auto mb-3 text-gray-600" />
          <p className="text-gray-400 mb-2">No MCP servers configured</p>
          <p className="text-sm text-gray-500">
            MCP servers provide additional tools and resources beyond built-in capabilities
          </p>
        </div>
      )}

      <div className="space-y-3">
        {serverEntries.map(([key, server]) => {
          const isExpanded = expandedServers.has(key);
          const serverType = server.type || 'stdio';

          return (
            <div key={key} className="border border-gray-800 rounded-lg bg-gray-900/50">
              <div className="flex items-center justify-between p-4 bg-gray-800/50">
                <div className="flex items-center gap-3 flex-1">
                  <button
                    type="button"
                    onClick={() => toggleExpanded(key)}
                    className="p-1 hover:bg-gray-700 rounded"
                  >
                    {isExpanded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                  </button>
                  <input
                    type="text"
                    value={key}
                    onChange={(e) => handleRenameServer(key, e.target.value)}
                    className="px-3 py-1 bg-gray-900 border border-gray-700 rounded focus:ring-2 focus:ring-green-500 text-sm font-medium"
                  />
                  <span className="px-2 py-1 bg-green-900/30 border border-green-500/30 rounded text-xs text-green-300">
                    {serverType}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => handleRemoveServer(key)}
                  className="p-2 hover:bg-red-900/50 rounded text-red-400"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              {isExpanded && (
                <div className="p-4 space-y-3">
                  <div>
                    <label className="block text-sm font-medium mb-2">Transport Type</label>
                    <select
                      value={serverType}
                      onChange={(e) => {
                        const type = e.target.value as 'stdio' | 'sse' | 'http';
                        handleUpdateServer(key, createDefaultMcpServer(type));
                      }}
                      className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded focus:ring-2 focus:ring-green-500 text-sm"
                    >
                      <option value="stdio">STDIO (Standard I/O)</option>
                      <option value="sse">SSE (Server-Sent Events)</option>
                      <option value="http">HTTP</option>
                    </select>
                  </div>

                  {serverType === 'stdio' && 'command' in server && (
                    <>
                      <div>
                        <label className="block text-sm font-medium mb-2">Command</label>
                        <input
                          type="text"
                          value={server.command}
                          onChange={(e) => handleUpdateServer(key, { ...server, command: e.target.value })}
                          className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded focus:ring-2 focus:ring-green-500 text-sm font-mono"
                          placeholder="node"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-2">Arguments (comma-separated)</label>
                        <input
                          type="text"
                          value={(server.args || []).join(', ')}
                          onChange={(e) => handleUpdateServer(key, { ...server, args: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })}
                          className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded focus:ring-2 focus:ring-green-500 text-sm font-mono"
                          placeholder="./server.js, --port=3000"
                        />
                      </div>
                    </>
                  )}

                  {(serverType === 'sse' || serverType === 'http') && 'url' in server && (
                    <div>
                      <label className="block text-sm font-medium mb-2">URL</label>
                      <input
                        type="url"
                        value={server.url}
                        onChange={(e) => handleUpdateServer(key, { ...server, url: e.target.value })}
                        className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded focus:ring-2 focus:ring-green-500 text-sm font-mono"
                        placeholder="http://localhost:3000/mcp"
                      />
                    </div>
                  )}

                  {/* Environment Variables */}
                  <div>
                    <label className="block text-sm font-medium mb-2">Environment Variables</label>
                    <p className="text-xs text-gray-500 mb-2">
                      Use placeholders like {'${GITHUB_TOKEN}'} for runtime credentials
                    </p>
                    <textarea
                      value={(server.type !== 'sse' && server.type !== 'http' && server.env) ? Object.entries(server.env).map(([k, v]) => `${k}=${v}`).join('\n') : ''}
                      onChange={(e) => {
                        const env: Record<string, string> = {};
                        e.target.value.split('\n').forEach(line => {
                          const [k, ...vParts] = line.split('=');
                          if (k && vParts.length > 0) {
                            env[k.trim()] = vParts.join('=').trim();
                          }
                        });
                        // Only update env for stdio servers (type undefined or 'stdio')
                        if (server.type !== 'sse' && server.type !== 'http') {
                          handleUpdateServer(key, { ...server, env: Object.keys(env).length > 0 ? env : undefined } as McpServerConfig);
                        }
                      }}
                      rows={3}
                      className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded focus:ring-2 focus:ring-green-500 text-sm font-mono"
                      placeholder="GITHUB_PERSONAL_ACCESS_TOKEN=${GITHUB_TOKEN}&#10;API_KEY=${API_KEY}"
                    />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
