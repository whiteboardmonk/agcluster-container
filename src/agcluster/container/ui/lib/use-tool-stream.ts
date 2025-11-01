import { useEffect, useState, useRef } from 'react';

export interface ToolEvent {
  type: 'tool_start' | 'tool_progress' | 'tool_complete' | 'tool_error';
  tool_name: string;
  tool_input?: unknown;
  output?: string | object;
  timestamp: string;
  status: string;
  duration_ms?: number;
  error?: string;
}

export interface ThinkingEvent {
  type: 'thinking';
  content: string;
  timestamp: string;
}

export interface TodoItem {
  content: string;
  status: 'pending' | 'in_progress' | 'completed';
  activeForm: string;
}

export interface TodoEvent {
  type: 'todo_update';
  todos: TodoItem[];
  timestamp: string;
}

export interface UseToolStreamReturn {
  toolEvents: ToolEvent[];
  thinkingEvents: ThinkingEvent[];
  todos: TodoItem[];
  isConnected: boolean;
  error: string | null;
}

/**
 * Hook to stream tool execution events via SSE from backend
 *
 * @param sessionId - Agent session ID
 * @returns Tool events, thinking events, todos, connection status, and errors
 */
export function useToolStream(sessionId: string | undefined): UseToolStreamReturn {
  const [toolEvents, setToolEvents] = useState<ToolEvent[]>([]);
  const [thinkingEvents, setThinkingEvents] = useState<ThinkingEvent[]>([]);
  const [todos, setTodos] = useState<TodoItem[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);

  useEffect(() => {
    if (!sessionId) {
      return;
    }

    const connect = () => {
      try {
        // Determine API URL (server-side vs client-side)
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const url = `${apiUrl}/api/tools/${sessionId}/stream`;

        console.log(`Connecting to tool stream: ${url}`);

        const eventSource = new EventSource(url);
        eventSourceRef.current = eventSource;

        eventSource.onopen = () => {
          console.log('Tool stream connected');
          setIsConnected(true);
          setError(null);
          reconnectAttemptsRef.current = 0;
        };

        eventSource.addEventListener('tool', (e) => {
          try {
            const data = JSON.parse(e.data);

            // Handle tool events
            if (data.type === 'tool_start' || data.type === 'tool_progress' ||
                data.type === 'tool_complete' || data.type === 'tool_error') {
              const toolEvent: ToolEvent = {
                type: data.type,
                tool_name: data.tool_name,
                tool_input: data.tool_input,
                timestamp: data.timestamp,
                status: data.status,
                duration_ms: data.duration_ms,
                error: data.error
              };

              setToolEvents(prev => {
                // If this is a completion/error event, try to update existing tool
                if (data.type === 'tool_complete' || data.type === 'tool_error') {
                  // Find the most recent "started" event for this tool
                  const existingIndex = prev.findIndex(
                    event => event.tool_name === data.tool_name && event.status === 'started'
                  );

                  if (existingIndex !== -1) {
                    // Update the existing event's status
                    const updated = [...prev];
                    updated[existingIndex] = {
                      ...updated[existingIndex],
                      type: data.type,
                      status: data.status,
                      duration_ms: data.duration_ms,
                      error: data.error
                    };
                    return updated;
                  }
                }

                // For new tool_start or if no existing event found, append
                return [...prev, toolEvent];
              });
            }

            // Handle TodoWrite updates
            else if (data.type === 'todo_update') {
              setTodos(data.todos || []);
            }

            // Handle thinking events
            else if (data.type === 'thinking') {
              const thinkingEvent: ThinkingEvent = {
                type: 'thinking',
                content: data.content,
                timestamp: data.timestamp
              };
              setThinkingEvents(prev => [...prev, thinkingEvent]);
            }
          } catch (err) {
            console.error('Error parsing tool event:', err);
          }
        });

        eventSource.addEventListener('error', (e: Event & { data?: string }) => {
          try {
            if (e.data) {
              const data = JSON.parse(e.data);
              if (data.fatal) {
                console.error('Fatal tool stream error:', data.message);
                setError(data.message);
                setIsConnected(false);
                eventSource.close();
              } else {
                console.warn('Tool stream error (will retry):', data.message);
              }
            }
          } catch {
            // Generic error event (connection lost)
            console.error('Tool stream connection error');
          }
        });

        eventSource.onerror = () => {
          console.error('Tool stream connection failed');
          setIsConnected(false);

          // Attempt to reconnect with exponential backoff
          if (reconnectAttemptsRef.current < 5) {
            const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
            console.log(`Reconnecting in ${delay}ms...`);

            reconnectTimeoutRef.current = setTimeout(() => {
              reconnectAttemptsRef.current += 1;
              connect();
            }, delay);
          } else {
            setError('Failed to connect to tool stream after multiple attempts');
          }
        };

      } catch (err) {
        console.error('Error creating EventSource:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
        setIsConnected(false);
      }
    };

    connect();

    // Cleanup on unmount
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };
  }, [sessionId]);

  return {
    toolEvents,
    thinkingEvents,
    todos,
    isConnected,
    error
  };
}
