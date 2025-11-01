'use client';

import { useState, useEffect } from 'react';

/**
 * Tool event type definition for tool execution tracking
 */
export interface ToolEvent {
  type: string;
  tool_name: string;
  tool_type?: string;
  tool_use_id?: string;
  tool_input?: any;
  status?: 'started' | 'in_progress' | 'completed' | 'error';
  output?: string | object;
  error?: string;
  timestamp: string;
  duration_ms?: number;
  is_error?: boolean;
  completed_at?: string;
}

/**
 * Todo item type for task tracking
 */
export interface TodoItem {
  content: string;
  activeForm?: string;
  status: 'pending' | 'in_progress' | 'completed';
}

/**
 * Thinking event type for Claude's reasoning process
 */
export interface ThinkingEvent {
  type: 'thinking';
  content: string;
  timestamp: string;
}

/**
 * Hook to track tool stream connection status
 *
 * This hook monitors whether the tool stream is connected and ready
 * to receive tool execution events. In the current architecture, tool
 * events are received through the chat stream, so this primarily tracks
 * session connectivity.
 *
 * @param sessionId - The current agent session ID
 * @returns Object with isConnected boolean indicating connection status
 */
export function useToolStream(sessionId: string) {
  const [isConnected, setIsConnected] = useState(true);

  useEffect(() => {
    // Check session connectivity
    const checkConnection = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/api/agents/sessions/${sessionId}`);
        setIsConnected(response.ok);
      } catch (error) {
        console.error('[useToolStream] Connection check failed:', error);
        setIsConnected(false);
      }
    };

    // Initial check
    checkConnection();

    // Poll connection status every 10 seconds
    const interval = setInterval(checkConnection, 10000);

    return () => clearInterval(interval);
  }, [sessionId]);

  return { isConnected };
}
