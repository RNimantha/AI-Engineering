import { useEffect, useRef, useState } from "react";

import { STARTER_PROMPTS } from "./config";
import { ChatInput } from "./ChatInput";
import { ChatMessages } from "./ChatMessages";
import type { Session } from "./types";
import { useChat } from "./useChat";

function ChevronDown() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

const DEFAULT_TITLE = "New session";
const MAX_TITLE_LEN = 42;

function deriveTitle(content: string): string {
  const trimmed = content.trim().replace(/\s+/g, " ");
  return trimmed.length > MAX_TITLE_LEN ? trimmed.slice(0, MAX_TITLE_LEN) + "…" : trimmed;
}

function getDateGroup(ts: number): string {
  const now = new Date();
  const d = new Date(ts);
  const diffDays = Math.floor((now.setHours(0, 0, 0, 0) - d.setHours(0, 0, 0, 0)) / 86_400_000);
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays <= 7) return "Previous 7 Days";
  return "Older";
}

const GROUP_ORDER = ["Today", "Yesterday", "Previous 7 Days", "Older"];

function groupSessions(sessions: Session[]): Map<string, Session[]> {
  const map = new Map<string, Session[]>();
  for (const s of sessions) {
    const g = getDateGroup(s.createdAt);
    if (!map.has(g)) map.set(g, []);
    map.get(g)!.push(s);
  }
  return map;
}

