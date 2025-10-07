'use client';

import { useState, useRef, useEffect } from 'react';
import { useSession, signOut } from 'next-auth/react';
import MessageList from './message-list';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  fileName?: string;
  isLoading?: boolean;
}

export default function ChatInterface() {
  const { data: session } = useSession();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  }, [input]);

  const handleSubmit = async () => {
    if (!input.trim() && !file) return;

    setLoading(true);
    setDownloadUrl(null);

    const formData = new FormData();
    formData.append('message', input);
    const currentFileName = file?.name;
    if (file) formData.append('file', file);

    // Add user message with file name if attached
    setMessages(prev => [...prev, {
      role: 'user',
      content: input,
      fileName: currentFileName
    }]);

    // Add loading message
    setMessages(prev => [...prev, {
      role: 'assistant',
      content: "....",
      isLoading: true
    }]);

    setInput('');
    setFile(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || '/api/chat';
      const response = await fetch(apiUrl, {
        method: 'POST',
        body: formData,
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      let assistantMessage = '';
      let sections: any[] = [];

      while (true) {
        const { done, value } = await reader!.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              console.log('Received data:', data);

              if (data.type === 'tool') {
                console.log('Tool:', data);
                if (data.status === 'failed') {
                  assistantMessage += `\n\n⚠️ **Tool Error (${data.tool})**: ${data.summary}\n`;
                }
              } else if (data.type === 'section') {
                sections.push(data);
                assistantMessage += `\n\n## ${data.title}\n\n${data.content}`;
              } else if (data.type === 'answer') {
                assistantMessage = data.content;
              } else if (data.type === 'artifact') {
                setDownloadUrl(data.url);
              }
            } catch (e) {
              console.error('Error parsing JSON:', e, 'Line:', line);
            }
          }
        }

        // Update assistant message in real-time
        setMessages(prev => {
          const newMessages = [...prev];
          const lastMsg = newMessages[newMessages.length - 1];

          if (lastMsg && lastMsg.role === 'assistant') {
            lastMsg.content = assistantMessage;
            lastMsg.isLoading = false;
          } else {
            newMessages.push({ role: 'assistant', content: assistantMessage });
          }

          return newMessages;
        });
      }
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, there was an error processing your request.'
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-[#343541]">
      {/* Sidebar */}
      <div className="hidden md:flex md:w-[260px] md:flex-col bg-[#202123]">
        <div className="flex-1 overflow-y-auto">
          <div className="p-2">
            <button className="flex w-full items-center gap-3 rounded-lg border border-white/20 px-3 py-3 text-sm text-white transition-colors hover:bg-gray-500/10">
              <svg stroke="currentColor" fill="none" strokeWidth="2" viewBox="0 0 24 24" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4" height="1em" width="1em" xmlns="http://www.w3.org/2000/svg">
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <line x1="5" y1="12" x2="19" y2="12"></line>
              </svg>
              New chat
            </button>
          </div>
        </div>
        <div className="border-t border-white/20 p-3">
          <div className="mb-3">
            <div className="text-xs text-white/70 mb-1">
              {session?.user?.name || session?.user?.email}
            </div>
            <button
              onClick={() => signOut({ callbackUrl: '/auth/signin' })}
              className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-white/70 transition-colors hover:bg-white/10"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
              Sign out
            </button>
          </div>
          <div className="text-xs text-gray-400 text-center">
            Mavik AI Assistant
            <br />
            <span className="text-[10px]">Commercial Real Estate Analysis</span>
          </div>
        </div>
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col relative">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <div className="flex h-full items-center justify-center">
              <div className="text-center px-4">
                <h1 className="text-4xl font-semibold text-white mb-8">Mavik AI Assistant</h1>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl mx-auto">
                  <div
                    onClick={() => setInput('Analyze this OM and extract metrics, sponsor info, and generate a pre-screening report')}
                    className="bg-[#444654] rounded-lg p-4 hover:bg-[#505060] transition-colors cursor-pointer"
                  >
                    <div className="text-white/90 text-sm">
                      <div className="font-medium mb-2">📊 Analyze OM</div>
                      <div className="text-white/70 text-xs">Extract metrics, sponsor info, and generate pre-screening report</div>
                    </div>
                  </div>
                  <div
                    onClick={() => setInput('Extract key terms including sponsor, DSCR, LTV, business plan, and other key data')}
                    className="bg-[#444654] rounded-lg p-4 hover:bg-[#505060] transition-colors cursor-pointer"
                  >
                    <div className="text-white/90 text-sm">
                      <div className="font-medium mb-2">📝 Extract Key Terms</div>
                      <div className="text-white/70 text-xs">Get sponsor, DSCR, LTV, business plan, and other key data</div>
                    </div>
                  </div>
                  <div
                    onClick={() => setInput('Research the sponsor and find their track record, past deals, and market reputation')}
                    className="bg-[#444654] rounded-lg p-4 hover:bg-[#505060] transition-colors cursor-pointer"
                  >
                    <div className="text-white/90 text-sm">
                      <div className="font-medium mb-2">🔍 Research Sponsor</div>
                      <div className="text-white/70 text-xs">Find track record, past deals, and market reputation</div>
                    </div>
                  </div>
                  <div
                    onClick={() => setInput('Calculate financial metrics: DSCR, LTV, Cap Rate, IRR, and other calculations')}
                    className="bg-[#444654] rounded-lg p-4 hover:bg-[#505060] transition-colors cursor-pointer"
                  >
                    <div className="text-white/90 text-sm">
                      <div className="font-medium mb-2">📈 Calculate Metrics</div>
                      <div className="text-white/70 text-xs">DSCR, LTV, Cap Rate, IRR, and other financial calculations</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <MessageList messages={messages} downloadUrl={downloadUrl} />
          )}
        </div>

        {/* Input area */}
        <div className="border-t border-white/20 bg-[#343541]">
          <div className="mx-auto max-w-3xl px-4 py-4">
            {file && (
              <div className="mb-3 flex items-center justify-between bg-[#40414f] rounded-lg px-4 py-2 border border-white/10">
                <span className="text-sm text-white/90">
                  📎 {file.name} <span className="text-white/50">({(file.size / 1024).toFixed(1)} KB)</span>
                </span>
                <button
                  onClick={() => setFile(null)}
                  className="text-white/70 hover:text-white"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            )}

            <div className="relative flex items-end gap-2">
              {/* Attach button */}
              <label className="flex items-center justify-center w-10 h-10 rounded-lg hover:bg-white/10 transition-colors cursor-pointer text-white/70 hover:text-white">
                <input
                  type="file"
                  accept=".pdf"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="hidden"
                />
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                </svg>
              </label>

              {/* Textarea */}
              <div className="flex-1 relative">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Message Mavik AI..."
                  rows={1}
                  className="w-full bg-[#40414f] border border-white/10 rounded-xl px-4 py-3 pr-12 text-white placeholder-white/40 focus:outline-none focus:border-white/30 resize-none max-h-52 overflow-y-auto"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSubmit();
                    }
                  }}
                  style={{ minHeight: '52px' }}
                />

                {/* Send button */}
                <button
                  onClick={handleSubmit}
                  disabled={loading || (!input.trim() && !file)}
                  className="absolute right-2 bottom-2 p-2 rounded-lg bg-white text-gray-900 hover:bg-white/90 disabled:bg-white/10 disabled:text-white/40 disabled:cursor-not-allowed transition-colors"
                >
                  {loading ? (
                    <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  ) : (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            <p className="text-xs text-white/40 text-center mt-3">
              Mavik AI can make mistakes. Verify important information.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
