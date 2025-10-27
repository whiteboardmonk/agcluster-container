'use client';

import { User, Bot } from 'lucide-react';

interface MessageSegmentProps {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: Date | string;
}

export function MessageSegment({ role, content, timestamp }: MessageSegmentProps) {
  if (!content || content.trim() === '') {
    return null;
  }

  return (
    <div className={`flex items-start gap-3 ${role === 'user' ? 'justify-end' : ''}`}>
      {role === 'assistant' && (
        <div className="flex-shrink-0">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-600 flex items-center justify-center">
            <Bot className="w-5 h-5 text-white" />
          </div>
        </div>
      )}

      <div
        className={`flex-1 ${role === 'user' ? 'max-w-2xl' : 'max-w-4xl'}`}
      >
        <div
          className={`rounded-2xl px-4 py-3 ${
            role === 'user'
              ? 'bg-gradient-to-r from-blue-600 to-blue-700 text-white ml-auto'
              : 'glass text-gray-100'
          }`}
        >
          <div className="prose prose-invert max-w-none">
            {content.split('\n').map((line, i) => (
              <p key={i} className={i > 0 ? 'mt-2' : ''}>
                {line || '\u00A0'}
              </p>
            ))}
          </div>
        </div>
      </div>

      {role === 'user' && (
        <div className="flex-shrink-0">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-gray-700 to-gray-800 flex items-center justify-center">
            <User className="w-5 h-5 text-white" />
          </div>
        </div>
      )}
    </div>
  );
}