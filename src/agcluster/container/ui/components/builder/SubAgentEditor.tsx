'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, Plus, Trash2, Users } from 'lucide-react';
import { AgentDefinition, createDefaultSubAgent } from './types';
import { ToolSelector } from './ToolSelector';

interface SubAgentEditorProps {
  agents: Record<string, AgentDefinition> | undefined;
  onChange: (agents: Record<string, AgentDefinition> | undefined) => void;
}

export function SubAgentEditor({ agents, onChange }: SubAgentEditorProps) {
  const [expandedAgents, setExpandedAgents] = useState<Set<string>>(new Set());

  const agentEntries = agents ? Object.entries(agents) : [];

  const handleAddAgent = () => {
    const newKey = `agent-${Date.now()}`;
    const newAgents = {
      ...(agents || {}),
      [newKey]: createDefaultSubAgent(),
    };
    onChange(newAgents);
    // Auto-expand the new agent
    setExpandedAgents(new Set([...expandedAgents, newKey]));
  };

  const handleRemoveAgent = (key: string) => {
    if (!agents) return;
    const newAgents = { ...agents };
    delete newAgents[key];
    onChange(Object.keys(newAgents).length > 0 ? newAgents : undefined);
    // Remove from expanded set
    const newExpanded = new Set(expandedAgents);
    newExpanded.delete(key);
    setExpandedAgents(newExpanded);
  };

  const handleUpdateAgent = (key: string, field: keyof AgentDefinition, value: any) => {
    if (!agents) return;
    onChange({
      ...agents,
      [key]: {
        ...agents[key],
        [field]: value,
      },
    });
  };

  const handleRenameAgent = (oldKey: string, newKey: string) => {
    if (!agents || !newKey || newKey === oldKey) return;

    // Check if new key already exists
    if (newKey in agents) {
      alert('A sub-agent with this name already exists');
      return;
    }

    const newAgents: Record<string, AgentDefinition> = {};
    for (const [k, v] of Object.entries(agents)) {
      if (k === oldKey) {
        newAgents[newKey] = v;
      } else {
        newAgents[k] = v;
      }
    }

    onChange(newAgents);

    // Update expanded state
    if (expandedAgents.has(oldKey)) {
      const newExpanded = new Set(expandedAgents);
      newExpanded.delete(oldKey);
      newExpanded.add(newKey);
      setExpandedAgents(newExpanded);
    }
  };

  const toggleExpanded = (key: string) => {
    const newExpanded = new Set(expandedAgents);
    if (newExpanded.has(key)) {
      newExpanded.delete(key);
    } else {
      newExpanded.add(key);
    }
    setExpandedAgents(newExpanded);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Users className="w-5 h-5" />
            Multi-Agent Configuration
          </h3>
          <p className="text-sm text-gray-400 mt-1">
            Define specialized sub-agents for team-based orchestration
          </p>
        </div>
        <button
          type="button"
          onClick={handleAddAgent}
          className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded transition-colors text-sm"
        >
          <Plus className="w-4 h-4" />
          Add Sub-Agent
        </button>
      </div>

      {agentEntries.length === 0 && (
        <div className="p-6 border-2 border-dashed border-gray-700 rounded-lg text-center">
          <Users className="w-12 h-12 mx-auto mb-3 text-gray-600" />
          <p className="text-gray-400 mb-4">No sub-agents defined yet</p>
          <p className="text-sm text-gray-500">
            Click &quot;Add Sub-Agent&quot; to create specialized agents that can be delegated tasks
          </p>
        </div>
      )}

      {/* Sub-agent Cards */}
      <div className="space-y-3">
        {agentEntries.map(([key, agent]) => {
          const isExpanded = expandedAgents.has(key);

          return (
            <div
              key={key}
              className="border border-gray-800 rounded-lg bg-gray-900/50 overflow-hidden"
            >
              {/* Card Header */}
              <div className="flex items-center justify-between p-4 bg-gray-800/50">
                <div className="flex items-center gap-3 flex-1">
                  <button
                    type="button"
                    onClick={() => toggleExpanded(key)}
                    className="p-1 hover:bg-gray-700 rounded transition-colors"
                  >
                    {isExpanded ? (
                      <ChevronDown className="w-5 h-5" />
                    ) : (
                      <ChevronRight className="w-5 h-5" />
                    )}
                  </button>

                  <input
                    type="text"
                    value={key}
                    onChange={(e) => handleRenameAgent(key, e.target.value)}
                    className="px-3 py-1 bg-gray-900 border border-gray-700 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm font-medium"
                    placeholder="agent-name"
                    pattern="[a-z0-9\-_]+"
                    title="Lowercase letters, numbers, hyphens, and underscores only"
                  />

                  {agent.model && (
                    <span className="px-2 py-1 bg-gray-800/40 border border-gray-700 rounded text-xs text-gray-300">
                      {agent.model}
                    </span>
                  )}
                </div>

                <button
                  type="button"
                  onClick={() => handleRemoveAgent(key)}
                  className="p-2 hover:bg-red-900/50 rounded transition-colors text-red-400"
                  title="Remove sub-agent"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              {/* Card Content */}
              {isExpanded && (
                <div className="p-4 space-y-4">
                  {/* Description */}
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Description (When to use this agent)
                    </label>
                    <textarea
                      value={agent.description}
                      onChange={(e) => handleUpdateAgent(key, 'description', e.target.value)}
                      placeholder="Frontend development with React, Next.js, and modern CSS frameworks..."
                      rows={2}
                      className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                    />
                  </div>

                  {/* System Prompt */}
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      System Prompt
                    </label>
                    <textarea
                      value={agent.prompt}
                      onChange={(e) => handleUpdateAgent(key, 'prompt', e.target.value)}
                      placeholder="You are a frontend specialist with expertise in..."
                      rows={6}
                      className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm font-mono"
                    />
                  </div>

                  {/* Tools */}
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Allowed Tools
                    </label>
                    <ToolSelector
                      selected={agent.tools || []}
                      onChange={(tools) => handleUpdateAgent(key, 'tools', tools)}
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Leave empty to inherit tools from parent agent
                    </p>
                  </div>

                  {/* Model */}
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Model
                    </label>
                    <select
                      value={agent.model || 'sonnet'}
                      onChange={(e) => handleUpdateAgent(key, 'model', e.target.value)}
                      className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                    >
                      <option value="sonnet">Sonnet (Balanced)</option>
                      <option value="opus">Opus (Most Capable)</option>
                      <option value="haiku">Haiku (Fast & Efficient)</option>
                      <option value="inherit">Inherit from Parent</option>
                    </select>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {agentEntries.length > 0 && (
        <div className="p-3 bg-gray-900/40 border border-gray-700/50 rounded text-xs text-gray-400">
          <strong className="text-gray-300">Multi-Agent Mode Active:</strong> The main agent can
          delegate tasks to these sub-agents using the Task tool. Make sure the main agent has the
          Task tool enabled.
        </div>
      )}
    </div>
  );
}
