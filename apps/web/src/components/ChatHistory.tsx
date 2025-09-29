import React, { useEffect, useRef } from "react";
import { ChatMessage } from "./ChatMessage";

export interface Message {
  message: string;
  sender: "user" | "ai";
  timestamp?: string;
}

interface ChatHistoryProps {
  messages: Message[];
}

export const ChatHistory: React.FC<ChatHistoryProps> = ({ messages }) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div ref={scrollRef} className="h-full overflow-y-auto py-4 scroll-smooth">
      <div className="space-y-4">
        {messages.map((msg, idx) => (
          <ChatMessage key={idx} message={msg.message} sender={msg.sender} timestamp={msg.timestamp} />
        ))}
      </div>
    </div>
  );
};
