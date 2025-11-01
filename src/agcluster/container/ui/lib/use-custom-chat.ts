import { useState, useCallback } from 'react';

interface CustomChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export function useCustomChat(sessionId: string, apiKey: string) {
  const [messages, setMessages] = useState<CustomChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [input, setInput] = useState('');

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim()) return;

    setIsLoading(true);

    // Add user message
    const userMessage: CustomChatMessage = { role: 'user', content };
    setMessages(prev => [...prev, userMessage]);

    // Clear input
    setInput('');

    // Prepare assistant message
    let assistantContent = '';
    const assistantMessage: CustomChatMessage = { role: 'assistant', content: '' };
    setMessages(prev => [...prev, assistantMessage]);

    const eventCallbacks = {
      onTool: (event: any) => {},
      onThinking: (event: any) => {},
      onTodo: (event: any) => {},
      onPlan: (event: any) => {},
    };

    try {
      const response = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: [...messages, userMessage].map(m => ({
            role: m.role,
            content: m.content,
          })),
          sessionId,
          apiKey,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to send message: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No reader available');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');

        // Keep the last line in the buffer if it's not complete
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') continue;

            try {
              const parsed = JSON.parse(data);
              console.log('[Custom Chat] Parsed event:', parsed);

              // Handle text content
              if (parsed.type === 'text-delta' && parsed.delta) {
                assistantContent += parsed.delta;
                setMessages(prev => {
                  const newMessages = [...prev];
                  newMessages[newMessages.length - 1] = {
                    ...newMessages[newMessages.length - 1],
                    content: assistantContent,
                  };
                  return newMessages;
                });
              }

              // Handle custom events
              if (parsed.type === 'custom' && parsed.value) {
                const event = parsed.value;
                console.log('[Custom Chat] Custom event:', event.type, event);

                switch (event.type) {
                  case 'tool':
                    eventCallbacks.onTool(event);
                    break;
                  case 'thinking':
                    eventCallbacks.onThinking(event);
                    break;
                  case 'todo':
                    eventCallbacks.onTodo(event);
                    break;
                  case 'plan':
                    eventCallbacks.onPlan(event);
                    break;
                }
              }
            } catch (e) {
              console.error('[Custom Chat] Parse error:', e);
            }
          }
        }
      }
    } catch (error) {
      console.error('[Custom Chat] Error:', error);
      setMessages(prev => {
        const newMessages = [...prev];
        newMessages[newMessages.length - 1] = {
          ...newMessages[newMessages.length - 1],
          content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        };
        return newMessages;
      });
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, apiKey, messages]);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value);
  }, []);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  }, [input, sendMessage]);

  return {
    messages,
    input,
    isLoading,
    handleInputChange,
    handleSubmit,
    setEventCallbacks: (callbacks: Partial<typeof eventCallbacks>) => {
      Object.assign(eventCallbacks, callbacks);
    },
  };
}
