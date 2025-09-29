import { useState } from "react";
import { ChatHistory, type Message } from "../components/ChatHistory";
import { ChatInput } from "../components/ChatInput";

export default function HomePage() {
  const [messages, setMessages] = useState<Message[]>([
    { sender: "ai", message: "Hi! I’m your Mavik AI assistant. How can I help you today?" },
  ]);
  const [pending, setPending] = useState(false);

  const handleSend = async (text: string) => {
    setMessages((prev) => [...prev, { sender: "user", message: text }]);
    setPending(true);

    // TODO: Replace this mock with a real API call to your backend
    await new Promise((r) => setTimeout(r, 500));
    setMessages((prev) => [
      ...prev,
      { sender: "ai", message: `You said: ${text}` },
    ]);

    setPending(false);
  };

  const wrapperStyle: React.CSSProperties = { minHeight: "100vh", background: "#f3f4f6" };
  const containerStyle: React.CSSProperties = { maxWidth: 768, margin: "0 auto", padding: 16 };
  const titleStyle: React.CSSProperties = { fontSize: 24, fontWeight: 700, marginBottom: 16 };

  return (
    <div style={wrapperStyle}>
      <div style={containerStyle}>
        <h1 style={titleStyle}>Mavik AI Chat</h1>
        <ChatHistory messages={messages} />
        <ChatInput onSend={handleSend} disabled={pending} />
      </div>
    </div>
  );
}
