'use client';

import { useState, useRef } from 'react';
import MessageList from './message-list';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!input.trim() && !file) return;

    setLoading(true);
    setDownloadUrl(null);

    const formData = new FormData();
    formData.append('message', input);
    if (file) formData.append('file', file);

    // Add user message
    setMessages(prev => [...prev, { role: 'user', content: input }]);
    setInput('');
    setFile(null);

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
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
            const data = JSON.parse(line.slice(6));

            if (data.type === 'tool') {
              console.log('Tool:', data);
            } else if (data.type === 'section') {
              sections.push(data);
              assistantMessage += `\n\n## ${data.title}\n\n${data.content}`;
            } else if (data.type === 'answer') {
              assistantMessage = data.content;
            } else if (data.type === 'artifact') {
              setDownloadUrl(data.url);
            }
          }
        }

        // Update assistant message in real-time
        setMessages(prev => {
          const newMessages = [...prev];
          const lastMsg = newMessages[newMessages.length - 1];

          if (lastMsg && lastMsg.role === 'assistant') {
            lastMsg.content = assistantMessage;
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
    <div className="flex-1 flex flex-col overflow-hidden">
      <MessageList messages={messages} />

      <div className="border-t bg-white p-4">
        <div className="max-w-4xl mx-auto space-y-3">
          {file && (
            <div className="flex items-center justify-between bg-blue-50 border border-blue-200 rounded-lg px-4 py-2">
              <span className="text-sm text-blue-700">
                📎 {file.name} ({(file.size / 1024).toFixed(1)} KB)
              </span>
              <button
                onClick={() => setFile(null)}
                className="text-blue-700 hover:text-blue-900"
              >
                ✕
              </button>
            </div>
          )}

          {downloadUrl && (
            <div className="flex items-center justify-between bg-green-50 border border-green-200 rounded-lg px-4 py-2">
              <span className="text-sm text-green-700">
                📄 Analysis report ready
              </span>
              <a
                href={downloadUrl}
                download
                className="bg-green-600 text-white px-4 py-1 rounded-md hover:bg-green-700 text-sm"
              >
                Download
              </a>
            </div>
          )}

          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask anything about CRE deals, or paste a pre-screening prompt..."
            rows={4}
            className="w-full border border-gray-300 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none text-gray-900 placeholder-gray-400"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit();
              }
            }}
          />

          <div className="flex gap-2">
            <label className="flex-1 border border-gray-300 rounded-lg px-4 py-2 cursor-pointer hover:bg-gray-50 transition">
              <input
                type="file"
                accept=".pdf"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="hidden"
              />
              <span className="text-gray-700">
                {file ? 'Change file' : '📎 Attach PDF'}
              </span>
            </label>

            <button
              onClick={handleSubmit}
              disabled={loading || (!input.trim() && !file)}
              className="bg-blue-600 text-white px-8 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition"
            >
              {loading ? 'Processing...' : 'Send'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
