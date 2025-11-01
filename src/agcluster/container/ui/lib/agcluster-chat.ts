import { useState, useCallback, useRef, useEffect } from 'react';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  createdAt?: Date;
}

export interface UseAgClusterChatOptions {
  api: string;
  id?: string;
  body?: Record<string, any>;
  onError?: (error: Error) => void;
  onData?: (dataPart: any) => void;
}

export interface UseAgClusterChatReturn {
  messages: Message[];
  input: string;
  handleInputChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  handleSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  isLoading: boolean;
  error: Error | null;
}

/**
 * Custom hook for AgCluster chat that handles raw OpenAI SSE format
 * with custom data parts (data-tool, data-todo)
 */
export function useAgClusterChat(options: UseAgClusterChatOptions): UseAgClusterChatReturn {
  const { api, id, body = {}, onError, onData } = options;

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value);
  }, []);

  const handleSubmit = useCallback(async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: input.trim(),
      createdAt: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setError(null);

    // Create abort controller for this request
    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch(api, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: [...messages, userMessage].map(m => ({
            role: m.role,
            content: m.content,
          })),
          ...body,
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      if (!response.body) {
        throw new Error('No response body');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: '',
        createdAt: new Date(),
      };
      let isFirstChunk = true;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (!line.trim() || line.trim() === 'data: [DONE]') continue;

          // Handle custom SSE events (data-tool, data-todo)
          if (line.startsWith('data: {')) {
            try {
              const data = JSON.parse(line.slice(6)); // Remove 'data: ' prefix

              // Check if this is a custom data part
              if (data.type === 'data-tool' || data.type === 'data-todo') {
                if (onData) {
                  onData(data);
                }
                continue;
              }

              // Handle OpenAI completion chunks
              if (data.choices && data.choices[0]?.delta?.content) {
                const content = data.choices[0].delta.content;
                assistantMessage.content += content;

                if (isFirstChunk) {
                  setMessages(prev => [...prev, assistantMessage]);
                  isFirstChunk = false;
                } else {
                  setMessages(prev =>
                    prev.map(m =>
                      m.id === assistantMessage.id
                        ? { ...m, content: assistantMessage.content }
                        : m
                    )
                  );
                }
              }

              // Handle completion
              if (data.choices && data.choices[0]?.finish_reason) {
                break;
              }
            } catch (parseError) {
              console.warn('Failed to parse SSE line:', line, parseError);
            }
          }
        }
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error');
      setError(error);
      if (onError && error.name !== 'AbortError') {
        onError(error);
      }
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  }, [api, input, isLoading, messages, body, onError, onData]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return {
    messages,
    input,
    handleInputChange,
    handleSubmit,
    isLoading,
    error,
  };
}
