import { ChatSession } from "@/lib/types";

interface HistoryPanelProps {
  sessions: ChatSession[];
  selectedSessionId: string | null;
  loadingSessions: boolean;
  deletingSessionId: string | null;
  onNewChat: () => void;
  onSelectSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string, title: string | null) => void;
  onClose?: () => void;
}

export default function HistoryPanel({
  sessions,
  selectedSessionId,
  loadingSessions,
  deletingSessionId,
  onNewChat,
  onSelectSession,
  onDeleteSession,
  onClose,
}: HistoryPanelProps) {
  return (
    <aside className="flex h-full w-72 shrink-0 flex-col border-r border-slate-800/80 bg-slate-900/95 md:bg-slate-900/60 backdrop-blur shadow-2xl md:shadow-none">
      <div className="border-b border-slate-800/80 p-5">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 via-blue-600 to-indigo-700 text-sm font-bold text-white shadow-lg shadow-blue-500/25 ring-1 ring-white/15">
              AI
            </div>

            <div>
              <div className="text-xl font-bold tracking-tight">AIRA</div>

              <div className="text-xs text-slate-400">
                AI Retrieval Assistant
              </div>
            </div>
          </div>

          {onClose && (
            <button
              type="button"
              onClick={onClose}
              aria-label="Đóng thanh bên"
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-slate-700/70 bg-slate-800/80 text-slate-300 transition duration-150 hover:bg-slate-700 hover:text-white active:scale-[0.97] md:hidden"
            >
              <svg
                aria-hidden="true"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="h-4 w-4"
              >
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        <button
          onClick={onNewChat}
          className="mt-5 flex min-h-[40px] w-full items-center justify-center rounded-2xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2.5 text-sm font-medium text-white shadow-md shadow-blue-600/30 transition duration-150 hover:brightness-110 active:scale-[0.97]"
        >
          + New Chat
        </button>
      </div>

      <div className="px-5 pb-2 pt-5 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
        Sessions
      </div>

      <div className="flex-1 overflow-y-auto px-3 pb-4">
        {loadingSessions ? (
          <div className="space-y-2 px-1 py-2">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="h-12 w-full animate-pulse rounded-xl bg-slate-800/50"
              />
            ))}
          </div>
        ) : sessions.length === 0 ? (
          <div className="px-3 py-4 text-sm text-slate-500">
            Chưa có session.
          </div>
        ) : (
          sessions.map((session) => {
            const active = session.id === selectedSessionId;

            const deleting = deletingSessionId === session.id;

            return (
              <div
                key={session.id}
                className={`group relative mb-1 flex items-center rounded-xl transition duration-150 active:scale-[0.98] ${
                  active
                    ? "bg-gradient-to-r from-blue-600/25 via-blue-600/10 to-transparent ring-1 ring-blue-500/25"
                    : "hover:bg-slate-800/80"
                }`}
              >
                {active && (
                  <span className="absolute bottom-2.5 left-0 top-2.5 w-1 rounded-full bg-gradient-to-b from-blue-400 to-indigo-500" />
                )}
                <button
                  onClick={() => onSelectSession(session.id)}
                  className="min-w-0 flex-1 px-3 py-3 text-left"
                >
                  <div className="truncate text-sm font-medium">
                    {session.title || "Untitled"}
                  </div>

                  <div className="mt-1 truncate text-[11px] text-slate-500">
                    {session.id}
                  </div>
                </button>

                <button
                  onClick={() => void onDeleteSession(session.id, session.title)}
                  disabled={deleting}
                  title="Xóa cuộc trò chuyện"
                  className="mr-2 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-lg text-slate-500 opacity-0 transition hover:bg-red-950 hover:text-red-400 group-hover:opacity-100 disabled:opacity-40"
                >
                  {deleting ? "…" : "×"}
                </button>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
}
