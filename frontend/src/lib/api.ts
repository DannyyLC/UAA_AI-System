import type {
  ChatPanelMessage,
  DocumentSources,
  LLMModel,
  LoginRequest,
  RegisterRequest,
  UserResponse,
} from "./types";

const BASE_URL = "/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
    credentials: "include",
  });

  if (!res.ok) {
    let errorText: string;
    try {
      const data = await res.json();
      // El gateway puede devolver { detail: "..." } (FastAPI default)
      // o { message: "..." } (exception handler custom del gateway)
      errorText =
        (data as any)?.detail ??
        (data as any)?.message ??
        JSON.stringify(data);
    } catch {
      errorText = await res.text();
    }
    throw new Error(errorText || `Error ${res.status}`);
  }

  if (res.status === 204) {
    // No Content
    return undefined as T;
  }

  return (await res.json()) as T;
}

type AuthResponse = {
  message: string;
  user: UserResponse;
};

// ========= Auth =========

export async function getMe(): Promise<UserResponse | null> {
  try {
    return await request<UserResponse>("/auth/me");
  } catch {
    return null;
  }
}

export async function login(data: LoginRequest): Promise<AuthResponse> {
  return request<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function register(data: RegisterRequest): Promise<AuthResponse> {
  return request<AuthResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function logout(): Promise<void> {
  await request<void>("/auth/logout", {
    method: "POST",
  });
}

// ========= Chat (conversaciones + streaming) =========

type CreateConversationResponse = {
  message: string;
  conversation: {
    id: string;
    title: string;
    created_at?: string;
  };
};

export async function createConversation(payload: {
  title: string;
}): Promise<CreateConversationResponse> {
  return request<CreateConversationResponse>("/chat/conversations", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getModels(): Promise<LLMModel[]> {
  const res = await request<{ models: LLMModel[] }>("/chat/models");
  return res.models;
}

export type ChatStreamChunk =
  | { type: "token"; token: string }
  | { type: "classifying" }
  | { type: "researching" }
  | { type: "rag_start" }
  | { type: "rag_done" }
  | { type: "done"; message: ChatPanelMessage; used_rag: boolean; similarity_score: number | null; has_similarity: boolean }
  | { type: "error"; message: string };

export async function* sendMessageStream(
  conversationId: string,
  payload: { content: string; model: string; expected_answer?: string }
): AsyncGenerator<ChatStreamChunk, void, unknown> {
  const url = `${BASE_URL}/chat/conversations/${conversationId}/messages`;

  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "include",
    body: JSON.stringify(payload),
  });

  if (!res.ok || !res.body) {
    throw new Error(`Error iniciando streaming (${res.status})`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      const lines = part.split("\n");
      let eventType: string | null = null;
      let dataStr = "";

      for (const line of lines) {
        if (line.startsWith("event:")) {
          eventType = line.slice("event:".length).trim();
        } else if (line.startsWith("data: ")) {
          // Slice exactamente "data: " (con su espacio delimitador)
          // para preservar espacios que son parte del token (ej. " Hol", " Est")
          dataStr += line.slice("data: ".length);
        } else if (line.startsWith("data:")) {
          dataStr += line.slice("data:".length);
        }
      }

      if (!eventType) continue;

      if (eventType === "token") {
        yield { type: "token", token: dataStr };
      } else if (eventType === "classifying") {
        yield { type: "classifying" };
      } else if (eventType === "researching") {
        yield { type: "researching" };
      } else if (eventType === "rag_start") {
        yield { type: "rag_start" };
      } else if (eventType === "rag_done") {
        yield { type: "rag_done" };
      } else if (eventType === "done") {
        try {
          const data = JSON.parse(dataStr) as {
            message: ChatPanelMessage;
            used_rag: boolean;
            similarity_score: number | null;
            has_similarity: boolean;
          };
          yield {
            type: "done",
            message: data.message,
            used_rag: data.used_rag,
            similarity_score: data.similarity_score,
            has_similarity: data.has_similarity,
          };
        } catch {
          // ignore parse errors
        }
      } else if (eventType === "error") {
        try {
          const data = JSON.parse(dataStr) as { message?: string };
          yield { type: "error", message: data.message ?? "Error en streaming" };
        } catch {
          yield { type: "error", message: "Error en streaming" };
        }
      }
    }
  }
}

// ========= Documentos / Fuentes =========

export async function getDocumentSources(): Promise<DocumentSources> {
  return request<DocumentSources>("/documents/sources");
}

export async function uploadDocument(file: File, topic: string): Promise<void> {
  const form = new FormData();
  form.append("file", file);
  form.append("topic", topic);

  const res = await fetch(`${BASE_URL}/documents/upload`, {
    method: "POST",
    body: form,
    credentials: "include",
  });

  if (!res.ok) {
    let msg: string;
    try {
      const data = await res.json();
      msg = (data as any)?.detail ?? JSON.stringify(data);
    } catch {
      msg = await res.text();
    }
    throw new Error(msg || `Error subiendo documento (${res.status})`);
  }
}

export async function deleteDocument(filename: string, topic: string): Promise<void> {
  const params = new URLSearchParams({ topic });
  await request<void>(`/documents/sources/${encodeURIComponent(filename)}?${params.toString()}`, {
    method: "DELETE",
  });
}

