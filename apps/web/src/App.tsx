import { useState } from "react";
import { ChatHistory, type Message } from "./components/ChatHistory";
import { ChatInput } from "./components/ChatInput";
import { Sidebar } from "./components/Sidebar";
// import { HeroSearch } from "./components/HeroSearch";
import "./App.css";

function App() {
  const [messages, setMessages] = useState<Message[]>([
    { sender: "ai", message: "Hi! I’m your Mavik AI assistant. How can I help you today?" },
  ]);
  const [pending, setPending] = useState(false);
  const handleSend = async (text: string) => {
    setMessages((prev) => [...prev, { sender: "user", message: text }]);
    setPending(true);

    // TODO: Hook this up to your API Gateway + Lambda
    await new Promise((r) => setTimeout(r, 400));
    setMessages((prev) => [...prev, { sender: "ai", message: `You said: ${text}` }]);
    setPending(false);
  };

  return (
    <div className="h-screen flex bg-slate-900 text-slate-200">
      <Sidebar />
      <div className="flex-1 flex flex-col h-full">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-slate-900 border-b border-slate-700 px-4 py-3">
          <div className="max-w-[700px] mx-auto">
            <div className="font-bold text-lg text-center">Mavik AI</div>
          </div>
        </div>        {/* Messages Area - The ONLY scrollable section */}
        <div className="flex-1 overflow-hidden">
          <div className="max-w-[700px] mx-auto h-full px-4">
            <ChatHistory messages={messages} />
          </div>
        </div>

        {/* Input Bar - Sticky at bottom */}
        <div className="sticky bottom-0 bg-slate-900 border-t border-slate-700 px-4 py-4" style={{ paddingBottom: 'max(1rem, env(safe-area-inset-bottom))' }}>
          <div className="max-w-[700px] mx-auto">
            <ChatInput onSend={handleSend} disabled={pending} />
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
