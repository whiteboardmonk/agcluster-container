'use client';

import { useState } from 'react';
import { AgentForm } from '../../components/builder/AgentForm';
import { YAMLPreview } from '../../components/builder/YAMLPreview';
import { TestAgentModal } from '../../components/builder/TestAgentModal';
import { LoadConfigModal } from '../../components/builder/LoadConfigModal';
import { useRouter } from 'next/navigation';
import Navigation from '@/components/Navigation';
import { AgentConfig, createDefaultConfig } from '../../components/builder/types';

export default function BuilderPage() {
  const router = useRouter();
  const [config, setConfig] = useState<AgentConfig>(createDefaultConfig());

  const [showTest, setShowTest] = useState(false);
  const [showLoad, setShowLoad] = useState(false);
  const [saving, setSaving] = useState(false);

  const loadConfig = async (configId: string) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/configs/${configId}`);

      if (!res.ok) {
        throw new Error('Failed to load configuration');
      }

      const loadedConfig = await res.json();
      setConfig(loadedConfig);
    } catch (error) {
      console.error('Error loading config:', error);
      alert(`Failed to load configuration: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const saveConfig = async () => {
    if (!config.id || !config.name) {
      alert('Please provide both ID and Name for the agent configuration');
      return;
    }

    setSaving(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/configs/custom`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to save configuration');
      }

      alert('Configuration saved successfully!');
      router.push('/');
    } catch (error) {
      console.error('Error saving config:', error);
      alert(`Failed to save configuration: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="h-screen flex flex-col bg-black text-white">
      {/* Header */}
      <Navigation />

      {/* Page Title */}
      <div className="border-b border-gray-800/50 bg-gradient-to-b from-black via-gray-950/5 to-black">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="text-center mb-4">
            <h1 className="text-2xl md:text-3xl font-bold gradient-text mb-1">Agent Builder</h1>
            <p className="text-gray-400 text-sm">Design custom agent configurations with visual tools</p>
          </div>
          <div className="flex justify-center">
            <button
              onClick={() => setShowLoad(true)}
              className="px-4 py-2 bg-gradient-to-r from-gray-700 to-gray-800 hover:from-gray-800 hover:to-gray-900 rounded-lg transition-all"
            >
              Load Config
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Form Side */}
        <div className="w-1/2 p-6 overflow-y-auto">
          <AgentForm config={config} onChange={setConfig} />

          <div className="flex gap-3 mt-6">
            <button
              onClick={() => setShowTest(true)}
              disabled={!config.id || !config.name}
              className="px-6 py-3 bg-gradient-to-r from-gray-700 to-gray-800 hover:from-gray-800 hover:to-gray-900 disabled:opacity-50 disabled:cursor-not-allowed rounded transition-all"
            >
              Test Agent
            </button>
            <button
              onClick={saveConfig}
              disabled={!config.id || !config.name || saving}
              className="px-6 py-3 bg-gradient-to-r from-gray-700 to-gray-800 hover:from-gray-800 hover:to-gray-900 disabled:opacity-50 disabled:cursor-not-allowed rounded transition-all"
            >
              {saving ? 'Saving...' : 'Save Configuration'}
            </button>
          </div>
        </div>

        {/* YAML Preview Side */}
        <div className="w-1/2 border-l border-gray-800 p-6 overflow-y-auto">
          <YAMLPreview config={config} />
        </div>
      </div>

      {/* Test Modal */}
      {showTest && (
        <TestAgentModal
          config={config}
          onClose={() => setShowTest(false)}
        />
      )}

      {/* Load Modal */}
      {showLoad && (
        <LoadConfigModal
          onLoad={loadConfig}
          onClose={() => setShowLoad(false)}
        />
      )}
    </div>
  );
}
