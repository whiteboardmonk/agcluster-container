'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, Settings, Plus, X } from 'lucide-react';

interface AdvancedFieldsProps {
  version?: string;
  model?: string;
  cwd?: string;
  env?: Record<string, string>;
  settingSources?: ('user' | 'project' | 'local')[];
  onChange: (field: string, value: any) => void;
}

export function AdvancedFields({
  version,
  model,
  cwd,
  env,
  settingSources,
  onChange,
}: AdvancedFieldsProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const envEntries = env ? Object.entries(env) : [];

  const handleAddEnvVar = () => {
    const newKey = `VAR_${Date.now()}`;
    onChange('env', { ...(env || {}), [newKey]: '' });
  };

  const handleRemoveEnvVar = (key: string) => {
    if (!env) return;
    const newEnv = { ...env };
    delete newEnv[key];
    onChange('env', Object.keys(newEnv).length > 0 ? newEnv : {});
  };

  const handleUpdateEnvKey = (oldKey: string, newKey: string) => {
    if (!env || !newKey || newKey === oldKey) return;
    const newEnv: Record<string, string> = {};
    for (const [k, v] of Object.entries(env)) {
      newEnv[k === oldKey ? newKey : k] = v;
    }
    onChange('env', newEnv);
  };

  const handleUpdateEnvValue = (key: string, value: string) => {
    if (!env) return;
    onChange('env', { ...env, [key]: value });
  };

  return (
    <div className="border border-gray-800 rounded-lg bg-gray-900/30">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-gray-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          {isExpanded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
          <Settings className="w-5 h-5" />
          <span className="font-semibold">Advanced Configuration</span>
        </div>
        <span className="text-xs text-gray-500">Optional fields</span>
      </button>

      {isExpanded && (
        <div className="p-4 pt-0 space-y-4">
          {/* Version */}
          <div>
            <label className="block text-sm font-medium mb-2">Version</label>
            <input
              type="text"
              value={version || ''}
              onChange={(e) => onChange('version', e.target.value || undefined)}
              placeholder="1.0.0"
              className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">Semantic version for this configuration</p>
          </div>

          {/* Model */}
          <div>
            <label className="block text-sm font-medium mb-2">Model Override</label>
            <input
              type="text"
              value={model || ''}
              onChange={(e) => onChange('model', e.target.value || undefined)}
              placeholder="claude-sonnet-4.5"
              className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm font-mono"
            />
            <p className="text-xs text-gray-500 mt-1">Specific Claude model to use</p>
          </div>

          {/* Working Directory */}
          <div>
            <label className="block text-sm font-medium mb-2">Working Directory</label>
            <input
              type="text"
              value={cwd || ''}
              onChange={(e) => onChange('cwd', e.target.value || undefined)}
              placeholder="/workspace"
              className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm font-mono"
            />
            <p className="text-xs text-gray-500 mt-1">Base working directory for agent operations</p>
          </div>

          {/* Environment Variables */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium">Environment Variables</label>
              <button
                type="button"
                onClick={handleAddEnvVar}
                className="flex items-center gap-1 px-2 py-1 text-xs bg-gray-800 hover:bg-gray-700 rounded"
              >
                <Plus className="w-3 h-3" />
                Add
              </button>
            </div>

            {envEntries.length === 0 ? (
              <div className="p-3 border border-dashed border-gray-700 rounded text-xs text-gray-500 text-center">
                No environment variables defined
              </div>
            ) : (
              <div className="space-y-2">
                {envEntries.map(([key, value]) => (
                  <div key={key} className="flex gap-2">
                    <input
                      type="text"
                      value={key}
                      onChange={(e) => handleUpdateEnvKey(key, e.target.value)}
                      placeholder="VARIABLE_NAME"
                      className="flex-1 px-3 py-2 bg-gray-900 border border-gray-800 rounded focus:ring-2 focus:ring-blue-500 text-sm font-mono"
                    />
                    <input
                      type="text"
                      value={value}
                      onChange={(e) => handleUpdateEnvValue(key, e.target.value)}
                      placeholder="value"
                      className="flex-1 px-3 py-2 bg-gray-900 border border-gray-800 rounded focus:ring-2 focus:ring-blue-500 text-sm font-mono"
                    />
                    <button
                      type="button"
                      onClick={() => handleRemoveEnvVar(key)}
                      className="p-2 hover:bg-red-900/50 rounded text-red-400"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Setting Sources */}
          <div>
            <label className="block text-sm font-medium mb-2">Setting Sources</label>
            <div className="space-y-2">
              {['user', 'project', 'local'].map((source) => (
                <label key={source} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={settingSources?.includes(source as any) || false}
                    onChange={(e) => {
                      const current = settingSources || [];
                      const updated = e.target.checked
                        ? [...current, source as 'user' | 'project' | 'local']
                        : current.filter((s) => s !== source);
                      onChange('setting_sources', updated.length > 0 ? updated : undefined);
                    }}
                    className="w-4 h-4 rounded border-gray-700 bg-gray-900 focus:ring-2 focus:ring-blue-500"
                  />
                  <span className="capitalize">{source}</span>
                </label>
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-1">Filesystem settings to load</p>
          </div>
        </div>
      )}
    </div>
  );
}
