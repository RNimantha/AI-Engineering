import type { Message } from "./types";

export const CHAT_API_URL = "http://127.0.0.1:8000/api/chat";

export const STARTER_PROMPTS = [
  "Show the inventory list.",
  "Find the item called bats.",
  "Update caps quantity to 8.",
  "List all users.",
  "Create a note titled Sprint with body Review inventory flow.",
];

export const INITIAL_MESSAGES: Message[] = [
  {
    id: "welcome",
    role: "assistant",
    content: "Pick a prompt or type a task. I can inspect inventory, manage users, and work with notes.",
    timestamp: Date.now(),
  },
];
