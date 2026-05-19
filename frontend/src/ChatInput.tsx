import type { FormEvent, KeyboardEvent } from "react";

type ChatInputProps = {
  disabled: boolean;
  error: string;
  onChange: (value: string) => void;
  onSend: (content: string) => Promise<void>;
  prompts: string[];
  value: string;
};

export function ChatInput({ disabled, error, onChange, onSend, prompts, value }: ChatInputProps) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void onSend(value);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void onSend(value);
    }
  }

  return (
    <footer className="composer-wrap">
      <div className="prompt-strip" aria-label="Prompt suggestions">
        {prompts.map((prompt) => (
          <button
            key={prompt}
            className="prompt-chip"
            disabled={disabled}
            onClick={() => void onSend(prompt)}
            type="button"
          >
            {prompt}
          </button>
        ))}
      </div>

      <form className="composer" onSubmit={handleSubmit}>
        <textarea
          id="prompt"
          rows={2}
          placeholder="Message ClaudeSDK..."
          value={value}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
        />
        <div className="composer-toolbar">
          <div className="composer-left-tools">
            <button className="composer-tool-btn" type="button" title="Attach file" disabled={disabled}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
              </svg>
            </button>
            <button className="composer-tool-btn" type="button" title="Web" disabled={disabled}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="2" y1="12" x2="22" y2="12" />
                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
              </svg>
            </button>
          </div>

          <div className="composer-right-tools">
            <button className="composer-feature-btn" type="button" disabled={disabled}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
              </svg>
              Enhance
            </button>
            <button className="composer-tool-btn" type="button" title="Voice input" disabled={disabled}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                <line x1="12" y1="19" x2="12" y2="23" />
                <line x1="8" y1="23" x2="16" y2="23" />
              </svg>
            </button>
            <button
              className="send-btn"
              disabled={disabled || !value.trim()}
              type="submit"
              title={disabled ? "Working..." : "Send message"}
            >
              {disabled ? (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="3" width="18" height="18" rx="3" />
                </svg>
              ) : (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" fill="currentColor" stroke="none" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </form>

      {error && <div className="error-banner">{error}</div>}

      <div className="composer-disclaimer">
        ClaudeSDK can make mistakes. Consider verifying important information.
      </div>
    </footer>
  );
}
