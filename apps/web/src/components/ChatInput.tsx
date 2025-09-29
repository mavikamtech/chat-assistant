import React, { useState } from "react";
import { MicIcon, PaperPlaneIcon, ClipIcon } from "./Icons";

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({ onSend, disabled }) => {
  const [text, setText] = useState("");

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed) return;
    onSend(trimmed);
    setText("");
  };

  const onKeyDown: React.KeyboardEventHandler<HTMLTextAreaElement> = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex justify-center">
      <div className={`flex items-center gap-2.5 bg-slate-800 border border-slate-700 rounded-3xl p-3 w-full max-w-4xl shadow-2xl ${
        disabled ? 'opacity-70' : ''
      }`}>
        <button
          className="w-7 h-7 flex items-center justify-center rounded-full bg-slate-900 border border-slate-700 hover:bg-slate-700 transition-colors"
          title="Attach"
        >
          <ClipIcon size={14} />
        </button>

        <textarea
          className="flex-1 bg-transparent border-none text-slate-200 outline-none text-sm resize-none placeholder-slate-400"
          placeholder="Ask me anything…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={disabled}
          rows={1}
          style={{ minHeight: '24px', maxHeight: '160px' }}
        />

        <button
          className="w-7 h-7 flex items-center justify-center rounded-full bg-slate-900 border border-slate-700 hover:bg-slate-700 transition-colors"
          title="Voice"
        >
          <MicIcon size={14} />
        </button>

        <button
          className="w-7 h-7 flex items-center justify-center rounded-full bg-accent border border-accent hover:opacity-80 transition-opacity"
          title="Send"
          onClick={handleSend}
          disabled={disabled || !text.trim()}
        >
          <PaperPlaneIcon size={14} color="#0b1220" />
        </button>
      </div>
    </div>
  );
};
