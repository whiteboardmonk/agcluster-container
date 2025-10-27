/**
 * Vercel AI SDK v5 compatible streaming chat route for AgCluster
 *
 * Returns proper x-vercel-ai-ui-message-stream format with text-delta events
 */

import { type CoreMessage } from 'ai';

// Remove edge runtime for compatibility with standalone builds
// export const runtime = 'edge';
export const maxDuration = 300; // 5 minutes for long-running tasks

export async function POST(req: Request) {
  try {
    const {
      messages,
      sessionId,
      apiKey,
    }: {
      messages: CoreMessage[];
      sessionId?: string;
      apiKey: string;
    } = await req.json();

    if (!apiKey) {
      return new Response('API key is required', { status: 400 });
    }

    if (!messages || messages.length === 0) {
      return new Response('Messages are required', { status: 400 });
    }

    // Call Claude-native backend endpoint
    const backendUrl = process.env.AGCLUSTER_API_URL || 'http://api:8000';
    const chatUrl = `${backendUrl}/api/agents/chat`;

    // Prepare request body for backend
    const requestBody = {
      messages: messages.map(m => {
        let content: string;

        if (typeof m.content === 'string') {
          content = m.content;
        } else if (Array.isArray(m.content)) {
          content = m.content
            .filter((part: any) => part.type === 'text')
            .map((part: any) => part.text)
            .join('\n');
        } else {
          content = JSON.stringify(m.content);
        }

        return {
          role: m.role,
          content
        };
      }),
      sessionId: sessionId
    };

    // Set up headers
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
    };

    if (sessionId) {
      headers['X-Session-ID'] = sessionId;
    }

    // Make request to backend
    const response = await fetch(chatUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      console.error('Backend error:', response.statusText);
      return new Response(response.statusText, { status: response.status });
    }

    // Transform backend SSE to Vercel AI SDK format
    const encoder = new TextEncoder();
    let messageId = `msg_${Date.now()}`;
    let textStarted = false;

    const transformStream = new TransformStream({
      async transform(chunk, controller) {
        const text = new TextDecoder().decode(chunk);
        const lines = text.split('\n');

        for (const line of lines) {
          if (!line.trim() || line === '[DONE]') continue;

          // Parse SSE line
          if (line.startsWith('data: ')) {
            try {
              const jsonStr = line.slice(6);
              const event = JSON.parse(jsonStr);

              // Handle backend message events
              if (event.type === 'message') {
                const msgType = event.msg_type;
                const data = event.data || {};

                // Handle different message types from backend
                switch (msgType) {
                  case 'content':
                    // Regular text content
                    const content = data.content || '';
                    if (content) {
                      // Send text-start on first content
                      if (!textStarted) {
                        controller.enqueue(
                          encoder.encode(`data: ${JSON.stringify({ type: 'text-start', id: messageId })}\n\n`)
                        );
                        textStarted = true;
                      }

                      // Send text-delta for each chunk
                      controller.enqueue(
                        encoder.encode(`data: ${JSON.stringify({ type: 'text-delta', id: messageId, delta: content })}\n\n`)
                      );
                    }
                    break;

                  case 'thinking':
                    // Send thinking event as custom
                    controller.enqueue(
                      encoder.encode(`data: ${JSON.stringify({
                        type: 'custom',
                        value: {
                          type: 'thinking',
                          content: data.content,
                          timestamp: data.timestamp || new Date().toISOString()
                        }
                      })}\n\n`)
                    );
                    break;

                  case 'tool_start':
                  case 'tool_use':
                    // Tool started event
                    controller.enqueue(
                      encoder.encode(`data: ${JSON.stringify({
                        type: 'custom',
                        value: {
                          type: 'tool',
                          tool_type: 'tool_start',
                          tool_name: data.tool_name,
                          tool_use_id: data.tool_use_id, // CRITICAL: Forward tool_use_id for matching
                          tool_input: data.tool_input,
                          timestamp: data.timestamp || new Date().toISOString(),
                          status: 'started'
                        }
                      })}\n\n`)
                    );
                    break;

                  case 'tool_complete':
                    // Tool completed event - tool_name is actually the tool_use_id
                    controller.enqueue(
                      encoder.encode(`data: ${JSON.stringify({
                        type: 'custom',
                        value: {
                          type: 'tool',
                          tool_type: 'tool_complete',
                          tool_use_id: data.tool_name, // Backend sends tool_use_id as tool_name
                          timestamp: data.timestamp || new Date().toISOString(),
                          status: 'completed',
                          output: data.output,
                          is_error: data.is_error
                        }
                      })}\n\n`)
                    );
                    break;

                  case 'todo_update':
                    // Todo list update
                    controller.enqueue(
                      encoder.encode(`data: ${JSON.stringify({
                        type: 'custom',
                        value: {
                          type: 'todo',
                          todos: data.todos,
                          timestamp: data.timestamp || new Date().toISOString()
                        }
                      })}\n\n`)
                    );
                    break;

                  case 'plan':
                    // Planning event
                    controller.enqueue(
                      encoder.encode(`data: ${JSON.stringify({
                        type: 'custom',
                        value: {
                          type: 'plan',
                          ...data
                        }
                      })}\n\n`)
                    );
                    break;

                  case 'file':
                    // File/artifact event
                    controller.enqueue(
                      encoder.encode(`data: ${JSON.stringify({
                        type: 'custom',
                        value: {
                          type: 'file',
                          ...data
                        }
                      })}\n\n`)
                    );
                    break;

                  case 'multi-agent':
                    // Multi-agent event
                    controller.enqueue(
                      encoder.encode(`data: ${JSON.stringify({
                        type: 'custom',
                        value: {
                          type: 'multi-agent',
                          ...data
                        }
                      })}\n\n`)
                    );
                    break;

                  case 'system':
                    // System messages (session init, etc)
                    if (data.subtype === 'init') {
                      console.log('[Backend] Session initialized:', data.session_id);
                    }
                    // Don't forward system messages to client
                    break;

                  case 'metadata':
                    // Metadata contains completion info
                    if (data.final_content || data.cost_usd || data.duration_ms) {
                      controller.enqueue(
                        encoder.encode(`data: ${JSON.stringify({
                          type: 'custom',
                          value: {
                            type: 'metadata',
                            final_content: data.final_content,
                            cost_usd: data.cost_usd,
                            duration_ms: data.duration_ms,
                            usage: data.usage
                          }
                        })}\n\n`)
                      );
                    }
                    break;

                  default:
                    // Log unhandled message types for debugging
                    console.log('[Backend Event] Unhandled msg_type:', msgType, data);
                }
              }
            } catch (e) {
              // Silently skip unparseable lines
            }
          }
        }
      },
      flush(controller) {
        // Send text-end and finish events
        if (textStarted) {
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify({ type: 'text-end', id: messageId })}\n\n`)
          );
        }
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify({ type: 'finish' })}\n\n`)
        );
        controller.enqueue(encoder.encode('data: [DONE]\n\n'));
      }
    });

    // Return transformed stream with required header
    if (response.body) {
      return new Response(response.body.pipeThrough(transformStream), {
        headers: {
          'Content-Type': 'text/event-stream; charset=utf-8',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
          'x-vercel-ai-ui-message-stream': 'v1', // CRITICAL: Required header for useChat
        }
      });
    } else {
      return new Response('No response body', { status: 500 });
    }

  } catch (error) {
    console.error('Chat API error:', error);
    const message = error instanceof Error ? error.message : 'Internal server error';
    return new Response(message, {
      status: 500,
      headers: { 'Content-Type': 'text/plain' }
    });
  }
}
