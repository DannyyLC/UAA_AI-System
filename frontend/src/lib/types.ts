export interface UserResponse {
  user_id: string;
  email: string;
  full_name?: string | null;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
}

export interface LLMModel {
  id: string;
  name: string;
  provider: string;
}

export interface ChatPanelMessage {
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
  used_rag?: boolean;
}

export interface DocumentSourceItem {
  job_id: string;
  filename: string;
  chunks: number;
  status: string;
  indexed_at: string;
}

export interface DocumentSources {
  topics: string[];
  sources: Record<string, DocumentSourceItem[]>;
  total: number;
}

