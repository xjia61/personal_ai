export type RetentionMode = "ephemeral" | "save" | "memory";

export interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  model?: string | null;
  memory_candidate: boolean;
  created_at: string;
}

export interface ConversationSummary {
  id: number;
  title: string;
  content_type: string;
  retention_type: RetentionMode;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends ConversationSummary {
  messages: Message[];
}

export interface ChatResponse {
  answer: string;
  model: string;
  conversation_id: number | null;
  saved: boolean;
}

const API_URL = "http://127.0.0.1:8000/api";

async function checkResponse(response: Response) {
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(data?.detail || "Request failed");
  }

  return response;
}

export async function getConversations(): Promise<ConversationSummary[]> {
  const response = await fetch(`${API_URL}/conversations`);
  await checkResponse(response);
  return response.json();
}

export async function getConversation(
  id: number
): Promise<ConversationDetail> {
  const response = await fetch(`${API_URL}/conversations/${id}`);
  await checkResponse(response);
  return response.json();
}

export async function sendMessage(
  message: string,
  retention: RetentionMode,
  conversationId?: number
): Promise<ChatResponse> {
  const response = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message,
      retention,
      conversation_id: conversationId ?? null,
    }),
  });

  await checkResponse(response);
  return response.json();
}