export function ChatContainer() {
  const { error, input, isThinking, messages, sessions, resetChat, loadSession, deleteSession, sendMessage, setInput } =
    useChat();
  const searchRef = useRef<HTMLInputElement>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [hoveredSessionId, setHoveredSessionId] = useState<string | null>(null);

  const firstUserMsg = messages.find((m) => m.role === "user");
  const sessionTitle = firstUserMsg ? deriveTitle(firstUserMsg.content) : DEFAULT_TITLE;

  useEffect(() => {
    document.title = firstUserMsg ? `${sessionTitle} — ClaudeSDK` : "ClaudeSDK";
  }, [sessionTitle, firstUserMsg]);

  function handleSearchNavClick() {
    searchRef.current?.focus();
    searchRef.current?.select();
  }

  const filteredSessions = searchQuery.trim()
    ? sessions.filter((s) => s.title.toLowerCase().includes(searchQuery.toLowerCase()))
    : sessions;

  const grouped = groupSessions(filteredSessions);

  const lastMsgPreview =
    messages.length > 1
      ? (messages[messages.length - 1].content.slice(0, 52) || "Working…")
      : "Pick a prompt or type a task";

  return (
    <div className="shell">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-top">
          <div className="logo-row">
            <div className="logo-icon">✦</div>
            <span className="logo-text">ClaudeSDK</span>
            <span className="logo-chevron">
              <ChevronDown />
            </span>
          </div>

          <button className="new-chat-btn" type="button" onClick={resetChat}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            New chat
            <span className="new-chat-spacer" />
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="7" height="7" rx="1" />
              <rect x="14" y="3" width="7" height="7" rx="1" />
              <rect x="3" y="14" width="7" height="7" rx="1" />
            </svg>
          </button>
        </div>

        <div className="search-wrap">
          <div className="search-inner">
            <span className="search-icon">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8" />
                <path d="m21 21-4.35-4.35" />
              </svg>
            </span>
            <input
              ref={searchRef}
              type="text"
              placeholder="Search chats..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button className="search-filter-btn" type="button" onClick={() => setSearchQuery("")} title="Clear">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            )}
          </div>
        </div>

        <nav className="chat-history">
          {/* Active (current) session — always at top under "Today" unless filtered out */}
          {!searchQuery && (
            <>
              <div className="history-group-label">Today</div>
              <div className="history-item active">
                <div className="history-item-title">{sessionTitle}</div>
                <div className="history-item-preview">{lastMsgPreview}</div>
              </div>
            </>
          )}

          {/* Archived sessions */}
          {GROUP_ORDER.map((group) => {
            const items = grouped.get(group);
            if (!items?.length) return null;
            return (
              <div key={group}>
                <div className="history-group-label">{group}</div>
                {items.map((session) => (
                  <div
                    key={session.id}
                    className="history-item history-item--archived"
                    onClick={() => loadSession(session.id)}
                    onMouseEnter={() => setHoveredSessionId(session.id)}
                    onMouseLeave={() => setHoveredSessionId(null)}
                  >
                    <div className="history-item-title">{session.title}</div>
                    <div className="history-item-preview">
                      {session.messages[session.messages.length - 1]?.content.slice(0, 52) || "—"}
                    </div>
                    {hoveredSessionId === session.id && (
                      <button
                        className="history-delete-btn"
                        type="button"
                        title="Delete session"
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteSession(session.id);
                        }}
                      >
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="3 6 5 6 21 6" />
                          <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                          <path d="M10 11v6M14 11v6" />
                          <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
                        </svg>
                      </button>
                    )}
                  </div>
                ))}
              </div>
            );
          })}

          {filteredSessions.length === 0 && searchQuery && (
            <div className="history-empty">No chats match "{searchQuery}"</div>
          )}

          {sessions.length === 0 && !searchQuery && (
            <div className="history-empty">Previous sessions appear here</div>
          )}
        </nav>

        <div className="user-profile">
          <div className="user-avatar">CS</div>
          <div className="user-info">
            <div className="user-name">Claude SDK</div>
            <div className="user-email">demo@localhost</div>
          </div>
          <button className="user-more-btn" type="button" onClick={resetChat} title="New chat">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          </button>
        </div>
      </aside>

      {/* Main area */}
      <div className="main-wrap">
        {/* Top nav */}
        <header className="top-nav">
          <div className="workspace-selector">
            <span className="workspace-name">Agent Workspace</span>
            <span className="workspace-chevron">
              <ChevronDown />
            </span>
          </div>

          <div className="nav-actions">
            <span className="pro-badge">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
              </svg>
              Local
            </span>
            <button
              className="nav-icon-btn"
              type="button"
              title="Focus search"
              onClick={handleSearchNavClick}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8" />
                <path d="m21 21-4.35-4.35" />
              </svg>
            </button>
            <button className="nav-icon-btn" type="button" title="New chat" onClick={resetChat}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="1 4 1 10 7 10" />
                <path d="M3.51 15a9 9 0 1 0 .49-3" />
              </svg>
            </button>
            <div className="nav-avatar" title="Claude SDK demo">CS</div>
          </div>
        </header>

        {/* Chat title bar */}
        <div className="chat-title-bar">
          <div className="chat-title-group">
            <span className="chat-title-text">{sessionTitle}</span>
          </div>

          <div className="chat-title-actions">
            <button
              className="chat-action-btn share"
              type="button"
              title="Copy session link"
              onClick={() => {
                void navigator.clipboard.writeText(window.location.href);
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="18" cy="5" r="3" />
                <circle cx="6" cy="12" r="3" />
                <circle cx="18" cy="19" r="3" />
                <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
                <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
              </svg>
              Share
            </button>
            <button className="chat-action-btn" type="button" title="New chat" onClick={resetChat}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="1 4 1 10 7 10" />
                <path d="M3.51 15a9 9 0 1 0 .49-3" />
              </svg>
            </button>
            <button
              className="chat-action-btn"
              type="button"
              title={`${messages.length} message${messages.length !== 1 ? "s" : ""} in session`}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
              <span className="chat-action-count">{messages.length}</span>
            </button>
          </div>
        </div>

        <ChatMessages isThinking={isThinking} messages={messages} />
        <ChatInput
          disabled={isThinking}
          error={error}
          onChange={setInput}
          onSend={sendMessage}
          prompts={STARTER_PROMPTS}
          value={input}
        />
      </div>
    </div>
  );
}
