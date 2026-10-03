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
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  linkedin_url: string;
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

  application_url: string | null;
  link_status: string;

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

export async function resolveJobLink(
  jobId: number
): Promise<Job> {

  const response = await fetch(
    `${API_URL}/jobs/${jobId}/resolve`,
    { method: "POST" }
  );

  await checkResponse(response);
  return response.json();
}


export async function setApplicationLink(
  jobId: number,
  url: string
): Promise<Job> {

  const response = await fetch(
    `${API_URL}/jobs/${jobId}/application-link`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        application_url: url,
      }),
    }
  );

  await checkResponse(response);
  return response.json();
}


export async function prepareApplication(
  jobId: number
): Promise<{ state: string }> {

  const response = await fetch(
    `${API_URL}/jobs/${jobId}/prepare`,
    { method: "POST" }
  );

  await checkResponse(response);
  return response.json();
}


export async function updateJobStatus(
  jobId: number,
  status: string
): Promise<Job> {

  const response = await fetch(
    `${API_URL}/jobs/${jobId}/status`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ status }),
    }
  );

  await checkResponse(response);
  return response.json();
}


export async function uploadResume(
  file: File
): Promise<void> {

  const form = new FormData();
  form.append("file", file);

  const response = await fetch(
    `${API_URL}/job-profile/resume`,
    {
      method: "POST",
      body: form,
    }
  );

  await checkResponse(response);
}

export type CareerCategory =
  | "education"
  | "work"
  | "project"
  | "skill"
  | "certification";

export interface CareerRecordInput {
  category: CareerCategory;
  title: string;
  organization: string | null;
  start_date: string | null;
  end_date: string | null;
  description: string;
  skills: string[];
}

export interface CareerRecord extends CareerRecordInput {
  id: number;
  profile_id: number;
  created_at: string;
  updated_at: string;
}

const CAREER_URL =
  "http://127.0.0.1:8000/api/career/records";

export async function getCareerRecords(): Promise<CareerRecord[]> {
  const response = await fetch(CAREER_URL);

  if (!response.ok) {
    throw new Error("Failed to load career records");
  }

  return response.json();
}

export async function saveCareerRecord(
  data: CareerRecordInput,
  id?: number
): Promise<CareerRecord> {
  const response = await fetch(
    id === undefined ? CAREER_URL : `${CAREER_URL}/${id}`,
    {
      method: id === undefined ? "POST" : "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    }
  );

  if (!response.ok) {
    throw new Error("Failed to save career record");
  }

  return response.json();
}

export async function deleteCareerRecord(
  id: number
): Promise<void> {
  const response = await fetch(`${CAREER_URL}/${id}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error("Failed to delete career record");
  }
}

export interface ResumeInput {
  name: string;
  content: string;
  role_tags: string[];
  skill_tags: string[];
}

export interface ResumeVersion extends ResumeInput {
  id: number;
  profile_id: number;
  family_id: string;
  version: number;
  status: "draft" | "approved";
  based_on_resume_id: number | null;
  source_profile_hash: string | null;
  created_at: string;
  approved_at: string | null;
  profile_changed: boolean;
}

const RESUMES_URL =
  "http://127.0.0.1:8000/api/resumes";

async function resumeRequest<T>(
  url: string,
  method = "GET",
  body?: ResumeInput
): Promise<T> {
  const response = await fetch(url, {
    method,
    headers: body
      ? { "Content-Type": "application/json" }
      : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json();
}

export function getResumeVersions() {
  return resumeRequest<ResumeVersion[]>(RESUMES_URL);
}

export function createResume(data: ResumeInput) {
  return resumeRequest<ResumeVersion>(
    RESUMES_URL,
    "POST",
    data
  );
}

export function updateResume(
  id: number,
  data: ResumeInput
) {
  return resumeRequest<ResumeVersion>(
    `${RESUMES_URL}/${id}`,
    "PUT",
    data
  );
}

export function approveResume(id: number) {
  return resumeRequest<ResumeVersion>(
    `${RESUMES_URL}/${id}/approve`,
    "POST"
  );
}

export function createResumeRevision(id: number) {
  return resumeRequest<ResumeVersion>(
    `${RESUMES_URL}/${id}/new-version`,
    "POST"
  );
}