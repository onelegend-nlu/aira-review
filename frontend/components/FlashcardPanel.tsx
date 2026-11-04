import EmptyState from "@/components/EmptyState";
import { Flashcard } from "@/lib/types";

interface FlashcardPanelProps {
  selectedSessionId: string | null;
  hasReadyDocument: boolean;
  loading: boolean;
  flashcards: Flashcard[];
  currentIndex: number;
  flipped: boolean;
  generating: boolean;
  deletingFlashcardId: string | null;
  onGenerate: () => void;
  onFlip: () => void;
  onPrevious: () => void;
  onNext: () => void;
  onDelete: (flashcardId: string) => void;
}

export default function FlashcardPanel({
  selectedSessionId,
  hasReadyDocument,
  loading,
  flashcards,
  currentIndex,
  flipped,
  generating,
  deletingFlashcardId,
  onGenerate,
  onFlip,
  onPrevious,
  onNext,
  onDelete,
}: FlashcardPanelProps) {
  const card = flashcards[currentIndex] ?? null;

  if (!selectedSessionId) {
    return (
      <div className="flex-1 px-6 py-6">
        <EmptyState
          title="Chưa có cuộc trò chuyện"
          description="Tạo New Chat để bắt đầu."
        />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex-1 px-6 py-6">
        <EmptyState title="Đang tải" description="Đang lấy flashcards..." />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-3 py-4 sm:px-6 sm:py-6">
      <div className="mx-auto flex h-full max-w-4xl flex-col">
        <div className="mb-4 sm:mb-5 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base sm:text-lg font-semibold tracking-tight">Flashcards</h2>

            <p className="mt-0.5 sm:mt-1 text-xs sm:text-sm text-slate-500">
              Ôn tập nhanh từ nội dung PDF đã upload.
            </p>
          </div>

          <button
            onClick={onGenerate}
            disabled={generating || !hasReadyDocument}
            className="flex min-h-[40px] items-center rounded-2xl bg-gradient-to-r from-blue-600 to-indigo-600 px-3.5 sm:px-4 py-2 sm:py-2.5 text-xs sm:text-sm font-medium shadow-md shadow-blue-950/50 transition duration-150 hover:from-blue-500 hover:to-indigo-500 active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-40 disabled:shadow-none"
          >
            {generating
              ? "Đang tạo..."
              : flashcards.length > 0
                ? "Tạo lại 10 thẻ"
                : "Tạo 10 flashcards"}
          </button>
        </div>

        {!hasReadyDocument ? (
          <div className="flex-1">
            <EmptyState
              title="Chưa có tài liệu"
              description="Upload ít nhất một PDF và đợi trạng thái ready trước khi tạo flashcards."
            />
          </div>
        ) : !card ? (
          <div className="flex-1">
            <EmptyState
              title="Chưa có flashcard"
              description="Nhấn Tạo 10 flashcards để AIRA tạo bộ thẻ ôn tập từ tài liệu trong session này."
            />
          </div>
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center pb-8">
            <div className="mb-4 rounded-full border border-slate-700/80 bg-slate-900/80 px-3.5 py-1.5 text-xs font-medium uppercase tracking-wider text-slate-400 shadow-md shadow-black/20">
              Thẻ {currentIndex + 1}
              {" / "}
              {flashcards.length}
            </div>

            <button
              onClick={onFlip}
              className="flex min-h-60 sm:min-h-72 w-full max-w-2xl flex-col justify-between rounded-3xl border border-blue-400/20 bg-gradient-to-br from-slate-900 via-slate-900 to-indigo-950/40 p-5 sm:p-8 text-left shadow-2xl shadow-black/40 ring-1 ring-white/5 transition duration-150 hover:-translate-y-0.5 hover:border-blue-400/50 hover:shadow-blue-950/40 active:scale-[0.98]"
            >
              <div>
                <div className="mb-4 text-xs font-bold uppercase tracking-wider text-blue-400">
                  {flipped ? "Đáp án" : "Câu hỏi"}
                </div>

                <div className="whitespace-pre-wrap text-base sm:text-lg leading-7 sm:leading-8 text-slate-100">
                  {flipped ? card.answer : card.question}
                </div>
              </div>

              <div className="mt-6 sm:mt-8 border-t border-slate-800 pt-3 sm:pt-4">
                <div className="text-xs text-slate-500">
                  Nguồn: {card.document_name}
                  {" · "}
                  Trang {card.source_page}
                </div>

                <div className="mt-1 sm:mt-2 text-xs text-slate-600">
                  Nhấn vào thẻ để {flipped ? "xem lại câu hỏi" : "lật xem đáp án"}.
                </div>
              </div>
            </button>

            <div className="mt-4 sm:mt-5 flex w-full max-w-2xl items-center justify-between gap-2 sm:gap-3">
              <button
                onClick={onPrevious}
                disabled={currentIndex === 0}
                className="flex min-h-[40px] items-center rounded-xl border border-slate-700/60 bg-slate-800/80 px-3.5 sm:px-4 py-2 text-xs sm:text-sm transition duration-150 hover:bg-slate-700 active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-40"
              >
                ← Trước
              </button>

              <button
                onClick={() => onDelete(card.id)}
                disabled={deletingFlashcardId === card.id}
                className="flex min-h-[40px] items-center rounded-xl border border-red-900/70 px-3.5 sm:px-4 py-2 text-xs sm:text-sm text-red-400 transition duration-150 hover:bg-red-950 active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-40"
              >
                {deletingFlashcardId === card.id ? "Đang xóa..." : "Xóa thẻ"}
              </button>

              <button
                onClick={onNext}
                disabled={currentIndex >= flashcards.length - 1}
                className="flex min-h-[40px] items-center rounded-xl border border-slate-700/60 bg-slate-800/80 px-3.5 sm:px-4 py-2 text-xs sm:text-sm transition duration-150 hover:bg-slate-700 active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-40"
              >
                Sau →
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
