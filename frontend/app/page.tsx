'use client';

import ChatInterface from '@/components/chat-interface';

export default function Home() {
  return (
    <main className="h-screen flex flex-col bg-gray-50">
      <header className="border-b bg-white px-6 py-4 shadow-sm">
        <h1 className="text-2xl font-bold text-gray-800">Mavik AI Assistant</h1>
        <p className="text-sm text-gray-500">Commercial Real Estate Deal Analysis</p>
      </header>
      <ChatInterface />
    </main>
  );
}
