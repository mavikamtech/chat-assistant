'use client';

import { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  fileName?: string;
  isLoading?: boolean;
}

interface MessageListProps {
  messages: Message[];
  downloadUrl?: string | null;
}

export default function MessageList({ messages, downloadUrl }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto">
      {messages.map((message, index) => (
        <div
          key={index}
          className={`border-b border-white/10 ${
            message.role === 'assistant' ? 'bg-[#444654]' : 'bg-[#343541]'
          }`}
        >
          <div className="max-w-3xl mx-auto px-4 py-6">
            <div className="flex gap-6">
              {/* Avatar */}
              <div className="flex-shrink-0">
                <div
                  className={`w-8 h-8 rounded-sm flex items-center justify-center text-white ${
                    message.role === 'user' ? 'bg-[#5436DA]' : 'bg-[#19c37d]'
                  }`}
                >
                  {message.role === 'user' ? (
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                    </svg>
                  ) : (
                    // Building/Real Estate icon for Mavik AI
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z" />
                    </svg>
                  )}
                </div>
              </div>

              {/* Message content */}
              <div className="flex-1 overflow-hidden">
                {/* Show attached file name for user messages */}
                {message.role === 'user' && message.fileName && (
                  <div className="mb-3 flex items-center gap-2 bg-[#40414f] rounded-lg px-3 py-2 border border-white/10 w-fit">
                    <svg className="w-4 h-4 text-white/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <span className="text-xs text-white/90">{message.fileName}</span>
                  </div>
                )}

                <div className="text-sm text-white/90 prose prose-invert max-w-none">
                  {message.isLoading ? (
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      <span>{message.content}</span>
                    </div>
                  ) : (
                    <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      // Customize markdown rendering
                      h1: ({node, ...props}) => <h1 className="text-2xl font-bold mt-4 mb-2" {...props} />,
                      h2: ({node, ...props}) => <h2 className="text-xl font-bold mt-3 mb-2" {...props} />,
                      h3: ({node, ...props}) => <h3 className="text-lg font-bold mt-2 mb-1" {...props} />,
                      p: ({node, ...props}) => <p className="mb-2 leading-7" {...props} />,
                      ul: ({node, ...props}) => <ul className="list-disc ml-4 mb-2" {...props} />,
                      ol: ({node, ...props}) => <ol className="list-decimal ml-4 mb-2" {...props} />,
                      code: ({node, inline, ...props}: any) =>
                        inline ? (
                          <code className="bg-black/30 px-1 py-0.5 rounded text-sm" {...props} />
                        ) : (
                          <code className="block bg-black/30 p-3 rounded-lg overflow-x-auto my-2" {...props} />
                        ),
                      pre: ({node, ...props}) => <pre className="bg-black/30 p-3 rounded-lg overflow-x-auto my-2" {...props} />,
                      table: ({node, ...props}) => (
                        <div className="overflow-x-auto my-2">
                          <table className="border-collapse border border-white/20" {...props} />
                        </div>
                      ),
                      th: ({node, ...props}) => <th className="border border-white/20 px-3 py-1.5 bg-white/5" {...props} />,
                      td: ({node, ...props}) => <td className="border border-white/20 px-3 py-1.5" {...props} />,
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                  )}
                </div>

                {/* Download button for artifacts */}
                {message.role === 'assistant' && downloadUrl && index === messages.length - 1 && (
                  <div className="mt-4 pt-3 border-t border-white/10">
                    <a
                      href={downloadUrl}
                      download
                      className="inline-flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm transition-colors"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      Download Word Report
                    </a>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
}
