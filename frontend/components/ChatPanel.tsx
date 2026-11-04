import { FormEvent, RefObject, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

import EmptyState from "@/components/EmptyState";
import { RetrievalMode, UiMessage } from "@/lib/types";

const SUGGESTED_QUESTIONS = [
  "Tóm tắt nội dung chính của tài liệu này.",
  "Tài liệu này gồm những phần chính nào?",
  "Những khái niệm quan trọng nhất trong tài liệu là gì?",
  "Liệt kê các con số, số liệu đáng chú ý trong tài liệu.",
];

const STREAM_STAGES = [
  "Đang tìm trong tài liệu…",
  "Đang xếp hạng các đoạn liên quan…",
  "Đang soạn câu trả lời…",
];

// Ba chế độ tốc độ truy xuất — khớp RETRIEVAL_MODES ở
// backend (src/config.py). Chỉ đổi pool rerank; ghi chú
// dùng số liệu kiểm định Pareto đã chốt (số của Nhanh và
// Trung bình đo trên tập dev, chỉ Lâu có số test chính thức).
// Thứ tự trong menu chọn: chuẩn winner trước, nhanh nhất cuối.
const RETRIEVAL_MODE_OPTIONS: Array<{
  value: RetrievalMode;
  label: string;
  note: string;
}> = [
  {
    value: "lau",
    label: "Lâu",
    note: "Pool 40 · Chuẩn winner E7 — ExcerptHit test 94,1%",
  },
  {
    value: "trung_binh",
    label: "Trung bình",
    note: "Pool 20 · Rerank nhanh hơn ~47% · ExcerptHit dev 0,884",
  },
  {
    value: "nhanh",
    label: "Nhanh",
    note: "Pool 10 · Rerank nhanh hơn ~70% · ExcerptHit dev 0,872",
  },
];

interface ChatPanelProps {
  selectedSessionId: string | null;
  loadingConversation: boolean;
  messages: UiMessage[];
  hasReadyDocument: boolean;
  streaming: boolean;
  question: string;
  onQuestionChange: (value: string) => void;
  retrievalMode: RetrievalMode;
  onRetrievalModeChange: (mode: RetrievalMode) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onSuggestionClick: (question: string) => void;
  messagesEndRef: RefObject<HTMLDivElement | null>;
}

export default function ChatPanel({
  selectedSessionId,
  loadingConversation,
  messages,
  hasReadyDocument,
  streaming,
  question,
  onQuestionChange,
  retrievalMode,
  onRetrievalModeChange,
  onSubmit,
  onSuggestionClick,
  messagesEndRef,
}: ChatPanelProps) {
  const [showScrollBottom, setShowScrollBottom] = useState(false);
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const showSuggestions =
    !!selectedSessionId &&
    hasReadyDocument &&
    !loadingConversation &&
    messages.length === 0;

  // Auto-resize textarea theo nội dung từ 1 dòng tới max 160px
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        160
      )}px`;
    }
  }, [question]);

  // Menu chọn chế độ (kiểu bộ chọn model của ChatGPT/Claude):
  // một nút gọn trong hàng nhập, bấm vào mới bật menu lên.
  const [modeMenuOpen, setModeMenuOpen] = useState(false);
  const modePickerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!modeMenuOpen) {
      return;
    }

    const onPointerDown = (event: MouseEvent) => {
      if (
        modePickerRef.current &&
        !modePickerRef.current.contains(event.target as Node)
      ) {
        setModeMenuOpen(false);
      }
    };

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setModeMenuOpen(false);
      }
    };

    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);

    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [modeMenuOpen]);

  const currentModeOption =
    RETRIEVAL_MODE_OPTIONS.find((option) => option.value === retrievalMode) ??
    RETRIEVAL_MODE_OPTIONS[0];

  const handleScroll = () => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const distanceFromBottom =
      el.scrollHeight - el.scrollTop - el.clientHeight;
    setShowScrollBottom(distanceFromBottom > 300);
  };

  return (
    <>
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="relative flex-1 overflow-y-auto px-3 py-4 sm:px-6 sm:py-6"
      >
        {!selectedSessionId ? (
          <EmptyState
            title="Chưa có cuộc trò chuyện"
            description="Tạo New Chat để bắt đầu."
          />
        ) : loadingConversation ? (
          <div className="mx-auto flex max-w-3xl flex-col gap-6 py-4">
            <div className="flex justify-end">
              <div className="h-14 w-2/3 animate-pulse rounded-2xl rounded-br-md bg-slate-800/60" />
            </div>
            <div className="flex justify-start">
              <div className="flex w-full gap-3 rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
                <div className="h-8 w-8 shrink-0 animate-pulse rounded-lg bg-slate-800" />
                <div className="flex-1 space-y-2.5">
                  <div className="h-4 w-24 animate-pulse rounded bg-slate-800" />
                  <div className="h-4 w-full animate-pulse rounded bg-slate-800/70" />
                  <div className="h-4 w-4/5 animate-pulse rounded bg-slate-800/70" />
                </div>
              </div>
            </div>
            <div className="flex justify-end">
              <div className="h-12 w-1/2 animate-pulse rounded-2xl rounded-br-md bg-slate-800/60" />
            </div>
          </div>
        ) : messages.length === 0 ? (
          <EmptyState
            title="Học cùng AIRA"
            description={
              hasReadyDocument
                ? "PDF đã sẵn sàng. Hãy đặt câu hỏi."
                : "Upload PDF trước khi đặt câu hỏi."
            }
          />
        ) : (
          <div className="mx-auto flex max-w-3xl flex-col gap-6">
            {messages.map((message, idx) => (
              <MessageBubble
                key={message.id}
                message={message}
                isStreamingLast={
                  streaming &&
                  idx === messages.length - 1 &&
                  message.role === "assistant"
                }
              />
            ))}

            {streaming && <StreamingProgress />}

            <div ref={messagesEndRef} className="h-px" />
          </div>
        )}

        {/* NÚT CUỘN XUỐNG CUỐI (KHI CÁCH ĐÁY > 300px) */}
        {showScrollBottom && (
          <button
            type="button"
            onClick={() => {
              messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
            }}
            aria-label="Cuộn xuống cuối"
            title="Cuộn xuống cuối"
            className="fixed bottom-24 right-5 sm:right-8 z-30 flex h-10 w-10 items-center justify-center rounded-full border border-blue-500/30 bg-slate-900/90 text-blue-400 shadow-xl shadow-black/40 backdrop-blur transition duration-150 hover:bg-slate-800 hover:text-white active:scale-95 animate-fade-in"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2.5"
                d="M19 14l-7 7m0 0l-7-7m7 7V3"
              />
            </svg>
          </button>
        )}
      </div>

      <div
        className="border-t border-slate-800/80 bg-slate-950/70 px-3 py-2.5 sm:px-6 sm:py-3 backdrop-blur"
        style={{ paddingBottom: "max(0.75rem, env(safe-area-inset-bottom))" }}
      >
        {showSuggestions && (
          <div className="mx-auto mb-2 sm:mb-3 flex max-w-3xl flex-nowrap sm:flex-wrap gap-2 overflow-x-auto pb-1 scrollbar-none">
            {SUGGESTED_QUESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                onClick={() => onSuggestionClick(suggestion)}
                className="flex shrink-0 min-h-[36px] sm:min-h-0 items-center gap-1.5 rounded-full border border-blue-400/25 bg-gradient-to-r from-blue-500/10 to-indigo-500/10 px-3 py-1.5 text-xs text-slate-300 transition duration-150 hover:-translate-y-0.5 hover:border-blue-400/70 hover:text-slate-100 hover:shadow-lg hover:shadow-blue-950/50 active:scale-[0.97]"
              >
                <svg
                  aria-hidden="true"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  className="h-3 w-3 shrink-0 text-blue-400"
                >
                  <path d="M12 2.5l1.9 5.6 5.6 1.9-5.6 1.9L12 17.5l-1.9-5.6L4.5 10l5.6-1.9L12 2.5zM19 15.5l.8 2.2 2.2.8-2.2.8L19 21.5l-.8-2.2-2.2-.8 2.2-.8.8-2.2zM5 16l.6 1.7L7.3 18.3l-1.7.6L5 20.6l-.6-1.7L2.7 18.3l1.7-.6L5 16z" />
                </svg>

                {suggestion}
              </button>
            ))}
          </div>
        )}

        <form
          onSubmit={onSubmit}
          className="mx-auto flex max-w-3xl items-end gap-2 sm:gap-3"
        >
          {/* Nút chọn chế độ — gọn như bộ chọn model; bấm mới mở menu */}
          <div ref={modePickerRef} className="relative shrink-0">
            <button
              type="button"
              onClick={() => setModeMenuOpen((open) => !open)}
              disabled={streaming}
              aria-haspopup="menu"
              aria-expanded={modeMenuOpen}
              title="Chế độ truy xuất"
              className="flex h-12 items-center gap-1.5 rounded-2xl border border-slate-700/80 bg-slate-900/80 px-3 text-xs font-medium text-slate-200 shadow-inner shadow-black/20 backdrop-blur transition duration-150 hover:bg-slate-800 active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-50"
            >
              <svg
                aria-hidden="true"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="h-4 w-4 shrink-0 text-blue-400"
              >
                <path d="m12 14 4-4" />
                <path d="M3.34 19a10 10 0 1 1 17.32 0" />
              </svg>

              <span>{currentModeOption.label}</span>

              <svg
                aria-hidden="true"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className={`h-3.5 w-3.5 shrink-0 text-slate-400 transition-transform duration-200 ${
                  modeMenuOpen ? "rotate-180" : ""
                }`}
              >
                <path d="m6 9 6 6 6-6" />
              </svg>
            </button>

            {modeMenuOpen && (
              <div
                role="menu"
                aria-label="Chế độ tốc độ truy xuất"
                className="animate-fade-in absolute bottom-full left-0 z-40 mb-2 w-72 max-w-[78vw] overflow-hidden rounded-2xl border border-slate-700/80 bg-slate-900 shadow-2xl shadow-black/50"
              >
                <div className="border-b border-slate-800 px-3.5 py-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                  Chế độ truy xuất
                </div>

                {RETRIEVAL_MODE_OPTIONS.map((option) => {
                  const isActive = option.value === retrievalMode;

                  return (
                    <button
                      key={option.value}
                      type="button"
                      role="menuitemradio"
                      aria-checked={isActive}
                      onClick={() => {
                        onRetrievalModeChange(option.value);
                        setModeMenuOpen(false);
                      }}
                      className={`flex w-full items-start gap-2.5 px-3.5 py-2.5 text-left transition duration-150 active:scale-[0.99] ${
                        isActive ? "bg-blue-600/10" : "hover:bg-slate-800/80"
                      }`}
                    >
                      <span className="min-w-0 flex-1">
                        <span
                          className={`block text-sm font-medium ${
                            isActive ? "text-blue-300" : "text-slate-200"
                          }`}
                        >
                          {option.label}
                        </span>

                        <span className="block truncate text-xs text-slate-500">
                          {option.note}
                        </span>
                      </span>

                      {isActive && (
                        <svg
                          aria-hidden="true"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2.2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          className="mt-0.5 h-4 w-4 shrink-0 text-blue-400"
                        >
                          <path d="M20 6 9 17l-5-5" />
                        </svg>
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <textarea
            ref={textareaRef}
            value={question}
            onChange={(event) => onQuestionChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();

                event.currentTarget.form?.requestSubmit();
              }
            }}
            placeholder={
              !selectedSessionId
                ? "Tạo session trước..."
                : !hasReadyDocument
                  ? "Upload PDF trước..."
                  : "Hỏi AIRA về tài liệu..."
            }
            disabled={!selectedSessionId || !hasReadyDocument || streaming}
            rows={1}
            className="min-h-12 max-h-[160px] flex-1 resize-none rounded-2xl border border-slate-700/80 bg-slate-900/80 px-3.5 py-3 text-base md:text-sm shadow-inner shadow-black/20 outline-none backdrop-blur transition placeholder:text-slate-500 focus:border-blue-400 focus:ring-4 focus:ring-blue-500/25 disabled:cursor-not-allowed disabled:opacity-50"
          />

          <button
            type="submit"
            disabled={streaming || !question.trim() || !hasReadyDocument}
            className="flex min-h-[44px] sm:min-h-12 shrink-0 items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 sm:px-5 font-medium text-white shadow-md shadow-blue-600/30 transition duration-150 hover:brightness-110 active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-40 disabled:shadow-none"
          >
            {streaming ? (
              <span className="flex items-center gap-2">
                <svg
                  className="h-4 w-4 animate-spin text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                <span className="hidden sm:inline text-xs">Đang soạn...</span>
              </span>
            ) : (
              <>
                <svg
                  aria-hidden="true"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  className="h-4 w-4"
                >
                  <path d="M3.4 20.4l17.8-7.5c.8-.35.8-1.45 0-1.8L3.4 3.6c-.66-.29-1.46.2-1.46.91L2 9.12c0 .5.37.93.87.99L17 12 2.87 13.88c-.5.07-.87.5-.87 1l.01 4.61c0 .77.75 1.24 1.39.91z" />
                </svg>
                Send
              </>
            )}
          </button>
        </form>

        <div className="mx-auto mt-2 max-w-3xl text-center text-xs text-slate-600">
          AIRA chỉ trả lời dựa trên tài liệu đã upload.
        </div>
      </div>
    </>
  );
}

// Chỉ báo giai đoạn trong lúc chờ câu trả lời: chuyển theo mốc
// thời gian phía client (0s / 1,2s / 2,5s), không phải tín hiệu
// thật từ backend.
function StreamingProgress() {
  const [stage, setStage] = useState(0);

  useEffect(() => {
    const startedAt = Date.now();

    const timer = setInterval(() => {
      const elapsed = Date.now() - startedAt;

      setStage(elapsed < 1200 ? 0 : elapsed < 2500 ? 1 : 2);
    }, 150);

    return () => clearInterval(timer);
  }, []);

  return (
    <div className="flex items-center gap-2 text-sm text-blue-400">
      <span className="relative flex h-2 w-2 shrink-0">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-60" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-blue-400" />
      </span>

      <span className="animate-pulse">{STREAM_STAGES[stage]}</span>
    </div>
  );
}

function MessageBubble({
  message,
  isStreamingLast = false,
}: {
  message: UiMessage;
  isStreamingLast?: boolean;
}) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="aira-msg-in flex justify-end">
        <div className="max-w-[95%] sm:max-w-[85%] rounded-2xl rounded-br-md bg-gradient-to-br from-blue-600 to-indigo-600 px-4 py-3 text-white shadow-lg shadow-blue-950/40 ring-1 ring-white/10">
          <div className="whitespace-pre-wrap text-sm leading-7">
            {message.content || "..."}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="aira-msg-in flex justify-start">
      <div className="flex w-full gap-2.5 sm:gap-3 rounded-2xl border border-slate-800 bg-slate-900/60 p-3 sm:p-4 shadow-lg shadow-black/25 backdrop-blur-sm">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 text-[11px] font-bold text-white shadow-md shadow-blue-500/30 ring-1 ring-white/15">
          AI
        </div>

        <div className="min-w-0 flex-1">
          <div className="mb-2 text-xs font-bold uppercase tracking-wider text-blue-400">
            AIRA
          </div>

          {/* Câu trả lời của AIRA được render markdown (in đậm, danh
              sách, tiêu đề...). Nội dung đang stream là markdown chưa
              hoàn chỉnh — react-markdown vẫn render an toàn, không lỗi. */}
          <div className="aira-markdown text-sm leading-7">
            <ReactMarkdown>{message.content || "..."}</ReactMarkdown>
            {isStreamingLast && (
              <span className="inline-block h-4 w-1.5 ml-1 bg-blue-400 animate-pulse align-middle" />
            )}
          </div>

          {message.responseTimeSec !== undefined && (
            <div className="mt-2 text-xs text-slate-500">
              Trả lời trong{" "}
              {message.responseTimeSec.toFixed(1).replace(".", ",")} giây ·{" "}
              {message.citations.length} nguồn trích dẫn
            </div>
          )}

          {message.citations.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {message.citations.map((citation) => (
                <details
                  key={`${message.id}-${citation.index}`}
                  className="rounded-xl border border-slate-700/80 bg-slate-900/80 text-xs transition duration-150 hover:border-blue-400/60 hover:shadow-[0_0_0_1px_rgba(96,165,250,0.25)]"
                >
                  <summary className="cursor-pointer px-3 py-2 text-blue-300">
                    [{citation.index}] {citation.doc_name}
                    {" · "}
                    Trang {citation.page}
                  </summary>

                  <div className="max-w-2xl border-t border-slate-700/80 p-3">
                    <div className="mb-2 text-[11px] font-medium uppercase tracking-wide text-slate-500">
                      Đoạn đầy đủ AIRA đã dùng làm ngữ cảnh
                    </div>

                    <div className="whitespace-pre-wrap break-words text-sm leading-6 text-slate-300">
                      {citation.text || citation.snippet}
                    </div>
                  </div>
                </details>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
