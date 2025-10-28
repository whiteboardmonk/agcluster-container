'use client';

import { useMemo } from 'react';
import yaml from 'js-yaml';
import { Copy, Download } from 'lucide-react';
import { AgentConfig } from './types';

interface YAMLPreviewProps {
  config: AgentConfig;
}

// Clean config by removing undefined/empty fields for cleaner YAML
function cleanConfig(config: AgentConfig): any {
  const cleaned: any = {
    id: config.id,
    name: config.name,
  };

  if (config.description) cleaned.description = config.description;
  if (config.version) cleaned.version = config.version;

  // Always include allowed_tools
  cleaned.allowed_tools = config.allowed_tools;

  // Handle system_prompt (can be string or object)
  if (config.system_prompt) {
    if (typeof config.system_prompt === 'string') {
      if (config.system_prompt.trim()) {
        cleaned.system_prompt = config.system_prompt;
      }
    } else {
      // Structured prompt (preset)
      cleaned.system_prompt = {
        type: config.system_prompt.type,
        preset: config.system_prompt.preset,
      };
      if (config.system_prompt.append?.trim()) {
        cleaned.system_prompt.append = config.system_prompt.append;
      }
    }
  }

  if (config.permission_mode && config.permission_mode !== 'acceptEdits') {
    cleaned.permission_mode = config.permission_mode;
  }

  // Resource limits
  if (config.resource_limits) {
    cleaned.resource_limits = config.resource_limits;
  }

  if (config.max_turns) cleaned.max_turns = config.max_turns;

  // Multi-agent configuration
  if (config.agents && Object.keys(config.agents).length > 0) {
    cleaned.agents = {};
    for (const [key, agent] of Object.entries(config.agents)) {
      cleaned.agents[key] = {
        description: agent.description,
        prompt: agent.prompt,
      };
      if (agent.tools && agent.tools.length > 0) {
        cleaned.agents[key].tools = agent.tools;
      }
      if (agent.model) {
        cleaned.agents[key].model = agent.model;
      }
    }
  }

  // MCP servers
  if (config.mcp_servers && Object.keys(config.mcp_servers).length > 0) {
    cleaned.mcp_servers = config.mcp_servers;
  }

  // Advanced fields
  if (config.model) cleaned.model = config.model;
  if (config.cwd) cleaned.cwd = config.cwd;
  if (config.env && Object.keys(config.env).length > 0) {
    cleaned.env = config.env;
  }
  if (config.setting_sources && config.setting_sources.length > 0) {
    cleaned.setting_sources = config.setting_sources;
  }

  return cleaned;
}

export function YAMLPreview({ config }: YAMLPreviewProps) {
  const yamlString = useMemo(() => {
    try {
      const cleanedConfig = cleanConfig(config);
      return yaml.dump(cleanedConfig, {
        indent: 2,
        lineWidth: 80,
        noRefs: true,
        sortKeys: false, // Preserve order
      });
    } catch (error) {
      console.error('YAML generation error:', error);
      return '# Error generating YAML\n# Please check your configuration';
    }
  }, [config]);

  const copyYAML = async () => {
    try {
      await navigator.clipboard.writeText(yamlString);
      alert('YAML copied to clipboard!');
    } catch (error) {
      console.error('Failed to copy:', error);
      alert('Failed to copy YAML');
    }
  };

  const downloadYAML = () => {
    const blob = new Blob([yamlString], { type: 'text/yaml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${config.id || 'agent'}-config.yaml`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-xl font-semibold">YAML Preview</h3>
        <div className="flex gap-2">
          <button
            onClick={copyYAML}
            className="p-2 hover:bg-gray-800 rounded transition-colors"
            title="Copy YAML"
          >
            <Copy className="w-5 h-5" />
          </button>
          <button
            onClick={downloadYAML}
            disabled={!config.id}
            className="p-2 hover:bg-gray-800 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Download YAML"
          >
            <Download className="w-5 h-5" />
          </button>
        </div>
      </div>

      <div className="flex-1 bg-gray-950 rounded-lg overflow-auto">
        <pre className="p-4 text-sm font-mono text-gray-300">
          {yamlString}
        </pre>
      </div>

      {!config.id && (
        <p className="text-sm text-yellow-400 mt-4">
          ⚠️ Please provide an Agent ID to enable download
        </p>
      )}
    </div>
  );
}
