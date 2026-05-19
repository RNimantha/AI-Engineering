import { useEffect, useRef } from "react";

import { ChatMessage } from "./ChatMessage";
import type { Message } from "./types";

type ChatMessagesProps = {
  isThinking: boolean;
  messages: Message[];
};

/**
 * Shows the conversation transcript and keeps the latest turn in view while streaming.
 */
export function ChatMessages({ isThinking, messages }: ChatMessagesProps) {
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [isThinking, messages]);

  return (
    <section className="messages" aria-live="polite">
      {messages.map((message, index) => (
        <ChatMessage
          key={message.id}
          isActive={index === messages.length - 1}
          isThinking={isThinking}
          message={message}
        />
      ))}
      <div ref={endRef} />
    </section>
  );
}
