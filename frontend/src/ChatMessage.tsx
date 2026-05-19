import { useState } from "react";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import type { Message } from "./types";
import { getToolCalls } from "./utils";

type ChatMessageProps = {
  isActive: boolean;
  isThinking: boolean;
  message: Message;
};

function AssistantAvatar() {
  return <div className="msg-avatar">✦</div>;
}

function CopyIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="9" y="9" width="13" height="13" rx="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

function ThumbUpIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z" />
      <path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
    </svg>
  );
}

function ThumbDownIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3H10z" />
      <path d="M17 2h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17" />
    </svg>
  );
}

function MoreIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="5" cy="12" r="1" fill="currentColor" />
      <circle cx="12" cy="12" r="1" fill="currentColor" />
      <circle cx="19" cy="12" r="1" fill="currentColor" />
    </svg>
  );
}

function TypingIndicator() {
  return (
    <div className="typing-indicator">
      <div className="typing-dot" />
      <div className="typing-dot" />
      <div className="typing-dot" />
    </div>
  );
}

export function ChatMessage({ isActive, isThinking, message }: ChatMessageProps) {
  const isAssistant = message.role === "assistant";
  const tools = isAssistant ? getToolCalls(message.events ?? [], isActive && isThinking) : [];
  const showTyping = isAssistant && isActive && isThinking && !message.content && tools.length === 0;
  const [copied, setCopied] = useState(false);

  const timestamp = message.timestamp
    ? new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : null;

  function handleCopy() {
    if (!message.content) return;
    void navigator.clipboard.writeText(message.content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  if (isAssistant) {
    return (
      <div className="message-row assistant">
        <AssistantAvatar />
        <div className="msg-content-wrap">
          {tools.length > 0 && (
            <div className="tool-stack">
              {tools.map((tool) => (
                <span key={tool.id} className={`tool-chip ${tool.status}`}>
                  {tool.status === "pending" ? "⟳" : "✓"} {tool.name}
                </span>
              ))}
            </div>
          )}
          {showTyping && <TypingIndicator />}
          {message.content && (
            <div className="msg-bubble msg-bubble--md">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </div>
          )}
          <div className="msg-meta">
            {timestamp && <span>{timestamp}</span>}
            <div className="msg-actions">
              <button
                className={`msg-action-btn${copied ? " copied" : ""}`}
                type="button"
                title={copied ? "Copied!" : "Copy response"}
                onClick={handleCopy}
                disabled={!message.content}
              >
                {copied ? (
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                ) : (
                  <CopyIcon />
                )}
              </button>
              <button className="msg-action-btn" type="button" title="Helpful">
                <ThumbUpIcon />
              </button>
              <button className="msg-action-btn" type="button" title="Not helpful">
                <ThumbDownIcon />
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="message-row user">
      <div className="msg-content-wrap">
        <div className="msg-bubble">{message.content}</div>
        <div className="msg-meta">
          {timestamp && <span>{timestamp}</span>}
          <span className="msg-check">✓✓</span>
        </div>
      </div>
    </div>
  );
}
