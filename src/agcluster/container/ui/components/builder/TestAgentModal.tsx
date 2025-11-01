'use client';

import { useState } from 'react';
import { X, Send, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface AgentConfig {
  id?: string;
  name?: string;
  allowed_tools?: string[];
  resource_limits?: {
    cpu_quota?: number;
    memory_limit?: string;
  };
  permission_mode?: string;
}

interface TestAgentModalProps {
  config: AgentConfig;
  onClose: () => void;
}

export function TestAgentModal({ config, onClose }: TestAgentModalProps) {
  const [apiKey, setApiKey] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [launching, setLaunching] = useState(false);

  // Simplified chat state - AI SDK v5 compatibility
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !sessionId) return;

    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Simple chat implementation
      const response = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [...messages, userMessage],
          sessionId,
          apiKey,
        }),
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let assistantContent = '';

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              if (data === '[DONE]') continue;

              try {
                const parsed = JSON.parse(data);
                if (parsed.type === 'text-delta' && parsed.delta) {
                  assistantContent += parsed.delta;
                }
              } catch (e) {
                // Ignore parse errors
              }
            }
          }
        }
      }

      setMessages(prev => [...prev, { role: 'assistant', content: assistantContent }]);
    } catch (error) {
      console.error('Chat error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const launchTest = async () => {
    if (!apiKey) {
      alert('Please enter your Anthropic API key');
      return;
    }

    setLaunching(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/agents/launch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: apiKey, config }),
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to launch agent');
      }

      const data = await res.json();
      setSessionId(data.session_id);
    } catch (error) {
      console.error('Error launching agent:', error);
      alert(`Failed to launch agent: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setLaunching(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-lg w-full max-w-4xl h-3/4 flex flex-col border border-gray-800">
        {/* Header */}
        <div className="p-4 border-b border-gray-800 flex justify-between items-center">
          <div>
            <h3 className="font-semibold text-lg">Test Agent: {config.name || 'Unnamed Agent'}</h3>
            <p className="text-xs text-gray-400">Test your configuration before saving</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-800 rounded transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {!sessionId ? (
          /* Launch Screen */
          <div className="flex-1 flex items-center justify-center p-6">
            <div className="w-full max-w-md space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">
                  Anthropic API Key
                </label>
                <input
                  type="password"
                  placeholder="sk-ant-..."
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="w-full px-4 py-2 bg-gray-800 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={launching}
                />
              </div>

              <div className="bg-gray-900/40 border border-gray-700/50 rounded p-4 text-sm">
                <p className="font-medium mb-2">Testing Configuration:</p>
                <ul className="text-xs text-gray-300 space-y-1">
                  <li>• Tools: {config.allowed_tools?.length || 0} selected</li>
                  <li>• CPU: {((config.resource_limits?.cpu_quota || 200000) / 100000).toFixed(1)} cores</li>
                  <li>• Memory: {config.resource_limits?.memory_limit || '4g'}</li>
                  <li>• Permission: {config.permission_mode || 'acceptEdits'}</li>
                </ul>
              </div>

              <button
                onClick={launchTest}
                disabled={!apiKey || launching}
                className="w-full px-4 py-3 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed rounded transition-colors flex items-center justify-center gap-2"
              >
                {launching ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Launching Test Agent...
                  </>
                ) : (
                  'Launch Test Agent'
                )}
              </button>
            </div>
          </div>
        ) : (
          /* Chat Interface */
          <>
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {messages.length === 0 && (
                <div className="text-center text-gray-500 mt-12">
                  <p className="text-lg mb-2">Test agent is ready</p>
                  <p className="text-sm">Send a message to test your configuration</p>
                </div>
              )}

              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-2xl rounded-xl p-4 ${
                      msg.role === 'user'
                        ? 'bg-gray-700 text-white'
                        : 'bg-gray-800 border border-gray-700'
                    }`}
                  >
                    {msg.role === 'assistant' ? (
                      <div className="prose prose-invert prose-sm max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {msg.content}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    )}
                  </div>
                </div>
              ))}

              {isLoading && (
                <div className="flex items-center gap-2 text-gray-400">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">Agent is thinking...</span>
                </div>
              )}

              {error && (
                <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/50 text-red-400">
                  Error: {error.message}
                </div>
              )}
            </div>

            {/* Input Form */}
            <form onSubmit={handleSubmit} className="p-4 border-t border-gray-800">
              <div className="flex gap-3">
                <input
                  value={input}
                  onChange={handleInputChange}
                  placeholder="Test message..."
                  disabled={isLoading}
                  className="flex-1 px-4 py-2 bg-gray-800 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  type="submit"
                  disabled={isLoading || !input.trim()}
                  className="px-6 py-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed rounded transition-colors flex items-center gap-2"
                >
                  {isLoading ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <Send className="w-5 h-5" />
                  )}
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
