import {
  ChatMessage,
  ChatSession,
  Citation,
  Flashcard,
  FlashcardGenerateResponse,
  RagDocument,
  RetrievalMode,
} from "@/lib/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  "http://127.0.0.1:8000";

// Khớp AIRA_API_KEY bên backend. Chỉ là lớp khóa cơ bản
// cho bản chạy local/LAN - key vẫn lộ ở phía trình duyệt,
// không thay thế được auth thật khi deploy public.
const API_KEY =
  process.env.NEXT_PUBLIC_AIRA_API_KEY ?? "";

function authHeaders(
  extra?: Record<string, string>
): Record<string, string> {
  return {
    ...(extra ?? {}),
    ...(API_KEY
      ? { "X-API-Key": API_KEY }
      : {}),
  };
}

async function getErrorMessage(
  response: Response
): Promise<string> {
  try {
    const data = await response.json();

    if (typeof data.detail === "string") {
      return data.detail;
    }

    return JSON.stringify(data);
  } catch {
    return `HTTP ${response.status}`;
  }
}

async function requestJson<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(
    `${API_BASE_URL}${url}`,
    {
      ...options,
      headers: authHeaders(
        options?.headers as
          | Record<string, string>
          | undefined
      ),
    }
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(response)
    );
  }

  return response.json();
}

// =========================================================
// SESSIONS
// =========================================================

export async function listSessions(): Promise<ChatSession[]> {
  return requestJson<ChatSession[]>(
    "/api/v1/sessions"
  );
}

export async function createSession(
  title: string
): Promise<ChatSession> {
  return requestJson<ChatSession>(
    "/api/v1/sessions",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ title }),
    }
  );
}

export async function deleteSession(
  sessionId: string
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/sessions/${sessionId}`,
    {
      method: "DELETE",
      headers: authHeaders(),
    }
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(response)
    );
  }
}

// =========================================================
// DOCUMENTS
// =========================================================

export async function getDocuments(
  sessionId: string
): Promise<RagDocument[]> {
  return requestJson<RagDocument[]>(
    `/api/v1/sessions/${sessionId}/documents`
  );
}

export async function uploadPdf(
  sessionId: string,
  file: File
): Promise<RagDocument> {
  const formData = new FormData();
  formData.append("file", file);

  return requestJson<RagDocument>(
    `/api/v1/sessions/${sessionId}/documents`,
    {
      method: "POST",
      body: formData,
    }
  );
}

// =========================================================
// MESSAGES
// =========================================================

export async function getMessages(
  sessionId: string
): Promise<ChatMessage[]> {
  return requestJson<ChatMessage[]>(
    `/api/v1/sessions/${sessionId}/messages`
  );
}

// =========================================================
// FLASHCARDS
// =========================================================

export async function getFlashcards(
  sessionId: string
): Promise<Flashcard[]> {
  return requestJson<Flashcard[]>(
    `/api/v1/sessions/${sessionId}/flashcards`
  );
}

export async function generateFlashcards(
  sessionId: string,
  count: number,
  replaceExisting = true
): Promise<FlashcardGenerateResponse> {
  return requestJson<FlashcardGenerateResponse>(
    `/api/v1/sessions/${sessionId}/flashcards/generate`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        count,
        replace_existing: replaceExisting,
      }),
    }
  );
}

export async function deleteFlashcard(
  sessionId: string,
  flashcardId: string
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/sessions/${sessionId}/flashcards/${flashcardId}`,
    {
      method: "DELETE",
      headers: authHeaders(),
    }
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(response)
    );
  }
}

// =========================================================
// CHAT STREAMING
// =========================================================

interface StreamChatCallbacks {
  onToken: (text: string) => void;
  onCitations: (
    citations: Citation[],
    coverage: number
  ) => void;
  onDone: () => void;
  onError: (message: string) => void;
}

interface SsePayload {
  text?: string;
  message?: string;
  citations?: Citation[];
  citation_coverage?: number;
}

function handleEvent(
  block: string,
  callbacks: StreamChatCallbacks
) {
  const lines = block.split("\n");
  let eventName = "message";
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      eventName = line.slice(6).trim();
      continue;
    }

    if (line.startsWith("data:")) {
      dataLines.push(
        line.slice(5).trimStart()
      );
    }
  }

  if (dataLines.length === 0) {
    return;
  }

  const rawData = dataLines.join("\n");
  let data: SsePayload;

  try {
    data = JSON.parse(rawData);
  } catch {
    return;
  }

  if (
    eventName === "token" &&
    typeof data.text === "string"
  ) {
    callbacks.onToken(data.text);
    return;
  }

  if (eventName === "citations") {
    callbacks.onCitations(
      data.citations ?? [],
      data.citation_coverage ?? 0
    );
    return;
  }

  if (eventName === "done") {
    callbacks.onDone();
    return;
  }

  if (eventName === "error") {
    callbacks.onError(
      data.message ?? "Streaming error."
    );
  }
}

export async function streamChat(
  sessionId: string,
  message: string,
  callbacks: StreamChatCallbacks,
  // Chế độ tốc độ truy xuất (tùy chọn, tương thích ngược):
  // không truyền thì payload giữ nguyên như trước và
  // backend tự dùng mặc định "lau" (pool 40, winner E7).
  mode?: RetrievalMode
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/sessions/${sessionId}/chat/stream`,
    {
      method: "POST",
      headers: authHeaders({
        "Content-Type": "application/json",
      }),
      body: JSON.stringify({
        message,
        ...(mode ? { mode } : {}),
      }),
    }
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(response)
    );
  }

  if (!response.body) {
    throw new Error(
      "Server không hỗ trợ streaming."
    );
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();

    if (done) {
      break;
    }

    buffer += decoder
      .decode(value, { stream: true })
      .replace(/\r\n/g, "\n");

    let boundary = buffer.indexOf("\n\n");

    while (boundary !== -1) {
      const block = buffer
        .slice(0, boundary)
        .trim();

      buffer = buffer.slice(boundary + 2);

      if (block) {
        handleEvent(block, callbacks);
      }

      boundary = buffer.indexOf("\n\n");
    }
  }

  const remaining = buffer.trim();

  if (remaining) {
    handleEvent(remaining, callbacks);
  }
}
