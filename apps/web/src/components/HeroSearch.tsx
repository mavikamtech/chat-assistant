import React, { useRef } from "react";
import { PlusIcon, MicIcon, WaveIcon } from "./Icons";

interface HeroSearchProps {
  onSubmit: (text: string) => void;
}

export const HeroSearch: React.FC<HeroSearchProps> = ({ onSubmit }) => {
  const inputRef = useRef<HTMLInputElement | null>(null);

  const pill: React.CSSProperties = {
    display: "flex",
    alignItems: "center",
    gap: 10,
    background: "#111827",
    border: "1px solid #1f2937",
    borderRadius: 24,
    padding: "10px 14px",
    minWidth: 500,
    maxWidth: 720,
    color: "#e5e7eb",
  };
  const input: React.CSSProperties = {
    flex: 1,
    background: "transparent",
    border: "none",
    color: "#e5e7eb",
    outline: "none",
    fontSize: 14,
  };

  const iconBtn: React.CSSProperties = {
    width: 28,
    height: 28,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 999,
    background: "#0b1220",
    border: "1px solid #1f2937",
    cursor: "pointer",
  };

  const onKeyDown: React.KeyboardEventHandler<HTMLInputElement> = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      const text = inputRef.current?.value?.trim() || "";
      if (text) onSubmit(text);
    }
  };

  return (
    <div style={{ textAlign: "center", color: "#e5e7eb" }}>
      <div style={{ fontSize: 28, marginBottom: 20 }}>What can I help with?</div>
      <div style={{ display: "flex", justifyContent: "center" }}>
        <div style={pill}>
          <div style={iconBtn}><PlusIcon size={14} /></div>
          <input ref={inputRef} style={input} placeholder="Ask anything" onKeyDown={onKeyDown} />
          <div style={iconBtn}><MicIcon size={14} /></div>
          <div style={iconBtn}><WaveIcon size={14} /></div>
        </div>
      </div>
    </div>
  );
};
