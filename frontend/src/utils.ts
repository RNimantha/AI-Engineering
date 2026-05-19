import type { EventItem, ToolCall } from "./types";

/**
 * Derives visible tool-call state from streamed assistant events.
 * The backend emits tool names as they are invoked and finishes the turn with
 * assistant text and a result event, so pending/completed state is inferred.
 */
export function getToolCalls(events: EventItem[], isStreaming: boolean): ToolCall[] {
  const toolCalls: ToolCall[] = [];

  for (const event of events) {
    if (event.type === "tool") {
      for (let index = toolCalls.length - 1; index >= 0; index -= 1) {
        if (toolCalls[index].status === "pending") {
          toolCalls[index].status = "completed";
          break;
        }
      }

      toolCalls.push({
        id: `${toolCalls.length}-${event.content}`,
        name: event.content,
        status: "pending",
      });
      continue;
    }

    if (event.type === "assistant" || event.type === "result") {
      for (const tool of toolCalls) {
        if (tool.status === "pending") tool.status = "completed";
      }
    }
  }

  if (!isStreaming) {
    for (const tool of toolCalls) {
      tool.status = "completed";
    }
  }

  return toolCalls;
}
