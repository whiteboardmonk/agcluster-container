'use client';

import { use } from 'react';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { ChatInterface } from '../../../components/ChatInterface';

export default function ChatPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const sessionId = resolvedParams.id;
  const router = useRouter();
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);

  // Load API key from localStorage only once on mount
  useEffect(() => {
    const savedKey = localStorage.getItem('anthropic_api_key');
    console.log('[ChatPage] API key from localStorage:', savedKey ? 'Found' : 'Not found');

    if (savedKey) {
      setApiKey(savedKey);
      console.log('[ChatPage] API key loaded successfully');
    } else {
      console.log('[ChatPage] No API key found, redirecting to dashboard');
      router.push('/');
      return;
    }

    setIsInitializing(false);
  }, [router]);

  // Show loading screen while initializing
  if (isInitializing) {
    return (
      <div className="h-screen flex items-center justify-center bg-gradient-to-br from-gray-950 via-black to-gray-950">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-blue-500 mx-auto mb-4" />
          <p className="text-gray-400">Loading session...</p>
        </div>
      </div>
    );
  }

  // If we get here, we have an API key
  // Render ChatInterface which can now safely call useChat
  if (!apiKey) {
    return null; // This shouldn't happen due to redirect above
  }

  return (
    <ChatInterface
      sessionId={sessionId}
      apiKey={apiKey}
      onBack={() => router.push('/')}
    />
  );
}
