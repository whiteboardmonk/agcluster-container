'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { User, Bot } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt?: Date;
}

interface MessageCardProps {
  message: Message;
}

export function MessageCard({ message }: MessageCardProps) {
  const isUser = message.role === 'user';

  return (
    <div
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
      data-testid="message-card"
    >
      <div
        className={`flex items-start gap-3 max-w-3xl p-3.5 rounded-2xl ${
          isUser
            ? 'bg-gradient-to-br from-gray-700 to-gray-800 text-white shadow-lg shadow-gray-900/30'
            : 'glass border border-gray-700/50 backdrop-blur-xl'
        }`}
      >
        <div className="flex-shrink-0">
          <div className={`w-7 h-7 rounded-xl flex items-center justify-center ${
            isUser ? 'bg-gray-800/60' : 'bg-gradient-to-br from-gray-800/40 to-gray-700/40'
          }`}>
            {isUser ? (
              <User className="w-4 h-4" />
            ) : (
              <Bot className="w-4 h-4 text-gray-400" />
            )}
          </div>
        </div>

        <div className="flex-1 min-w-0">
          {isUser ? (
            <p className="text-sm whitespace-pre-wrap leading-relaxed">{message.content}</p>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
                components={{
                  code: (props) => {
                    const { className, children } = props;
                    const isInline = !className || !className.startsWith('language-');
                    return isInline ? (
                      <code className="px-2 py-0.5 rounded-md bg-gray-800/80 text-gray-300 text-xs font-mono border border-gray-700/50">
                        {children}
                      </code>
                    ) : (
                      <code className={className}>
                        {children}
                      </code>
                    );
                  },
                  pre: (props) => (
                    <pre className="overflow-x-auto rounded-xl bg-gray-950/80 border border-gray-800/50 p-4 my-3 shadow-inner">
                      {props.children}
                    </pre>
                  ),
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
