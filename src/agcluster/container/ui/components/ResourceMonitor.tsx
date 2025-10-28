'use client';

import { useEffect, useState } from 'react';
import { Cpu, HardDrive, MemoryStick } from 'lucide-react';

interface ResourceStats {
  cpu: {
    percent: number;
    count: number;
  };
  memory: {
    used_mb: number;
    limit_mb: number;
    percent: number;
  };
  disk: {
    percent: number;
  };
  status: string;
}

interface ResourceMonitorProps {
  sessionId: string | undefined;
}

export function ResourceMonitor({ sessionId }: ResourceMonitorProps) {
  const [stats, setStats] = useState<ResourceStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      return;
    }

    const fetchStats = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/api/resources/${sessionId}`);

        if (!response.ok) {
          throw new Error(`Failed to fetch resources: ${response.statusText}`);
        }

        const data = await response.json();
        setStats(data);
        setError(null);
      } catch (err) {
        console.error('Error fetching resource stats:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
      }
    };

    // Initial fetch
    fetchStats();

    // Poll every 2 seconds
    const interval = setInterval(fetchStats, 2000);

    return () => clearInterval(interval);
  }, [sessionId]);

  const getGaugeColor = (percent: number) => {
    if (percent >= 80) return 'text-red-500';
    if (percent >= 60) return 'text-yellow-500';
    return 'text-green-500';
  };

  const getGaugeFill = (percent: number) => {
    if (percent >= 80) return 'bg-red-500';
    if (percent >= 60) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  if (error) {
    return (
      <div
        className="p-4 glass rounded-lg border border-gray-800"
        data-testid="resource-monitor"
      >
        <h3 className="text-sm font-semibold mb-3">Resource Usage</h3>
        <p className="text-xs text-red-400">Failed to load resource stats</p>
      </div>
    );
  }

  if (!stats) {
    return (
      <div
        className="p-4 glass rounded-lg border border-gray-800"
        data-testid="resource-monitor"
      >
        <h3 className="text-sm font-semibold mb-3">Resource Usage</h3>
        <p className="text-xs text-gray-500">Loading...</p>
      </div>
    );
  }

  return (
    <div
      className="p-4 glass rounded-lg border border-gray-800"
      data-testid="resource-monitor"
    >
      <h3 className="text-sm font-semibold mb-4">Resource Usage</h3>

      <div className="space-y-4">
        {/* CPU Gauge */}
        <div data-testid="cpu-gauge">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-gray-400" />
              <span className="text-xs font-medium">CPU</span>
            </div>
            <span className={`text-xs font-semibold ${getGaugeColor(stats.cpu.percent)}`}>
              {stats.cpu.percent.toFixed(1)}%
            </span>
          </div>
          <div className="w-full h-2 glass rounded-full overflow-hidden">
            <div
              className={`h-full ${getGaugeFill(stats.cpu.percent)} transition-all duration-300`}
              style={{ width: `${Math.min(stats.cpu.percent, 100)}%` }}
            />
          </div>
          <p className="text-xs text-gray-500 mt-1">{stats.cpu.count} cores available</p>
        </div>

        {/* Memory Gauge */}
        <div data-testid="memory-gauge">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <MemoryStick className="w-4 h-4 text-gray-400" />
              <span className="text-xs font-medium">Memory</span>
            </div>
            <span className={`text-xs font-semibold ${getGaugeColor(stats.memory.percent)}`}>
              {stats.memory.percent.toFixed(1)}%
            </span>
          </div>
          <div className="w-full h-2 glass rounded-full overflow-hidden">
            <div
              className={`h-full ${getGaugeFill(stats.memory.percent)} transition-all duration-300`}
              style={{ width: `${Math.min(stats.memory.percent, 100)}%` }}
            />
          </div>
          <p className="text-xs text-gray-500 mt-1">
            {stats.memory.used_mb.toFixed(0)} MB / {stats.memory.limit_mb.toFixed(0)} MB
          </p>
        </div>

        {/* Disk Gauge */}
        <div data-testid="disk-gauge">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <HardDrive className="w-4 h-4 text-orange-400" />
              <span className="text-xs font-medium">Disk</span>
            </div>
            <span className={`text-xs font-semibold ${getGaugeColor(stats.disk.percent)}`}>
              {stats.disk.percent.toFixed(1)}%
            </span>
          </div>
          <div className="w-full h-2 glass rounded-full overflow-hidden">
            <div
              className={`h-full ${getGaugeFill(stats.disk.percent)} transition-all duration-300`}
              style={{ width: `${Math.min(stats.disk.percent, 100)}%` }}
            />
          </div>
          <p className="text-xs text-gray-500 mt-1">Storage usage</p>
        </div>
      </div>

      {/* Status */}
      <div className="mt-4 pt-4 border-t border-gray-800">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${
            stats.status === 'running' ? 'bg-green-500' : 'bg-gray-500'
          }`} />
          <span className="text-xs text-gray-400 capitalize">{stats.status}</span>
        </div>
      </div>
    </div>
  );
}
