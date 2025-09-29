import React from "react";

export const PlusIcon: React.FC<{ size?: number; color?: string }> = ({ size = 18, color = "#cbd5e1" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 5v14M5 12h14" stroke={color} strokeWidth="2" strokeLinecap="round" />
  </svg>
);

export const MicIcon: React.FC<{ size?: number; color?: string }> = ({ size = 18, color = "#cbd5e1" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3Z" stroke={color} strokeWidth="2" />
    <path d="M19 11a7 7 0 0 1-14 0" stroke={color} strokeWidth="2" strokeLinecap="round" />
    <path d="M12 18v3" stroke={color} strokeWidth="2" strokeLinecap="round" />
  </svg>
);

export const WaveIcon: React.FC<{ size?: number; color?: string }> = ({ size = 20, color = "#cbd5e1" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M3 12c2-2 4 2 6 0s4-4 6 0 4 2 6 0" stroke={color} strokeWidth="2" strokeLinecap="round" />
  </svg>
);

export const MenuIcon: React.FC<{ size?: number; color?: string }> = ({ size = 20, color = "#cbd5e1" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M4 6h16M4 12h16M4 18h10" stroke={color} strokeWidth="2" strokeLinecap="round" />
  </svg>
);

export const ChatIcon: React.FC<{ size?: number; color?: string }> = ({ size = 20, color = "#cbd5e1" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M21 12a8 8 0 1 1-4.9-7.4L21 3l-1.6 4.9A7.96 7.96 0 0 1 21 12Z" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const PaperPlaneIcon: React.FC<{ size?: number; color?: string }> = ({ size = 18, color = "#e5e7eb" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M22 2L11 13" stroke={color} strokeWidth="2" strokeLinecap="round" />
    <path d="M22 2l-7 20-4-9-9-4 20-7Z" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const ClipIcon: React.FC<{ size?: number; color?: string }> = ({ size = 18, color = "#e5e7eb" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M21.44 11.05 12.5 20a6 6 0 1 1-8.49-8.49l9.19-9.2a4 4 0 1 1 5.66 5.66L9.4 17.43a2 2 0 1 1-2.83-2.83l8.49-8.49" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const GearIcon: React.FC<{ size?: number; color?: string }> = ({ size = 18, color = "#cbd5e1" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" stroke={color} strokeWidth="2" />
    <path d="m19.4 15-1 .6a2 2 0 0 0-.7 2.7l.5 1a2 2 0 0 1-1.7 2.9h-1.2a2 2 0 0 1-1.9-1.4l-.3-1a2 2 0 0 0-2.4-1.4h-1a2 2 0 0 0-2 2v1.2a2 2 0 0 1-2.9 1.7l-1-.5a2 2 0 0 1-1-2.6l.6-1a2 2 0 0 0-1-2.6l-1-.6a2 2 0 0 1 0-3.4l1-.6a2 2 0 0 0 1-2.6l-.6-1a2 2 0 0 1 1-2.6l1-.5a2 2 0 0 1 2.6 1l.6 1a2 2 0 0 0 2.6 1l1-.6a2 2 0 0 0 1-2.6l-.5-1a2 2 0 0 1 2.6-1l1 .6a2 2 0 0 1 1 2.6l-.6 1a2 2 0 0 0 1 2.6l1 .6a2 2 0 0 1 0 3.4Z" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
