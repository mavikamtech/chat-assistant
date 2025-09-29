import React from "react";

interface ChatMessageProps {
  message: string;
  sender: "user" | "ai";
  timestamp?: string;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message, sender, timestamp }) => {
  return (
    <div className={`flex ${sender === "user" ? "justify-end" : "justify-start"} fade-in`}>
      <div className="max-w-[70%]">
        <div
          className={`rounded-2xl px-4 py-2.5 text-[15px] shadow-lg whitespace-pre-wrap break-words ${
            sender === "user"
              ? "bg-accent text-slate-900"
              : "bg-slate-800 text-slate-200"
          }`}
        >
          {message}
        </div>
        {timestamp && (
          <div className={`text-xs text-slate-400 mt-1 ${sender === "user" ? "text-right" : "text-left"}`}>
            {timestamp}
          </div>
        )}
      </div>
    </div>
  );
};
