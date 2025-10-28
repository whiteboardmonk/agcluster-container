'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Activity, Clock, Cpu, HardDrive, MemoryStick, Trash2, MessageSquare } from 'lucide-react';
import Navigation from '@/components/Navigation';

interface Session {
  session_id: string;
  agent_id: string;
  config_id: string;
  status: string;
  created_at: string;
  last_activity: string;
  container_stats?: {
    cpu_usage: number;
    memory_usage: string;
    network_rx: string;
    network_tx: string;
  };
}

export default function SessionsPage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadSessions();
    // Refresh every 5 seconds
    const interval = setInterval(loadSessions, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadSessions = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/agents/sessions`);

      if (!res.ok) {
        throw new Error('Failed to load sessions');
      }

      const data = await res.json();
      setSessions(data.sessions || []);
      setError('');
    } catch (error) {
      console.error('Error loading sessions:', error);
      setError(error instanceof Error ? error.message : 'Failed to load sessions');
    } finally {
      setLoading(false);
    }
  };

  const terminateSession = async (sessionId: string) => {
    if (!confirm('Are you sure you want to terminate this session?')) {
      return;
    }

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/agents/sessions/${sessionId}`, {
        method: 'DELETE',
      });

      if (!res.ok) {
        throw new Error('Failed to terminate session');
      }

      // Reload sessions
      loadSessions();
    } catch (error) {
      console.error('Error terminating session:', error);
      alert(`Failed to terminate session: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const formatDuration = (timestamp: string) => {
    const start = new Date(timestamp).getTime();
    const now = Date.now();
    const diff = Math.floor((now - start) / 1000); // seconds

    if (diff < 60) return `${diff}s`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
    return `${Math.floor(diff / 86400)}d`;
  };

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Header */}
      <Navigation />

      {/* Page Title */}
      <div className="border-b border-gray-800/50 bg-gradient-to-b from-black via-gray-950/5 to-black">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 text-center">
          <h1 className="text-2xl md:text-3xl font-bold gradient-text mb-1">Active Sessions</h1>
          <p className="text-gray-400 text-sm">Monitor and manage your agent sessions</p>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading && sessions.length === 0 && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-gray-500 mb-4"></div>
            <p className="text-gray-400">Loading sessions...</p>
          </div>
        )}

        {error && (
          <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/50 text-red-400 mb-6">
            {error}
          </div>
        )}

        {!loading && sessions.length === 0 && !error && (
          <div className="text-center py-12 glass rounded-xl">
            <Activity className="w-16 h-16 mx-auto mb-4 text-gray-600" />
            <h3 className="text-xl font-semibold mb-2">No Active Sessions</h3>
            <p className="text-gray-400 mb-6">Launch an agent from the dashboard to get started</p>
            <button
              onClick={() => router.push('/')}
              className="px-6 py-3 bg-gray-700 hover:bg-gray-600 rounded transition-colors"
            >
              Go to Dashboard
            </button>
          </div>
        )}

        {sessions.length > 0 && (
          <div className="grid gap-4">
            {sessions.map((session) => (
              <div
                key={session.session_id}
                className="glow-card glass rounded-xl p-6 hover:bg-gray-900/50 transition-all cursor-pointer group"
                onClick={() => router.push(`/chat/${session.session_id}`)}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-semibold group-hover:text-gray-200 transition-colors">
                        {session.config_id}
                      </h3>
                      <span className={`px-2 py-1 rounded text-xs ${
                        session.status === 'running'
                          ? 'bg-green-500/20 text-green-400'
                          : 'bg-gray-500/20 text-gray-400'
                      }`}>
                        {session.status}
                      </span>
                    </div>
                    <p className="text-sm text-gray-400 font-mono">
                      Session: {session.session_id.substring(0, 12)}...
                    </p>
                    <p className="text-sm text-gray-400 font-mono">
                      Container: {session.agent_id.substring(0, 12)}...
                    </p>
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        router.push(`/chat/${session.session_id}`);
                      }}
                      className="p-2 bg-gray-700 hover:bg-gray-600 rounded transition-colors"
                      title="Open chat"
                    >
                      <MessageSquare className="w-5 h-5" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        terminateSession(session.session_id);
                      }}
                      className="p-2 bg-red-900/70 hover:bg-red-900/90 rounded transition-colors"
                      title="Terminate session"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                </div>

                {/* Time Info */}
                <div className="flex gap-6 mb-4 text-sm">
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-gray-500" />
                    <span className="text-gray-400">Created:</span>
                    <span>{formatDuration(session.created_at)} ago</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Activity className="w-4 h-4 text-gray-500" />
                    <span className="text-gray-400">Last activity:</span>
                    <span>{formatDuration(session.last_activity)} ago</span>
                  </div>
                </div>

                {/* Resource Stats */}
                {session.container_stats && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-gray-800">
                    <div className="flex items-center gap-2">
                      <Cpu className="w-4 h-4 text-blue-400" />
                      <div>
                        <div className="text-xs text-gray-500">CPU</div>
                        <div className="text-sm font-medium">{session.container_stats.cpu_usage.toFixed(1)}%</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <MemoryStick className="w-4 h-4 text-gray-400" />
                      <div>
                        <div className="text-xs text-gray-500">Memory</div>
                        <div className="text-sm font-medium">{session.container_stats.memory_usage}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <HardDrive className="w-4 h-4 text-green-400" />
                      <div>
                        <div className="text-xs text-gray-500">Network RX</div>
                        <div className="text-sm font-medium">{session.container_stats.network_rx}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <HardDrive className="w-4 h-4 text-orange-400" />
                      <div>
                        <div className="text-xs text-gray-500">Network TX</div>
                        <div className="text-sm font-medium">{session.container_stats.network_tx}</div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
