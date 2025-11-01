'use client';

import { useEffect, useState, useCallback } from 'react';
import { ArrowLeft, Send, Loader2, StopCircle, PanelRightOpen, PanelRightClose, XCircle, CheckCircle, AlertCircle, Maximize2, Minimize2, ChevronDown, ChevronRight, Paperclip } from 'lucide-react';
import { useToolStream } from '../lib/use-tool-stream';
import { ToolExecutionPanel } from './ToolExecutionPanel';
import { TodoList } from './TodoList';
import { ResourceMonitor } from './ResourceMonitor';
import { FileExplorer } from './FileExplorer';
import { FileViewer } from './FileViewer';
import { Timeline } from './Timeline';
import { FileUploadModal } from './FileUploadModal';

interface ChatInterfaceProps {
  sessionId: string;
  apiKey: string;
  onBack: () => void;
}

export function ChatInterface({ sessionId, apiKey, onBack }: ChatInterfaceProps) {
  const [isStopping, setIsStopping] = useState(false);
  const [isInterrupting, setIsInterrupting] = useState(false);
  const [manualInput, setManualInput] = useState(''); // Fallback input state
  const [manualMessages, setManualMessages] = useState<any[]>([]); // Manual messages state
  const [manualLoading, setManualLoading] = useState(false); // Manual loading state
  const [messageSegments, setMessageSegments] = useState<any[]>([]); // Track message segments with timestamps

  // Panel visibility
  const [showRightPanel, setShowRightPanel] = useState(true);
  const [showResourceMonitor, setShowResourceMonitor] = useState(false);
  const [showTasksPanel, setShowTasksPanel] = useState(true);
  const [showToolsPanel, setShowToolsPanel] = useState(false); // Collapsed by default
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [sessionStatus, setSessionStatus] = useState<'checking' | 'active' | 'not_found' | 'error'>('checking');
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [showUploadModal, setShowUploadModal] = useState(false);

  // State for Claude-specific events from chat stream
  const [toolEvents, setToolEvents] = useState<any[]>([]);
  const [todos, setTodos] = useState<any[]>([]);
  const [thinkingEvents, setThinkingEvents] = useState<any[]>([]);

  // Connect to tool stream
  const { isConnected } = useToolStream(sessionId);

  const checkSessionStatus = useCallback(async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/agents/sessions/${sessionId}`);

      if (response.ok) {
        const data = await response.json();
        setSessionStatus('active');
        console.log('Session resumed:', data);
      } else if (response.status === 404) {
        setSessionStatus('not_found');
        setSessionError('Session not found or expired. Please create a new session from the dashboard.');
      } else {
        setSessionStatus('error');
        setSessionError('Failed to check session status. The session may not exist.');
      }
    } catch (error) {
      console.error('Error checking session:', error);
      setSessionStatus('error');
      setSessionError('Could not connect to the API. Please check if the service is running.');
    }
  }, [sessionId]);

  // Check session status on mount
  useEffect(() => {
    checkSessionStatus();
  }, [checkSessionStatus]);

  // Log for debugging
  console.log('[ChatInterface] Mounted with apiKey:', apiKey ? 'Set' : 'Empty');
  console.log('[ChatInterface] sessionStatus:', sessionStatus);

  const handleStopSession = async () => {
    if (!confirm('Are you sure you want to stop this session? This will terminate the agent container.')) {
      return;
    }

    setIsStopping(true);
    try {
      const response = await fetch(`http://localhost:8000/api/agents/sessions/${sessionId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        onBack();
      } else {
        const error = await response.json();
        alert(`Failed to stop session: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error stopping session:', error);
      alert('Failed to stop session. Please try again.');
    } finally {
      setIsStopping(false);
    }
  };

  const handleInterrupt = async () => {
    setIsInterrupting(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/agents/sessions/${sessionId}/interrupt`, {
        method: 'POST',
      });

      if (!response.ok) {
        console.error('Interrupt failed:', response.statusText);
      }
    } catch (error) {
      console.error('Error sending interrupt:', error);
    } finally {
      setTimeout(() => setIsInterrupting(false), 1000);
    }
  };

  // Manual submit handler when useChat isn't working
  const handleManualSubmit = async (messageContent: string) => {
    console.log('[Manual Submit] Starting with message:', messageContent);

    if (!messageContent.trim()) return;

    setManualLoading(true);

    // Add user message to manual messages
    const userMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: messageContent,
      createdAt: new Date(),
    };
    setManualMessages(prev => [...prev, userMessage]);

    try {
      // Prepare messages array including the new user message
      const messagesToSend = [
        ...manualMessages,
        userMessage,
      ].map(m => ({
        role: m.role,
        content: m.content,
      }));

      console.log('[Manual Submit] Sending messages:', messagesToSend);

      // Call the chat API directly
      const response = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: messagesToSend,
          sessionId,
          apiKey,
        }),
      });

      if (!response.ok) {
        throw new Error(`Chat API error: ${response.statusText}`);
      }

      // Read the streaming response
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let assistantContent = '';
      let buffer = ''; // Add buffer for partial lines

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');

          // Keep the last line in buffer if it's incomplete
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6).trim();
              if (!data || data === '[DONE]') continue;

              try {
                const parsed = JSON.parse(data);

                // Debug log to see what we're receiving
                if (parsed.type !== 'text-delta' && parsed.type !== 'text-start' && parsed.type !== 'text-end' && parsed.type !== 'finish') {
                  console.log('[Manual Submit] Received event type:', parsed.type, parsed);
                }

                // Handle text content - create message segments with proper timestamps
                if (parsed.type === 'text-delta' && parsed.delta) {
                  const timestamp = Date.now();

                  setMessageSegments(prev => {
                    const lastSegment = prev[prev.length - 1];

                    // Append to last segment if it's recent (within 50ms) and is assistant role
                    if (lastSegment && lastSegment.role === 'assistant' &&
                        (timestamp - lastSegment.timestamp) < 50 &&
                        !lastSegment.closed) {
                      return [
                        ...prev.slice(0, -1),
                        {
                          ...lastSegment,
                          content: lastSegment.content + parsed.delta
                        }
                      ];
                    } else {
                      // Create new segment with current timestamp
                      return [
                        ...prev,
                        {
                          id: `segment-${timestamp}`,
                          role: 'assistant',
                          content: parsed.delta,
                          timestamp,
                          createdAt: new Date(timestamp),
                          closed: false
                        }
                      ];
                    }
                  });
                }

                // CRITICAL: Process custom events
                if (parsed.type === 'custom' && parsed.value) {
                  const event = parsed.value;
                  console.log('[Manual Submit] Custom event:', event.type, event);

                  switch (event.type) {
                    case 'tool':
                      // Close current message segment so next text-delta creates a new one
                      setMessageSegments(prev => {
                        if (prev.length > 0 && !prev[prev.length - 1].closed) {
                          return [
                            ...prev.slice(0, -1),
                            { ...prev[prev.length - 1], closed: true }
                          ];
                        }
                        return prev;
                      });

                      setToolEvents(prev => {
                        const toolType = event.tool_type || event.type;
                        if (toolType === 'tool_start') {
                          const toolUseId = event.tool_use_id;
                          console.log('[Manual Submit] Tool start:', event.tool_name, 'ID:', toolUseId);
                          // Add tool with tool_use_id for matching
                          return [...prev, {
                            ...event,
                            type: 'tool_start',
                            tool_use_id: toolUseId,
                            status: 'started'
                          }];
                        } else if (toolType === 'tool_complete') {
                          const toolUseId = event.tool_use_id;
                          console.log('[Manual Submit] Tool complete for ID:', toolUseId);

                          // Find and update the matching tool_start event by tool_use_id
                          const existingIndex = prev.findIndex(t => t.tool_use_id === toolUseId);

                          if (existingIndex !== -1) {
                            // Update existing tool to completed status
                            const updated = [...prev];
                            updated[existingIndex] = {
                              ...updated[existingIndex],
                              status: 'completed',
                              output: event.output,
                              is_error: event.is_error,
                              completed_at: event.timestamp
                            };
                            console.log('[Manual Submit] ✅ Updated tool at index', existingIndex, 'to completed');
                            return updated;
                          } else {
                            // If no matching start found, add as new (shouldn't happen normally)
                            console.warn('[Manual Submit] ⚠️  No matching tool_start found for ID:', toolUseId);
                            console.warn('[Manual Submit] Current tools:', prev.map(t => ({ name: t.tool_name, id: t.tool_use_id })));
                            return [...prev, { ...event, type: 'tool_complete' }];
                          }
                        }
                        return [...prev, event];
                      });
                      break;

                    case 'thinking':
                      console.log('[Manual Submit] Thinking event:', event.content);
                      setThinkingEvents(prev => [...prev, event]);
                      break;

                    case 'todo':
                      if (event.todos) {
                        console.log('[Manual Submit] Todo update:', event.todos.length, 'items');
                        console.log('[Manual Submit] Todo items:', event.todos);

                        // Update TodoList
                        setTodos(event.todos);
                      }
                      break;

                    case 'plan':
                      console.log('[Manual Submit] Plan event (ignored - planning panel removed)');
                      break;

                    case 'file':
                    case 'multi-agent':
                      console.log('[Manual Submit] File/multi-agent event (ignored - panels removed)');
                      break;
                  }
                }
              } catch (e) {
                // Ignore parse errors
              }
            }
          }
        }
      }

      console.log('[Manual Submit] Completed successfully');
    } catch (error) {
      console.error('[Manual Submit] Error:', error);
      // Optionally add an error message
      setManualMessages(prev => [...prev, {
        id: `msg-${Date.now()}-error`,
        role: 'assistant',
        content: `Error: ${error instanceof Error ? error.message : 'Failed to send message'}`,
        createdAt: new Date(),
      }]);
    } finally {
      setManualLoading(false);
      setManualInput(''); // Clear input after sending
    }
  };

  return (
    <div className="h-screen flex flex-col bg-gradient-to-br from-gray-950 via-black to-gray-950 text-white">
      {/* Header */}
      <header className="border-b border-gray-800/50 backdrop-blur-xl bg-black/40 flex-shrink-0">
        <div className="max-w-full mx-auto px-4 sm:px-6 lg:px-8 py-3">
          <div className="flex items-center gap-3">
            <button
              onClick={onBack}
              className="p-2 rounded-xl hover:bg-white/5 transition-all duration-200 hover:scale-105"
              title="Back to Dashboard"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div className="flex-1 min-w-0">
              <h1 className="text-sm font-semibold gradient-text truncate">Claude Agent Session</h1>
              <p className="text-xs text-gray-500 font-mono truncate">Session: {sessionId.substring(0, 16)}...</p>
            </div>

            {/* Panel Toggles */}
            <div className="flex items-center gap-1">
              <button
                onClick={() => setShowRightPanel(!showRightPanel)}
                className="p-2 rounded-xl hover:bg-white/5 transition-all duration-200"
                title={showRightPanel ? 'Hide activity panel' : 'Show activity panel'}
              >
                {showRightPanel ? (
                  <PanelRightClose className="w-4 h-4 text-gray-400" />
                ) : (
                  <PanelRightOpen className="w-4 h-4 text-gray-500" />
                )}
              </button>
              <button
                onClick={() => setShowResourceMonitor(!showResourceMonitor)}
                className="p-2 rounded-xl hover:bg-white/5 transition-all duration-200"
                title={showResourceMonitor ? 'Hide resources' : 'Show resources'}
              >
                {showResourceMonitor ? (
                  <Minimize2 className="w-4 h-4 text-emerald-400" />
                ) : (
                  <Maximize2 className="w-4 h-4 text-gray-500" />
                )}
              </button>
            </div>

            <button
              onClick={handleStopSession}
              disabled={isStopping}
              className="px-3 py-1.5 rounded-xl bg-gradient-to-r from-red-900/80 to-red-950/80 hover:from-red-900 hover:to-red-950 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center gap-2 text-xs font-medium shadow-lg shadow-red-950/20"
              title="Stop and close this session"
            >
              {isStopping ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <StopCircle className="w-3.5 h-3.5" />
              )}
              Stop
            </button>
          </div>
        </div>
      </header>

      {/* Session Status Banner */}
      {sessionStatus === 'checking' && (
        <div className="bg-gray-900/40 border-b border-gray-700/50 px-4 py-2 flex items-center gap-2 flex-shrink-0">
          <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
          <span className="text-sm text-gray-300">Checking session status...</span>
        </div>
      )}
      {sessionStatus === 'active' && (
        <div className="bg-green-900/20 border-b border-green-700/30 px-4 py-2 flex items-center gap-2 flex-shrink-0">
          <CheckCircle className="w-4 h-4 text-green-400" />
          <span className="text-sm text-green-300">Session active</span>
        </div>
      )}
      {(sessionStatus === 'not_found' || sessionStatus === 'error') && (
        <div className="bg-red-900/20 border-b border-red-700/30 px-4 py-3 flex-shrink-0">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm text-red-300 font-medium mb-1">Session Unavailable</p>
              <p className="text-xs text-red-300/80">{sessionError}</p>
            </div>
            <button
              onClick={onBack}
              className="px-3 py-1 rounded-lg bg-red-600/20 hover:bg-red-600/30 text-xs text-red-300 transition-colors"
            >
              Go to Dashboard
            </button>
          </div>
        </div>
      )}

      {/* Main Content Area - 3 Column Layout */}
      <div className="flex-1 flex overflow-hidden min-h-0">
        {/* Main Content - Timeline or File Viewer */}
        <div className="flex-1 flex flex-col overflow-hidden min-w-0">
          {selectedFile ? (
            <FileViewer
              sessionId={sessionId}
              filePath={selectedFile}
              onClose={() => setSelectedFile(null)}
            />
          ) : (
            <Timeline
              messages={(() => {
                // Merge user messages from manualMessages with assistant segments from messageSegments
                if (messageSegments.length > 0) {
                  // Get all user messages
                  const userMessages = manualMessages.filter(m => m.role === 'user');
                  // Combine user messages with assistant message segments
                  return [...userMessages, ...messageSegments].sort((a, b) => {
                    const aTime = a.createdAt?.getTime() || a.timestamp || 0;
                    const bTime = b.createdAt?.getTime() || b.timestamp || 0;
                    return aTime - bTime;
                  });
                }
                return manualMessages;
              })()}
              thinkingEvents={thinkingEvents}
              toolEvents={toolEvents}
              isLoading={manualLoading}
              error={null}
            />
          )}
        </div>

        {/* Right Panel - Tools, Files, Activity */}
        {showRightPanel && (
          <div className="w-96 flex flex-col overflow-hidden border-l border-gray-800/50 flex-shrink-0">
            {/* File Explorer */}
            <div className="h-64 border-b border-gray-800/50 flex-shrink-0">
              <FileExplorer
                sessionId={sessionId}
                onFileSelect={(filePath) => setSelectedFile(filePath)}
                selectedFile={selectedFile}
              />
            </div>

            {/* Tasks Panel - Collapsible */}
            <div className="border-b border-gray-800/50 flex-shrink-0">
              <button
                onClick={() => setShowTasksPanel(!showTasksPanel)}
                className="w-full p-3 flex items-center justify-between hover:bg-white/5 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold">Tasks</span>
                  <span className="text-xs text-gray-400">{todos.length} {todos.length === 1 ? 'task' : 'tasks'}</span>
                </div>
                {showTasksPanel ? (
                  <ChevronDown className="w-4 h-4 text-gray-400" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-gray-400" />
                )}
              </button>
              {showTasksPanel && (
                <div className="p-3 max-h-64 overflow-y-auto">
                  <TodoList todos={todos} />
                </div>
              )}
            </div>

            {/* Tool Execution Panel - Collapsible, Collapsed by Default */}
            <div className="flex-shrink-0">
              <button
                onClick={() => setShowToolsPanel(!showToolsPanel)}
                className="w-full p-3 flex items-center justify-between hover:bg-white/5 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold">Tool Execution</span>
                  <span className="text-xs text-gray-400">{toolEvents.length} {toolEvents.length === 1 ? 'event' : 'events'}</span>
                </div>
                {showToolsPanel ? (
                  <ChevronDown className="w-4 h-4 text-gray-400" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-gray-400" />
                )}
              </button>
              {showToolsPanel && (
                <div className="max-h-96 overflow-y-auto">
                  <ToolExecutionPanel toolEvents={toolEvents} isConnected={isConnected} />
                </div>
              )}
            </div>

            {/* Bottom: Resource Monitor */}
            {showResourceMonitor && (
              <div className="border-t border-gray-800 p-4 flex-shrink-0">
                <ResourceMonitor sessionId={sessionId} />
              </div>
            )}
          </div>
        )}
      </div>

      {/* Input Form */}
      <div className="border-t border-gray-800/50 backdrop-blur-xl bg-black/40 flex-shrink-0">
        <div className="max-w-4xl mx-auto px-4 py-3">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleManualSubmit(manualInput);
            }}
            className="flex gap-2">
            <input
              value={manualInput}
              onChange={(e) => setManualInput(e.target.value)}
              placeholder={sessionStatus === 'active' ? "Type your message or /command..." : "Session unavailable"}
              disabled={manualLoading || sessionStatus !== 'active'}
              className="flex-1 px-4 py-2.5 rounded-2xl bg-gray-900/50 border border-gray-800/50 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-gray-500/50 focus:border-gray-500/50 disabled:opacity-50 transition-all text-sm placeholder:text-gray-500"
              autoFocus
            />
            <button
              type="button"
              onClick={() => setShowUploadModal(true)}
              disabled={sessionStatus !== 'active'}
              className="px-3 py-2.5 rounded-2xl bg-gray-800/50 hover:bg-gray-700/50 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center"
              title="Upload files to workspace"
            >
              <Paperclip className="w-4 h-4" />
            </button>
            {manualLoading && (
              <button
                type="button"
                onClick={handleInterrupt}
                disabled={isInterrupting}
                className="px-4 py-2.5 rounded-2xl bg-gradient-to-r from-red-900/80 to-red-950/80 hover:from-red-900 hover:to-red-950 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center gap-2 text-xs font-medium shadow-lg shadow-red-950/20"
                title="Interrupt current execution"
              >
                {isInterrupting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <XCircle className="w-4 h-4" />
                )}
                Interrupt
              </button>
            )}
            <button
              type="submit"
              disabled={manualLoading || !manualInput.trim() || sessionStatus !== 'active'}
              className="px-5 py-2.5 rounded-2xl bg-gradient-to-r from-gray-700 to-gray-800 hover:from-gray-800 hover:to-gray-900 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center gap-2 text-xs font-medium shadow-lg shadow-gray-900/20"
            >
              {manualLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
              Send
            </button>
          </form>
        </div>
      </div>

      {/* File Upload Modal */}
      {showUploadModal && (
        <FileUploadModal
          sessionId={sessionId}
          onClose={() => setShowUploadModal(false)}
          onUploadComplete={() => {
            // File explorer auto-refreshes every 3s, so just close modal
            setShowUploadModal(false);
          }}
        />
      )}
    </div>
  );
}
