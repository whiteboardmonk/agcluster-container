'use client';

import React from 'react';
import { Wrench, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { ToolEvent } from '../lib/use-tool-stream';

interface ToolEventCardProps {
  event: ToolEvent;
}

export function ToolEventCard({ event }: ToolEventCardProps) {
  const getStatusIcon = () => {
    switch (event.status) {
      case 'started':
        return <Loader2 className="w-3.5 h-3.5 text-yellow-400 animate-spin" />;
      case 'completed':
        return <CheckCircle className="w-3.5 h-3.5 text-green-400" />;
      case 'error':
        return <AlertCircle className="w-3.5 h-3.5 text-red-400" />;
      default:
        return <Wrench className="w-3.5 h-3.5 text-gray-400" />;
    }
  };

  const getStatusColor = () => {
    switch (event.status) {
      case 'started': return 'text-yellow-400';
      case 'completed': return 'text-green-400';
      case 'error': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  // Extract key metadata from tool_input
  const getKeyMetadata = () => {
    if (!event.tool_input) return null;

    if (typeof event.tool_input === 'object') {
      const input = event.tool_input as Record<string, unknown>;

      // Special handling for TodoWrite - show intelligent summary
      if (event.tool_name === 'TodoWrite' && input.todos && Array.isArray(input.todos)) {
        const todos = input.todos as any[];
        const total = todos.length;

        // Count by status
        const statusCounts = todos.reduce((acc, todo) => {
          const status = todo.status || 'pending';
          acc[status] = (acc[status] || 0) + 1;
          return acc;
        }, {} as Record<string, number>);

        const completed = statusCounts.completed || 0;
        const inProgress = statusCounts.in_progress || 0;
        const pending = statusCounts.pending || 0;

        // Generate smart summary
        if (completed > 0 && pending === 0 && inProgress === 0) {
          return `${completed} task${completed === 1 ? '' : 's'} completed`;
        } else if (pending > 0 && completed === 0 && inProgress === 0) {
          return `${pending} new task${pending === 1 ? '' : 's'}`;
        } else if (inProgress === 1 && completed === 0 && pending === 0) {
          return `started: ${todos[0].content?.substring(0, 30) || 'task'}${todos[0].content?.length > 30 ? '...' : ''}`;
        } else if (completed > 0 && pending > 0) {
          return `${completed} done, ${pending} pending`;
        } else if (completed > 0 && inProgress > 0) {
          return `${completed} done, ${inProgress} in progress`;
        } else {
          // Fallback to simple count
          return `${total} task${total === 1 ? '' : 's'}`;
        }
      }

      // For file operations, show just the file path
      if (input.file_path) return input.file_path as string;
      if (input.path) return input.path as string;

      // For bash, show the command
      if (input.command) {
        const cmd = input.command as string;
        return cmd.length > 50 ? `${cmd.substring(0, 50)}...` : cmd;
      }

      // For other tools, show first meaningful value
      const firstKey = Object.keys(input)[0];
      if (firstKey) {
        const value = input[firstKey];
        const str = String(value);
        return str.length > 50 ? `${str.substring(0, 50)}...` : str;
      }
    }

    return null;
  };

  const metadata = getKeyMetadata();

  return (
    <div
      className="flex items-center gap-2 px-3 py-2 text-xs text-gray-400 hover:bg-gray-800/30 rounded-lg transition-colors"
      data-testid="tool-event-card"
    >
      {getStatusIcon()}
      <span className={`font-medium ${getStatusColor()}`}>{event.tool_name}</span>
      {metadata && (
        <>
          <span className="text-gray-600">·</span>
          <span className="text-gray-500 truncate">{metadata}</span>
        </>
      )}
      {event.duration_ms && event.status === 'completed' && (
        <>
          <span className="text-gray-600">·</span>
          <span className="text-gray-500">{event.duration_ms}ms</span>
        </>
      )}
      {event.error && (
        <>
          <span className="text-gray-600">·</span>
          <span className="text-red-400 truncate">{event.error}</span>
        </>
      )}
    </div>
  );
}
