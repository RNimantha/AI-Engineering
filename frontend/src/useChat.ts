import { startTransition, useEffect, useRef, useState } from "react";

import { CHAT_API_URL, INITIAL_MESSAGES } from "./config";
import type { ChatTurn, EventItem, Message, Session } from "./types";

const SESSIONS_KEY = "claudesdk_sessions";
const MAX_SESSIONS = 50;
const MAX_TITLE_LEN = 42;

type UseChatResult = {
  error: string;
  input: string;
  isThinking: boolean;
  messages: Message[];
  sessions: Session[];
  resetChat: () => void;
  loadSession: (id: string) => void;
  deleteSession: (id: string) => void;
  sendMessage: (content: string) => Promise<void>;
  setInput: (value: string) => void;
};

function readSessions(): Session[] {
  try {
    const raw = localStorage.getItem(SESSIONS_KEY);
    return raw ? (JSON.parse(raw) as Session[]) : [];
  } catch {
    return [];
  }
}

function writeSessions(sessions: Session[]) {
  try {
    localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions));
  } catch {
    // storage quota exceeded — silently drop oldest
  }
}

function deriveTitle(content: string): string {
  const trimmed = content.trim().replace(/\s+/g, " ");
  return trimmed.length > MAX_TITLE_LEN ? trimmed.slice(0, MAX_TITLE_LEN) + "…" : trimmed;
}

function freshInitialMessages(): Message[] {
  return INITIAL_MESSAGES.map((m) => ({ ...m, timestamp: Date.now() }));
}

function getAssistantText(events: EventItem[]) {
  return events
    .filter((event) => event.type === "assistant")
    .map((event) => event.content)
    .join("\n\n");
}

function parseSseLine(line: string) {
  if (!line.startsWith("data: ")) return null;

  const raw = line.slice(6).trim();
  if (raw === "[DONE]") return "done";

  try {
    return JSON.parse(raw) as EventItem;
  } catch {
    return null;
  }
}

/**
 * Manages chat history and request-scoped streaming updates from the FastAPI backend.
 * Sessions are persisted to localStorage so history survives page refresh.
 * The backend returns an SSE-formatted response body over POST, so cleanup is handled
 * by aborting the active fetch rather than closing a persistent EventSource.
 */
export function useChat(): UseChatResult {
  const [messages, setMessages] = useState<Message[]>(freshInitialMessages);
  const [sessions, setSessions] = useState<Session[]>(readSessions);
  const [input, setInput] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [error, setError] = useState("");
  const abortRef = useRef<AbortController | null>(null);
  const messagesRef = useRef(messages);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  function archiveCurrentSession() {
    const current = messagesRef.current;
    const firstUser = current.find((m) => m.role === "user");
    if (!firstUser) return; // nothing worth saving

    const session: Session = {
      id: crypto.randomUUID(),
      title: deriveTitle(firstUser.content),
      messages: current,
      createdAt: Date.now(),
    };

    setSessions((prev) => {
      const updated = [session, ...prev].slice(0, MAX_SESSIONS);
      writeSessions(updated);
      return updated;
    });
  }

  function resetChat() {
    abortRef.current?.abort();
    abortRef.current = null;
    archiveCurrentSession();
    setMessages(freshInitialMessages());
    setInput("");
    setError("");
    setIsThinking(false);
  }

  function loadSession(id: string) {
    const session = sessions.find((s) => s.id === id);
    if (!session) return;
    abortRef.current?.abort();
    abortRef.current = null;
    archiveCurrentSession();
    setMessages(session.messages);
    setInput("");
    setError("");
    setIsThinking(false);
  }

  function deleteSession(id: string) {
    setSessions((prev) => {
      const updated = prev.filter((s) => s.id !== id);
      writeSessions(updated);
      return updated;
    });
  }

  /**
   * Sends one user turn and applies streamed assistant/tool events onto a placeholder response.
   */
  async function sendMessage(content: string) {
    const trimmed = content.trim();
    if (!trimmed || isThinking) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
      timestamp: Date.now(),
    };
    const assistantId = crypto.randomUUID();
    const nextMessages = [...messagesRef.current, userMessage];

    setMessages([
      ...nextMessages,
      { id: assistantId, role: "assistant", content: "", events: [], timestamp: Date.now() },
    ]);
    setInput("");
    setError("");
    setIsThinking(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch(CHAT_API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: nextMessages.map((message): ChatTurn => ({
            role: message.role,
            content: message.content,
          })),
        }),
        signal: controller.signal,
      });

      if (!response.ok) throw new Error(`Request failed: ${response.status}`);
      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let isDone = false;

      while (!isDone) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          const parsed = parseSseLine(line);
          if (parsed === "done") {
            isDone = true;
            break;
          }
          if (!parsed) continue;

          startTransition(() => {
            setMessages((current) =>
              current.map((message) => {
                if (message.id !== assistantId) return message;

                const updatedEvents = [...(message.events ?? []), parsed];
                return {
                  ...message,
                  content: getAssistantText(updatedEvents),
                  events: updatedEvents,
                };
              }),
            );
          });
        }
      }
    } catch (requestError) {
      if (requestError instanceof Error && requestError.name === "AbortError") return;

      const message =
        requestError instanceof Error ? requestError.message : "The chat request failed.";
      setError(message);
      setMessages((current) => current.filter((message) => message.id !== assistantId));
    } finally {
      setIsThinking(false);
      abortRef.current = null;
    }
  }

  return {
    error,
    input,
    isThinking,
    messages,
    sessions,
    resetChat,
    loadSession,
    deleteSession,
    sendMessage,
    setInput,
  };
}
