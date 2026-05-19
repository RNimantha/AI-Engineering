import type { ToolCall } from "./types";

type ToolProgressProps = {
  isThinking: boolean;
  tools: ToolCall[];
};

/**
 * Displays per-turn tool activity and current execution state.
 */
export function ToolProgress({ isThinking, tools }: ToolProgressProps) {
  if (!tools.length) {
    return isThinking ? <p className="thinking-copy">Preparing response...</p> : null;
  }

  return (
    <div className="tool-stack" aria-live="polite">
      <p className="tool-progress-label">Tool activity</p>
      <div className="tool-progress">
        {tools.map((tool) => (
          <span
            key={tool.id}
            className={`tool-chip ${tool.status === "pending" ? "pending" : "completed"}`}
          >
            <span className="tool-chip-icon" aria-hidden="true">
              {tool.status === "pending" ? "..." : "OK"}
            </span>
            <span>{tool.name}</span>
            <span className="tool-chip-status">{tool.status}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
