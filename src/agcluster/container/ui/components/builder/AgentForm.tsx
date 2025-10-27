'use client';

import { AgentConfig } from './types';
import { ToolSelector } from './ToolSelector';
import { SystemPromptEditor } from './SystemPromptEditor';
import { SubAgentEditor } from './SubAgentEditor';
import { MCPServerEditor } from './MCPServerEditor';
import { AdvancedFields } from './AdvancedFields';

interface AgentFormProps {
  config: AgentConfig;
  onChange: (config: AgentConfig) => void;
}

export function AgentForm({ config, onChange }: AgentFormProps) {
  const updateField = <K extends keyof AgentConfig>(field: K, value: AgentConfig[K]) => {
    onChange({ ...config, [field]: value });
  };

  const updateResourceLimit = (field: string, value: string | number) => {
    onChange({
      ...config,
      resource_limits: {
        ...config.resource_limits,
        [field]: value,
      },
    });
  };

  const handleAdvancedFieldChange = (field: string, value: any) => {
    onChange({
      ...config,
      [field]: value,
    });
  };

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Basic Information</h2>

      {/* ID */}
      <div>
        <label className="block text-sm font-medium mb-2">
          Agent ID <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={config.id}
          onChange={(e) => updateField('id', e.target.value)}
          placeholder="e.g., my-custom-agent"
          className="w-full px-4 py-2 bg-gray-900 border border-gray-800 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          pattern="[a-z0-9\-_]+"
          title="Lowercase letters, numbers, hyphens, and underscores only"
        />
        <p className="text-xs text-gray-500 mt-1">
          Unique identifier (lowercase, hyphens/underscores allowed)
        </p>
      </div>

      {/* Name */}
      <div>
        <label className="block text-sm font-medium mb-2">
          Agent Name <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={config.name}
          onChange={(e) => updateField('name', e.target.value)}
          placeholder="e.g., My Custom Agent"
          className="w-full px-4 py-2 bg-gray-900 border border-gray-800 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <p className="text-xs text-gray-500 mt-1">
          Display name shown in the dashboard
        </p>
      </div>

      {/* Description */}
      <div>
        <label className="block text-sm font-medium mb-2">Description</label>
        <textarea
          value={config.description || ''}
          onChange={(e) => updateField('description', e.target.value || undefined)}
          placeholder="Brief description of what this agent does..."
          rows={3}
          className="w-full px-4 py-2 bg-gray-900 border border-gray-800 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* System Prompt - New Editor */}
      <SystemPromptEditor
        value={config.system_prompt}
        onChange={(value) => updateField('system_prompt', value)}
      />

      {/* Tools */}
      <div>
        <h3 className="text-lg font-semibold mb-3">Available Tools</h3>
        <ToolSelector
          selected={config.allowed_tools}
          onChange={(tools) => updateField('allowed_tools', tools)}
        />
      </div>

      {/* Permission Mode */}
      <div>
        <label className="block text-sm font-medium mb-2">Permission Mode</label>
        <select
          value={config.permission_mode || 'acceptEdits'}
          onChange={(e) => updateField('permission_mode', e.target.value as any)}
          className="w-full px-4 py-2 bg-gray-900 border border-gray-800 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="default">Default</option>
          <option value="acceptEdits">Accept Edits (Auto-approve file changes)</option>
          <option value="plan">Plan Mode (Review before execution)</option>
          <option value="bypassPermissions">Bypass Permissions</option>
        </select>
        <p className="text-xs text-gray-500 mt-1">
          Control how the agent handles file modifications and tool execution
        </p>
      </div>

      {/* Resource Limits */}
      <div>
        <h3 className="text-lg font-semibold mb-3">Resource Limits</h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">CPU Quota</label>
            <div className="flex items-center gap-3">
              <input
                type="number"
                value={config.resource_limits?.cpu_quota || 200000}
                onChange={(e) => updateResourceLimit('cpu_quota', parseInt(e.target.value))}
                min="50000"
                max="400000"
                step="50000"
                className="flex-1 px-4 py-2 bg-gray-900 border border-gray-800 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-400">
                ({((config.resource_limits?.cpu_quota || 200000) / 100000).toFixed(1)} CPUs)
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              100000 = 1 CPU. Typical: 200000 (2 CPUs)
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Memory Limit</label>
            <select
              value={config.resource_limits?.memory_limit || '4g'}
              onChange={(e) => updateResourceLimit('memory_limit', e.target.value)}
              className="w-full px-4 py-2 bg-gray-900 border border-gray-800 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="2g">2 GB</option>
              <option value="4g">4 GB</option>
              <option value="8g">8 GB</option>
              <option value="16g">16 GB</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Storage Limit</label>
            <select
              value={config.resource_limits?.storage_limit || '10g'}
              onChange={(e) => updateResourceLimit('storage_limit', e.target.value)}
              className="w-full px-4 py-2 bg-gray-900 border border-gray-800 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="5g">5 GB</option>
              <option value="10g">10 GB</option>
              <option value="20g">20 GB</option>
              <option value="50g">50 GB</option>
            </select>
          </div>
        </div>
      </div>

      {/* Max Turns */}
      <div>
        <label className="block text-sm font-medium mb-2">Maximum Turns</label>
        <input
          type="number"
          value={config.max_turns || 100}
          onChange={(e) => updateField('max_turns', parseInt(e.target.value) || undefined)}
          min="10"
          max="500"
          className="w-full px-4 py-2 bg-gray-900 border border-gray-800 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <p className="text-xs text-gray-500 mt-1">
          Maximum conversation turns before auto-termination
        </p>
      </div>

      {/* Multi-Agent Section - Progressive Disclosure */}
      {(config.agents && Object.keys(config.agents).length > 0) || (
        <div className="pt-6 border-t border-gray-800">
          <SubAgentEditor
            agents={config.agents}
            onChange={(agents) => updateField('agents', agents)}
          />
        </div>
      )}

      {!config.agents && (
        <div className="pt-6 border-t border-gray-800">
          <button
            type="button"
            onClick={() => updateField('agents', {})}
            className="w-full p-4 border-2 border-dashed border-gray-700 rounded-lg hover:border-gray-500 hover:bg-gray-900/30 transition-colors text-gray-400 hover:text-gray-300"
          >
            + Enable Multi-Agent Configuration
          </button>
        </div>
      )}

      {/* Show SubAgentEditor if agents exist */}
      {config.agents && Object.keys(config.agents).length > 0 && (
        <div className="pt-6 border-t border-gray-800">
          <SubAgentEditor
            agents={config.agents}
            onChange={(agents) => updateField('agents', agents)}
          />
        </div>
      )}

      {/* MCP Servers Section - Progressive Disclosure */}
      {!config.mcp_servers && (
        <div className="pt-6 border-t border-gray-800">
          <button
            type="button"
            onClick={() => updateField('mcp_servers', {})}
            className="w-full p-4 border-2 border-dashed border-gray-700 rounded-lg hover:border-gray-600 hover:bg-gray-800/20 transition-colors text-gray-400 hover:text-white"
          >
            + Add MCP Servers
          </button>
        </div>
      )}

      {config.mcp_servers && Object.keys(config.mcp_servers).length >= 0 && (
        <div className="pt-6 border-t border-gray-800">
          <MCPServerEditor
            servers={config.mcp_servers}
            onChange={(servers) => updateField('mcp_servers', servers)}
          />
        </div>
      )}

      {/* Advanced Fields - Collapsible */}
      <div className="pt-6 border-t border-gray-800">
        <AdvancedFields
          version={config.version}
          model={config.model}
          cwd={config.cwd}
          env={config.env}
          settingSources={config.setting_sources}
          onChange={handleAdvancedFieldChange}
        />
      </div>
    </div>
  );
}
