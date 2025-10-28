'use client';

import { useState } from 'react';
import { Brain, ChevronDown, ChevronUp } from 'lucide-react';
import { ThinkingEvent } from '../lib/use-tool-stream';

interface ThinkingCardProps {
  event: ThinkingEvent;
}

export function ThinkingCard({ event }: ThinkingCardProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  const formatTime = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch {
      return timestamp;
    }
  };

  // Truncate content for preview when collapsed
  const previewContent = event.content.length > 100
    ? event.content.substring(0, 100) + '...'
    : event.content;

  return (
    <div
      className="flex items-start gap-2.5 px-3 py-2.5 rounded-xl bg-gradient-to-r from-gray-900/40 to-gray-800/40 border border-gray-700/50 backdrop-blur-sm"
      data-testid="thinking-card"
    >
      <div className="flex-shrink-0">
        <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-gray-700/40 to-gray-800/40 flex items-center justify-center">
          <Brain className="w-3.5 h-3.5 text-gray-400" />
        </div>
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <h4 className="text-xs font-medium text-white">Thinking</h4>
            <span className="text-[10px] text-gray-500">{formatTime(event.timestamp)}</span>
          </div>
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-1 hover:bg-gray-700/20 rounded transition-colors"
            aria-label={isCollapsed ? "Expand thinking" : "Collapse thinking"}
          >
            {isCollapsed ? (
              <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
            ) : (
              <ChevronUp className="w-3.5 h-3.5 text-gray-400" />
            )}
          </button>
        </div>

        <div className="text-xs text-gray-300 whitespace-pre-wrap leading-relaxed">
          {isCollapsed ? previewContent : event.content}
        </div>
      </div>
    </div>
  );
}