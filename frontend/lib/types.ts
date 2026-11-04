export interface ChatSession {
  id: string;
  title: string | null;
  created_at: string;
}

export interface RagDocument {
  id: string;
  name: string;
  status: string;
  page_count: number | null;
  error_message: string | null;
  created_at: string;
}

export interface Citation {
  index: number;
  chunk_id: string;
  doc_id: string;
  doc_name: string;
  page: number;
  text: string;
  snippet: string;
  retrieval_score: number;
  rerank_score: number;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: string;
  content: string;
  citations: Citation[] | null;
  created_at: string;
}

export interface Flashcard {
  id: string;
  session_id: string;
  document_id: string;
  document_name: string;
  source_chunk_id: string;
  source_page: number;
  question: string;
  answer: string;
  created_at: string;
}

export interface FlashcardGenerateResponse {
  requested_count: number;
  generated_count: number;
  flashcards: Flashcard[];
}

// Chế độ tốc độ truy xuất — khóa gửi kèm request chat,
// khớp RETRIEVAL_MODES ở backend (src/config.py).
// "lau" là mặc định = pool 40, winner E7 nguyên bản.
export type RetrievalMode = "nhanh" | "trung_binh" | "lau";

export interface UiMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  // Thời gian trả lời đo phía client (giây) — chỉ có ở tin nhắn
  // được tạo trong phiên làm việc hiện tại, tin nạp từ lịch sử thì không.
  responseTimeSec?: number;
}
