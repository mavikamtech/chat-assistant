import React from "react";
import { PlusIcon, GearIcon } from "./Icons";

export const Sidebar: React.FC = () => {
  return (
    <div className="w-56 bg-slate-800 text-slate-300 flex flex-col h-full border-r border-slate-700 overflow-y-auto">
      <div className="p-3 space-y-2">
        <div className="flex items-center gap-3 p-2.5 rounded-lg cursor-pointer bg-slate-900 border border-slate-700 hover:bg-slate-700 transition-colors">
          <PlusIcon />
          <span className="text-sm">New Chat</span>
        </div>
      </div>
      <div className="flex-1" />
      <div className="p-3">
        <div className="flex items-center gap-3 p-2.5 rounded-lg cursor-pointer hover:bg-slate-700 transition-colors">
          <GearIcon />
          <span className="text-sm">Settings</span>
        </div>
      </div>
    </div>
  );
};
