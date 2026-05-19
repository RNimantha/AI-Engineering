export type Role = "user" | "assistant";

export type EventType = "assistant" | "tool" | "result";

export type EventItem = {
  type: EventType | string;
  content: string;
};

export type Message = {
  id: string;
  role: Role;
  content: string;
  events?: EventItem[];
  timestamp?: number;
};

export type ChatTurn = {
  role: Role;
  content: string;
};

export type ToolStatus = "pending" | "completed";

export type ToolCall = {
  id: string;
  name: string;
  status: ToolStatus;
};

export type Session = {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
};
