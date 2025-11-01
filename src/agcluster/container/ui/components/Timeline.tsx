'use client';

import { useEffect, useRef, useMemo } from 'react';
import { MessageCard } from './MessageCard';
import { ThinkingCard } from './ThinkingCard';
import { ToolEventCard } from './ToolEventCard';
import { ToolEvent, ThinkingEvent } from '../lib/use-tool-stream';
import { Loader2 } from 'lucide-react';

interface TimelineMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt?: Date;
  timestamp?: number;
}

interface TimelineEvent {
  type: 'message' | 'thinking' | 'tool';
  timestamp: number;
  data: TimelineMessage | ThinkingEvent | ToolEvent;
}

interface TimelineProps {
  messages: TimelineMessage[];
  thinkingEvents: ThinkingEvent[];
  toolEvents: ToolEvent[];
  isLoading?: boolean;
  error?: Error | null;
}

export function Timeline({
  messages,
  thinkingEvents,
  toolEvents,
  isLoading,
  error
}: TimelineProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Merge and sort all events chronologically
  const timeline = useMemo(() => {
    const events: TimelineEvent[] = [];

    // Add messages (filter to only user/assistant)
    messages.forEach((message, index) => {
      // Skip if message is undefined or null
      if (!message) return;

      if (message.role === 'user' || message.role === 'assistant') {
        events.push({
          type: 'message',
          timestamp: message.createdAt ? new Date(message.createdAt).getTime() : Date.now(),
          data: {
            id: message.id || `msg-${index}`, // Fallback to index-based ID if missing
            role: message.role,
            content: message.content || '', // Ensure content is never undefined
            createdAt: message.createdAt
          }
        });
      }
    });

    // Add thinking events
    thinkingEvents.forEach((event) => {
      events.push({
        type: 'thinking',
        timestamp: new Date(event.timestamp).getTime(),
        data: event
      });
    });

    // Add tool events
    toolEvents.forEach((event) => {
      events.push({
        type: 'tool',
        timestamp: new Date(event.timestamp).getTime(),
        data: event
      });
    });

    // Sort by timestamp
    return events.sort((a, b) => a.timestamp - b.timestamp);
  }, [messages, thinkingEvents, toolEvents]);

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [timeline]);

  return (
    <div className="flex-1 overflow-y-auto" data-testid="timeline">
      <div className="max-w-4xl mx-auto px-4 py-6 space-y-3">
        {timeline.length === 0 && !isLoading && (
          <div className="text-center text-gray-500 mt-12">
            <p className="text-xl mb-2">Ready to assist</p>
            <p className="text-sm">Send a message to get started</p>
          </div>
        )}

        {timeline.map((event, index) => {
          const key = `${event.type}-${index}-${event.timestamp}`;

          // Each event gets its own separate rendering - no grouping
          switch (event.type) {
            case 'message':
              return (
                <div key={key} className="mb-3">
                  <MessageCard message={event.data as TimelineMessage} />
                </div>
              );
            case 'thinking':
              return (
                <div key={key} className="mb-2">
                  <ThinkingCard event={event.data as ThinkingEvent} />
                </div>
              );
            case 'tool':
              return (
                <div key={key} className="mb-2">
                  <ToolEventCard event={event.data as ToolEvent} />
                </div>
              );
            default:
              return null;
          }
        })}

        {isLoading && (
          <div className="flex items-center gap-2 text-gray-400 justify-center py-4">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">Agent is thinking...</span>
          </div>
        )}

        {error && (
          <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/50 text-red-400">
            Error: {error.message}
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
