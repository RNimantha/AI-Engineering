import {
  Bot,
  Database,
  FolderClosed,
  KeyRound,
  LayoutGrid,
  LibraryBig,
  LogOut,
  Settings,
} from "lucide-react";

import { navItems } from "../data";

const navIcons = [LayoutGrid, FolderClosed, Database, LibraryBig, KeyRound, Settings];

export function LeftNavigation() {
  return (
    <aside className="flex min-h-[24rem] flex-col rounded-2xl border border-slate-800/60 bg-gradient-to-b from-slate-950/95 via-slate-950/85 to-slate-900/90 p-4 shadow-glow md:min-h-0">
      <div className="mb-6 flex items-center justify-between">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-indigo-400/30 bg-gradient-to-br from-indigo-500/35 via-purple-500/20 to-cyan-400/20">
          <Bot className="h-5 w-5 text-indigo-300" />
        </div>
        <button
          type="button"
          className="rounded-lg border border-slate-700/70 p-2 text-slate-400 transition-all duration-200 hover:border-slate-500 hover:text-slate-200"
          aria-label="Log out"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>

      <nav className="space-y-1.5" aria-label="Primary">
        {navItems.map((item, index) => {
          const Icon = navIcons[index];
          return (
            <button
              key={item.label}
              type="button"
              className={[
                "flex w-full items-center gap-3 rounded-xl border px-3 py-2.5 text-left text-sm font-medium transition-all duration-200",
                item.active
                  ? "border-indigo-400/35 bg-indigo-500/15 text-slate-100 shadow-[0_0_0_1px_rgba(129,140,248,0.22)]"
                  : "border-transparent text-slate-400 hover:border-slate-800/70 hover:bg-slate-900/80 hover:text-slate-200",
              ].join(" ")}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="mt-auto pt-5">
        <button
          type="button"
          className="flex w-full items-center gap-3 rounded-xl border border-slate-800/70 bg-slate-900/75 px-3 py-2.5 text-sm font-medium text-slate-300 transition-all duration-200 hover:border-slate-700 hover:bg-slate-900 hover:text-slate-100"
        >
          <Settings className="h-4 w-4" />
          <span>Settings</span>
        </button>
      </div>
    </aside>
  );
}
