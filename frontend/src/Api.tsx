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

export interface JobProfile {
  id: number;
  resume_text: string;
  target_roles: string[];
  preferred_locations: string[];

  remote_ok: boolean;
  posted_within_days: number;
  min_match_score: number;

  created_at: string;
  updated_at: string;
}

export interface Job {
  id: number;

  title: string;
  company: string | null;
  location: string | null;

  source: string;
  source_url: string;

  posted_date_text: string | null;
  snippet: string | null;

  match_score: number;
  freshness_score: number;
  location_score: number;
  final_score: number;

  status: string;

  created_at: string;
  updated_at: string;
}


export async function getJobProfile(): Promise<JobProfile> {
  const response = await fetch(
    `${API_URL}/job-profile`
  );

  await checkResponse(response);

  return response.json();
}


export async function saveJobProfile(
  profile: Omit<
    JobProfile,
    "id" | "created_at" | "updated_at"
  >
): Promise<JobProfile> {

  const response = await fetch(
    `${API_URL}/job-profile`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(profile),
    }
  );

  await checkResponse(response);

  return response.json();
}


export async function findJobs(): Promise<Job[]> {

  const response = await fetch(
    `${API_URL}/jobs/search`,
    {
      method: "POST",
    }
  );

  await checkResponse(response);

  return response.json();
}


export async function getJobs(): Promise<Job[]> {

  const response = await fetch(
    `${API_URL}/jobs`
  );

  await checkResponse(response);

  return response.json();
}