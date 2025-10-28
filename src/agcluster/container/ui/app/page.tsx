'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Code2, Search, BarChart3, Rocket, Plus } from 'lucide-react';
import { listConfigs, launchAgent, type ConfigInfo } from '@/lib/api-client';
import Navigation from '@/components/Navigation';

const PRESET_ICONS = {
  'code-assistant': Code2,
  'research-agent': Search,
  'data-analysis': BarChart3,
  'fullstack-team': Rocket,
} as const;

export default function DashboardPage() {
  const router = useRouter();
  const [configs, setConfigs] = useState<ConfigInfo[]>([]);
  const [apiKey, setApiKey] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [backendConnected, setBackendConnected] = useState(false);

  // Load API key from localStorage
  useEffect(() => {
    const savedKey = localStorage.getItem('anthropic_api_key');
    if (savedKey) setApiKey(savedKey);
  }, []);

  // Fetch available configs from backend
  useEffect(() => {
    listConfigs()
      .then((fetchedConfigs) => {
        setConfigs(fetchedConfigs);
        setBackendConnected(true);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to connect to AgCluster API:', err.message);
        setError('Cannot connect to AgCluster API. Make sure the backend is running on http://localhost:8000');
        setBackendConnected(false);
        setLoading(false);
      });
  }, []);

  const handleLaunchAgent = async (configId: string) => {
    if (!apiKey) {
      setError('Please enter your Anthropic API key');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // Save API key
      localStorage.setItem('anthropic_api_key', apiKey);

      // Launch agent with config
      const response = await launchAgent({
        api_key: apiKey,
        config_id: configId,
      });

      // Navigate to chat with session ID
      router.push(`/chat/${response.session_id}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to launch agent';
      setError(message);
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Header */}
      <Navigation />

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Hero Section */}
        <div className="text-center mb-12 animate-fade-in">
          <h2 className="text-2xl md:text-3xl font-bold mb-2 gradient-text">
            Launch Your Agent
          </h2>
          <p className="text-gray-400 text-sm max-w-2xl mx-auto mb-8">
            Choose from specialized agent configurations or build your own
          </p>

          {/* API Key Input */}
          <div className="max-w-md mx-auto">
            <input
              type="password"
              placeholder="Enter your Anthropic API Key"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="w-full px-4 py-3 rounded-lg glass focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
            />
            <p className="text-xs text-gray-500 mt-2">Your API key is stored locally and never sent to our servers</p>
          </div>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500 mb-4"></div>
            <p className="text-gray-400">Connecting to AgCluster API...</p>
          </div>
        )}

        {/* Backend Connection Error */}
        {!loading && !backendConnected && (
          <div className="max-w-2xl mx-auto">
            <div className="glass rounded-xl p-8 border-2 border-red-500/50">
              <div className="text-center mb-6">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-500/20 mb-4">
                  <svg className="w-8 h-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-red-400 mb-2">Backend Not Running</h3>
                <p className="text-gray-400 mb-6">{error}</p>
              </div>

              <div className="space-y-4 text-sm text-gray-300">
                <p className="font-semibold">To start the AgCluster backend:</p>
                <div className="glass rounded-lg p-4 bg-gray-900/50 font-mono text-xs">
                  <div className="mb-2 text-gray-400"># From agcluster-container root directory:</div>
                  <div>python -m uvicorn agcluster.container.api.main:app --host 0.0.0.0 --port 8000</div>
                </div>
                <p className="text-gray-400 text-xs pt-2">
                  Or use Docker: <code className="bg-gray-800 px-2 py-1 rounded">docker compose up -d</code>
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Error Message (for other errors) */}
        {!loading && backendConnected && error && (
          <div className="mb-8 p-4 rounded-lg bg-red-500/10 border border-red-500/50 text-red-400">
            {error}
          </div>
        )}

        {/* Agent Presets Grid */}
        {!loading && backendConnected && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
            {configs.map((config) => {
            const Icon = PRESET_ICONS[config.id as keyof typeof PRESET_ICONS] || Code2;

            return (
              <button
                key={config.id}
                onClick={() => handleLaunchAgent(config.id)}
                disabled={loading}
                className="glow-card glass glass-hover rounded-xl p-6 text-left transition-all duration-300 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed group"
              >
                <div className="flex items-start gap-4">
                  <div className="p-3 rounded-lg bg-gradient-to-br from-primary-500/20 to-primary-700/20 group-hover:from-primary-500/30 group-hover:to-primary-700/30 transition-colors">
                    <Icon className="w-6 h-6 text-primary-400" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-lg mb-2">{config.name}</h3>
                    <p className="text-sm text-gray-400 mb-4">
                      {config.description}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <span className="text-xs px-2 py-1 rounded bg-primary-500/20 text-primary-300">
                        {config.allowed_tools.length} tools
                      </span>
                      {config.has_sub_agents && (
                        <span className="text-xs px-2 py-1 rounded bg-gray-700/30 text-gray-300">
                          Multi-Agent
                        </span>
                      )}
                      {config.has_mcp_servers && (
                        <span className="text-xs px-2 py-1 rounded bg-blue-500/20 text-blue-300">
                          MCP
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </button>
            );
          })}

          {/* Custom Builder Card */}
          <button
            onClick={() => router.push('/builder')}
            className="glass glass-hover rounded-xl p-6 text-left transition-all duration-300 hover:scale-105 group border-2 border-dashed border-gray-700"
          >
            <div className="flex items-start gap-4">
              <div className="p-3 rounded-lg bg-gradient-to-br from-gray-500/20 to-gray-700/20 group-hover:from-gray-500/30 group-hover:to-gray-700/30 transition-colors">
                <Plus className="w-6 h-6 text-gray-400" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-lg mb-2">Custom Agent</h3>
                <p className="text-sm text-gray-400">
                  Build your own agent configuration with specialized tools and prompts
                </p>
              </div>
            </div>
          </button>
          </div>
        )}
      </main>
    </div>
  );
}
