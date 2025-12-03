'use client';

import { useState, useEffect } from 'react';
import { X, Key, AlertCircle } from 'lucide-react';

interface McpCredentialsModalProps {
  isOpen: boolean;
  onClose: () => void;
  mcpServers: Record<string, any>;
  onSubmit: (credentials: Record<string, Record<string, string>>) => void;
}

export function McpCredentialsModal({
  isOpen,
  onClose,
  mcpServers,
  onSubmit,
}: McpCredentialsModalProps) {
  const [credentials, setCredentials] = useState<Record<string, Record<string, string>>>({});
  const [errors, setErrors] = useState<string[]>([]);

  // Extract required env vars from MCP servers
  useEffect(() => {
    if (isOpen && mcpServers) {
      const initialCreds: Record<string, Record<string, string>> = {};
      Object.entries(mcpServers).forEach(([serverName, serverConfig]: [string, any]) => {
        if (serverConfig.env) {
          initialCreds[serverName] = {};
          Object.keys(serverConfig.env).forEach((envKey) => {
            initialCreds[serverName][envKey] = '';
          });
        }
      });
      setCredentials(initialCreds);
      setErrors([]);
    }
  }, [isOpen, mcpServers]);

  const handleSubmit = () => {
    const newErrors: string[] = [];

    // Validate all required fields are filled
    Object.entries(credentials).forEach(([serverName, serverCreds]) => {
      Object.entries(serverCreds).forEach(([key, value]) => {
        if (!value || value.trim() === '') {
          newErrors.push(`${serverName}: ${key} is required`);
        }
      });
    });

    if (newErrors.length > 0) {
      setErrors(newErrors);
      return;
    }

    onSubmit(credentials);
  };

  const handleSkip = () => {
    // Submit empty credentials (will likely fail at runtime, but let user try)
    onSubmit({});
  };

  if (!isOpen) return null;

  const hasAnyMcpServers = Object.keys(mcpServers || {}).length > 0;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="glass rounded-xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-800">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-500/20">
              <Key className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold">MCP Server Credentials</h2>
              <p className="text-sm text-gray-400">
                This agent uses MCP servers that require authentication
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {!hasAnyMcpServers && (
            <div className="text-center py-8">
              <p className="text-gray-400">No MCP servers configured for this agent</p>
            </div>
          )}

          {errors.length > 0 && (
            <div className="p-4 bg-red-500/10 border border-red-500/50 rounded-lg">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-red-400 mb-1">Missing required credentials:</p>
                  <ul className="text-sm text-red-300 space-y-1">
                    {errors.map((error, i) => (
                      <li key={i}>• {error}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {Object.entries(credentials).map(([serverName, serverCreds]) => (
            <div key={serverName} className="glass rounded-lg p-4 border border-gray-800">
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <span className="px-2 py-1 bg-blue-500/20 rounded text-sm text-blue-300">
                  {serverName}
                </span>
              </h3>
              <div className="space-y-3">
                {Object.entries(serverCreds).map(([key, value]) => {
                  const placeholder = mcpServers[serverName]?.env?.[key];
                  const isPlaceholder = typeof placeholder === 'string' && placeholder.startsWith('${');

                  return (
                    <div key={key}>
                      <label className="block text-sm font-medium mb-2">
                        {key}
                        {isPlaceholder && (
                          <span className="text-gray-500 ml-2">
                            (expects: {placeholder})
                          </span>
                        )}
                      </label>
                      <input
                        type="password"
                        value={value}
                        onChange={(e) => {
                          setCredentials({
                            ...credentials,
                            [serverName]: {
                              ...credentials[serverName],
                              [key]: e.target.value,
                            },
                          });
                          // Clear errors when user starts typing
                          setErrors([]);
                        }}
                        className="w-full px-4 py-2 bg-gray-900 border border-gray-800 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm font-mono"
                        placeholder={isPlaceholder ? placeholder.slice(2, -1) : key}
                      />
                    </div>
                  );
                })}
              </div>
            </div>
          ))}

          <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
            <p className="text-sm text-blue-300">
              <strong>💡 Tip:</strong> These credentials are passed to the container at launch
              time and are never stored. Each session requires its own credentials.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-800">
          <button
            onClick={handleSkip}
            className="px-4 py-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
          >
            Skip (Launch Without Credentials)
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors font-medium"
          >
            Launch Agent
          </button>
        </div>
      </div>
    </div>
  );
}
