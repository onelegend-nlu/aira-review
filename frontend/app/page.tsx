"use client";

import {
  FormEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import ChatPanel from "@/components/ChatPanel";
import DocumentLibrary from "@/components/DocumentLibrary";
import FlashcardPanel from "@/components/FlashcardPanel";
import HistoryPanel from "@/components/HistoryPanel";
import SystemInfoPanel from "@/components/SystemInfoPanel";
import UploadPanel from "@/components/UploadPanel";

import {
  createSession,
  deleteSession,
  deleteFlashcard,
  generateFlashcards,
  getDocuments,
  getFlashcards,
  getMessages,
  listSessions,
  streamChat,
  uploadPdf,
} from "@/lib/api";

import {
  ChatSession,
  Flashcard,
  RagDocument,
  RetrievalMode,
  UiMessage,
} from "@/lib/types";

function createLocalId(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random()}`;
}

export default function Home() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [documents, setDocuments] = useState<RagDocument[]>([]);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [activeTab, setActiveTab] = useState<"chat" | "flashcards" | "info">(
    "chat"
  );
  const [flashcards, setFlashcards] = useState<Flashcard[]>([]);
  const [generatingFlashcards, setGeneratingFlashcards] = useState(false);
  const [deletingFlashcardId, setDeletingFlashcardId] = useState<string | null>(null);
  const [flashcardIndex, setFlashcardIndex] = useState(0);
  const [flashcardFlipped, setFlashcardFlipped] = useState(false);
  const [question, setQuestion] = useState("");
  // Chế độ tốc độ truy xuất — giữ trong phiên làm việc của
  // trang, mặc định "lau" (pool 40, winner E7 nguyên bản).
  const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>("lau");
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [loadingConversation, setLoadingConversation] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [deletingSessionId, setDeletingSessionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Thanh bên ẩn/hiện được: trên mobile khởi tạo LUÔN đóng (bỏ qua localStorage);
  // từ md trở lên giữ nguyên lựa chọn nhớ qua localStorage (mặc định mở).
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const isDesktop = window.innerWidth >= 768;
      if (isDesktop) {
        const saved = window.localStorage.getItem("aira.ui.sidebarOpen");
        setSidebarOpen(saved === null ? true : saved === "1");
      } else {
        setSidebarOpen(false);
      }
    }
  }, []);

  useEffect(() => {
    if (typeof window !== "undefined" && window.innerWidth >= 768) {
      window.localStorage.setItem(
        "aira.ui.sidebarOpen",
        sidebarOpen ? "1" : "0"
      );
    }
  }, [sidebarOpen]);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const selectedSession = useMemo(
    () => sessions.find((session) => session.id === selectedSessionId) ?? null,
    [sessions, selectedSessionId]
  );

  const hasReadyDocument = useMemo(
    () => documents.some((document) => document.status === "ready"),
    [documents]
  );

  // Poll trạng thái document (ingest chạy nền ở backend):
  // poll cho tới khi mọi tài liệu đều ready/failed.
  useEffect(() => {
    if (!selectedSessionId) {
      return;
    }

    const hasPending = documents.some(
      (document) =>
        document.status === "pending" || document.status === "processing"
    );

    if (!hasPending) {
      return;
    }

    const timer = setInterval(() => {
      void getDocuments(selectedSessionId)
        .then(setDocuments)
        .catch(() => {});
    }, 2000);

    return () => clearInterval(timer);
  }, [selectedSessionId, documents]);

  // Initial load
  useEffect(() => {
    void loadSessions();
  }, []);

  // Session change
  useEffect(() => {
    if (!selectedSessionId) {
      setDocuments([]);
      setMessages([]);
      setFlashcards([]);
      setFlashcardIndex(0);
      setFlashcardFlipped(false);
      setActiveTab("chat");
      return;
    }

    void loadConversation(selectedSessionId);
  }, [selectedSessionId]);

  // Auto scroll
  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      messagesEndRef.current?.scrollIntoView({
        behavior: streaming ? "auto" : "smooth",
        block: "end",
      });
    });

    return () => {
      cancelAnimationFrame(frame);
    };
  }, [messages, streaming]);

  async function loadSessions() {
    try {
      setLoadingSessions(true);
      setError(null);

      const data = await listSessions();

      setSessions(data);

      if (data.length > 0) {
        setSelectedSessionId((current) => current ?? data[0].id);
      }
    } catch (err) {
      setError(getErrorText(err));
    } finally {
      setLoadingSessions(false);
    }
  }

  // Refresh title mà không làm sidebar nháy loading.
  async function refreshSessionList() {
    try {
      const data = await listSessions();

      setSessions(data);
    } catch (err) {
      console.error(err);
    }
  }

  async function loadConversation(sessionId: string) {
    try {
      setLoadingConversation(true);
      setError(null);

      const [docs, history, cards] = await Promise.all([
        getDocuments(sessionId),
        getMessages(sessionId),
        getFlashcards(sessionId),
      ]);

      setDocuments(docs);

      setMessages(
        history.map((message) => ({
          id: message.id,
          role: message.role === "user" ? "user" : "assistant",
          content: message.content,
          citations: message.citations ?? [],
        }))
      );

      setFlashcards(cards);
      setFlashcardIndex(0);
      setFlashcardFlipped(false);
    } catch (err) {
      setError(getErrorText(err));
    } finally {
      setLoadingConversation(false);
    }
  }

  async function handleNewChat() {
    try {
      setError(null);

      const session = await createSession("Cuộc trò chuyện mới");

      setSessions((current) => [session, ...current]);
      setSelectedSessionId(session.id);
      setActiveTab("chat");
      if (typeof window !== "undefined" && window.innerWidth < 768) {
        setSidebarOpen(false);
      }
    } catch (err) {
      setError(getErrorText(err));
    }
  }

  async function handleDeleteSession(sessionId: string, title: string | null) {
    if (streaming && sessionId === selectedSessionId) {
      setError("Không thể xóa cuộc trò chuyện khi AIRA đang trả lời.");
      return;
    }

    const confirmed = window.confirm(
      `Xóa cuộc trò chuyện "${title || "Untitled"}"?\n\nLịch sử chat của session này sẽ bị xóa.`
    );

    if (!confirmed) {
      return;
    }

    try {
      setDeletingSessionId(sessionId);
      setError(null);

      await deleteSession(sessionId);

      const data = await listSessions();

      setSessions(data);

      if (selectedSessionId === sessionId) {
        setSelectedSessionId(data[0]?.id ?? null);
      }
    } catch (err) {
      setError(getErrorText(err));
    } finally {
      setDeletingSessionId(null);
    }
  }

  // Chọn/thả PDF là upload ngay — không chờ bấm nút riêng.
  async function handleFileChosen(file: File) {
    if (!selectedSessionId || uploading) {
      return;
    }

    try {
      setUploading(true);
      setError(null);

      await uploadPdf(selectedSessionId, file);

      const docs = await getDocuments(selectedSessionId);

      setDocuments(docs);
    } catch (err) {
      setError(getErrorText(err));
    } finally {
      setUploading(false);
    }
  }

  async function handleGenerateFlashcards() {
    if (!selectedSessionId || !hasReadyDocument || generatingFlashcards) {
      return;
    }

    try {
      setGeneratingFlashcards(true);
      setError(null);

      const result = await generateFlashcards(selectedSessionId, 10, true);

      setFlashcards(result.flashcards);
      setFlashcardIndex(0);
      setFlashcardFlipped(false);
      setActiveTab("flashcards");
    } catch (err) {
      setError(getErrorText(err));
    } finally {
      setGeneratingFlashcards(false);
    }
  }

  async function handleDeleteFlashcard(flashcardId: string) {
    if (!selectedSessionId || deletingFlashcardId) {
      return;
    }

    try {
      setDeletingFlashcardId(flashcardId);
      setError(null);

      await deleteFlashcard(selectedSessionId, flashcardId);

      setFlashcards((current) => {
        const next = current.filter((card) => card.id !== flashcardId);

        setFlashcardIndex((index) =>
          Math.min(index, Math.max(next.length - 1, 0))
        );

        return next;
      });

      setFlashcardFlipped(false);
    } catch (err) {
      setError(getErrorText(err));
    } finally {
      setDeletingFlashcardId(null);
    }
  }

  function showPreviousFlashcard() {
    setFlashcardIndex((current) => Math.max(current - 1, 0));
    setFlashcardFlipped(false);
  }

  function showNextFlashcard() {
    setFlashcardIndex((current) =>
      Math.min(current + 1, flashcards.length - 1)
    );
    setFlashcardFlipped(false);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    await sendQuestion(question);
  }

  // Đường gửi câu hỏi duy nhất — dùng cho cả form nhập và chip
  // câu hỏi mẫu. Đo thời gian trả lời phía client để hiển thị
  // metadata dưới câu trả lời.
  async function sendQuestion(rawText: string) {
    const text = rawText.trim();

    if (!text || !selectedSessionId || streaming) {
      return;
    }

    if (!hasReadyDocument) {
      setError("Hãy upload ít nhất một PDF và đợi tài liệu ở trạng thái ready.");
      return;
    }

    setError(null);
    setQuestion("");

    const userMessageId = createLocalId("user");
    const assistantMessageId = createLocalId("assistant");

    setMessages((current) => [
      ...current,
      {
        id: userMessageId,
        role: "user",
        content: text,
        citations: [],
      },
      {
        id: assistantMessageId,
        role: "assistant",
        content: "",
        citations: [],
      },
    ]);

    setStreaming(true);

    const startedAt = performance.now();

    try {
      await streamChat(selectedSessionId, text, {
        onToken: (token) => {
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantMessageId
                ? { ...message, content: message.content + token }
                : message
            )
          );
        },

        onCitations: (citations) => {
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantMessageId
                ? { ...message, citations }
                : message
            )
          );
        },

        onDone: () => {
          // Backend đã auto-title nếu đây là câu hỏi đầu.
          void refreshSessionList();
        },

        onError: (message) => {
          setError(message);
        },
      }, retrievalMode);

      // streamChat resolve khi stream kết thúc = đã nhận xong
      // toàn bộ câu trả lời.
      const elapsedSec = (performance.now() - startedAt) / 1000;

      setMessages((current) =>
        current.map((message) =>
          message.id === assistantMessageId
            ? { ...message, responseTimeSec: elapsedSec }
            : message
        )
      );
    } catch (err) {
      setError(getErrorText(err));

      setMessages((current) =>
        current.map((item) =>
          item.id === assistantMessageId
            ? {
                ...item,
                content: item.content || "Có lỗi khi tạo câu trả lời.",
              }
            : item
        )
      );
    } finally {
      setStreaming(false);
    }
  }

  return (
    <main className="relative flex h-screen overflow-hidden text-slate-100">
      {/* Mobile drawer backdrop — fade mượt 2 chiều */}
      <div
        className={`fixed inset-0 z-40 bg-black/60 backdrop-blur-sm transition-opacity duration-300 md:hidden ${
          sidebarOpen
            ? "opacity-100 pointer-events-auto"
            : "opacity-0 pointer-events-none"
        }`}
        onClick={() => setSidebarOpen(false)}
        aria-hidden="true"
      />

      {/* SIDEBAR — drawer trượt mượt 2 chiều trên mobile, co giãn mượt trên desktop */}
      <div
        className={`fixed inset-y-0 left-0 z-50 w-72 max-w-[85vw] transition-transform duration-300 ease-in-out md:static md:z-auto md:translate-x-0 md:h-full md:transition-[width,opacity] md:duration-300 md:ease-in-out ${
          sidebarOpen
            ? "translate-x-0 md:w-72 md:opacity-100"
            : "-translate-x-full md:w-0 md:opacity-0 md:overflow-hidden md:pointer-events-none"
        }`}
      >
        <HistoryPanel
          sessions={sessions}
          selectedSessionId={selectedSessionId}
          loadingSessions={loadingSessions}
          deletingSessionId={deletingSessionId}
          onNewChat={handleNewChat}
          onSelectSession={(id) => {
            setSelectedSessionId(id);
            if (typeof window !== "undefined" && window.innerWidth < 768) {
              setSidebarOpen(false);
            }
          }}
          onDeleteSession={handleDeleteSession}
          onClose={() => setSidebarOpen(false)}
        />
      </div>

      {/* MAIN CONTENT */}
      <section className="flex min-w-0 flex-1 flex-col">
        {/* HEADER */}
        <header className="sticky top-0 z-20 border-b border-slate-800/80 bg-slate-950/70 px-3 py-2.5 sm:px-6 sm:py-3 shadow-lg shadow-black/10 backdrop-blur-md">
          <div className="flex items-center justify-between gap-2 sm:gap-4">
            <div className="flex min-w-0 flex-1 items-center gap-2 sm:gap-3">
              <button
                type="button"
                onClick={() => setSidebarOpen((open) => !open)}
                aria-label={sidebarOpen ? "Ẩn thanh bên" : "Hiện thanh bên"}
                title={sidebarOpen ? "Ẩn thanh bên" : "Hiện thanh bên"}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-slate-700/70 bg-slate-800/80 text-slate-300 transition duration-150 hover:bg-slate-700 hover:text-white active:scale-[0.97]"
              >
                <svg
                  aria-hidden="true"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="h-5 w-5"
                >
                  <rect x="3" y="4" width="18" height="16" rx="2" />
                  <path d="M9.5 4v16" />
                </svg>
              </button>

              <div className="min-w-0 flex-1">
                <h1 className="truncate text-sm font-semibold tracking-tight sm:text-lg">
                  {selectedSession?.title ?? "Chọn hoặc tạo session"}
                </h1>

                <DocumentLibrary documents={documents} />
              </div>
            </div>

            {selectedSessionId && (
              <div className="shrink-0">
                <UploadPanel
                  uploading={uploading}
                  compact={hasReadyDocument}
                  onFileChosen={handleFileChosen}
                />
              </div>
            )}
          </div>
        </header>

        {/* MODE TABS */}
        {selectedSessionId && (
          <div className="flex gap-2 overflow-x-auto whitespace-nowrap border-b border-slate-800/80 bg-slate-950/50 px-3 py-2 sm:px-6 sm:py-3 backdrop-blur scrollbar-none">
            <button
              onClick={() => setActiveTab("chat")}
              className={`flex min-h-[40px] shrink-0 items-center rounded-xl px-3.5 py-2 text-xs font-medium transition duration-150 active:scale-[0.97] sm:text-sm ${
                activeTab === "chat"
                  ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md shadow-blue-600/30"
                  : "bg-slate-900/70 text-slate-400 ring-1 ring-slate-800 hover:bg-slate-800 hover:text-slate-200"
              }`}
            >
              Chat
            </button>

            <button
              onClick={() => {
                setActiveTab("flashcards");
                setFlashcardFlipped(false);
              }}
              className={`flex min-h-[40px] shrink-0 items-center rounded-xl px-3.5 py-2 text-xs font-medium transition duration-150 active:scale-[0.97] sm:text-sm ${
                activeTab === "flashcards"
                  ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md shadow-blue-600/30"
                  : "bg-slate-900/70 text-slate-400 ring-1 ring-slate-800 hover:bg-slate-800 hover:text-slate-200"
              }`}
            >
              Flashcards ({flashcards.length})
            </button>

            <button
              onClick={() => setActiveTab("info")}
              className={`flex min-h-[40px] shrink-0 items-center rounded-xl px-3.5 py-2 text-xs font-medium transition duration-150 active:scale-[0.97] sm:text-sm ${
                activeTab === "info"
                  ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md shadow-blue-600/30"
                  : "bg-slate-900/70 text-slate-400 ring-1 ring-slate-800 hover:bg-slate-800 hover:text-slate-200"
              }`}
            >
              Giới thiệu
            </button>
          </div>
        )}

        {/* ERROR */}
        {error && (
          <div className="mx-6 mt-4 rounded-2xl border border-red-900/70 bg-red-950/50 px-4 py-3 text-sm text-red-300 shadow-lg shadow-red-950/20 backdrop-blur">
            {error}
          </div>
        )}

        {/* CHAT / FLASHCARDS / GIỚI THIỆU (TRANSITION FADE-IN KHI ĐỔI TAB) */}
        <div key={activeTab} className="animate-fade-in flex flex-1 flex-col min-h-0">
          {activeTab === "info" ? (
            <SystemInfoPanel />
          ) : activeTab === "chat" ? (
            <ChatPanel
              selectedSessionId={selectedSessionId}
              loadingConversation={loadingConversation}
              messages={messages}
              hasReadyDocument={hasReadyDocument}
              streaming={streaming}
              question={question}
              onQuestionChange={setQuestion}
              retrievalMode={retrievalMode}
              onRetrievalModeChange={setRetrievalMode}
              onSubmit={handleSubmit}
              onSuggestionClick={(text) => {
                void sendQuestion(text);
              }}
              messagesEndRef={messagesEndRef}
            />
          ) : (
            <FlashcardPanel
              selectedSessionId={selectedSessionId}
              hasReadyDocument={hasReadyDocument}
              loading={loadingConversation}
              flashcards={flashcards}
              currentIndex={flashcardIndex}
              flipped={flashcardFlipped}
              generating={generatingFlashcards}
              deletingFlashcardId={deletingFlashcardId}
              onGenerate={handleGenerateFlashcards}
              onFlip={() => setFlashcardFlipped((current) => !current)}
              onPrevious={showPreviousFlashcard}
              onNext={showNextFlashcard}
              onDelete={handleDeleteFlashcard}
            />
          )}
        </div>
      </section>
    </main>
  );
}

function getErrorText(error: unknown) {
  if (error instanceof Error) {
    return error.message;
  }

  return "Đã xảy ra lỗi.";
}
