'use client';

import { useEffect, useState } from 'react';

// Tool execution event type
export interface ToolEvent {
  type: string;
  tool_name: string;
  tool_use_id?: string;
  tool_type?: string;
  tool_input?: any;
  timestamp: string;
  duration_ms?: number;
  output?: any;
  error?: string;
  status?: 'started' | 'in_progress' | 'completed' | 'error';
  is_error?: boolean;
  completed_at?: string;
}

// Thinking event type
export interface ThinkingEvent {
  type: 'thinking';
  content?: string;
  timestamp?: string;
}

/**
 * Hook to monitor tool stream connection status.
 *
 * Since tool events are now received directly through the chat stream
 * (via custom fetch in ChatInterface), this hook provides a simplified
 * connection status that's always true when the session is active.
 *
 * @param sessionId - The session ID to monitor
 * @returns Object with isConnected boolean
 */
export function useToolStream(sessionId: string) {
  const [isConnected, setIsConnected] = useState(true);

  useEffect(() => {
    // For now, always mark as connected since events come through the chat stream
    setIsConnected(true);

    // Cleanup function
    return () => {
      setIsConnected(false);
    };
  }, [sessionId]);

  return { isConnected };
}
