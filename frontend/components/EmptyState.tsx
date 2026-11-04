export default function EmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="text-center">
        <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500/25 via-blue-600/20 to-indigo-600/25 shadow-lg shadow-blue-950/40 ring-1 ring-blue-400/30">
          <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="currentColor"
            className="h-7 w-7 text-blue-300"
          >
            <path d="M12 2.5l1.9 5.6 5.6 1.9-5.6 1.9L12 17.5l-1.9-5.6L4.5 10l5.6-1.9L12 2.5zM19 15.5l.8 2.2 2.2.8-2.2.8L19 21.5l-.8-2.2-2.2-.8 2.2-.8.8-2.2zM5 16l.6 1.7 1.7.6-1.7.6L5 20.6l-.6-1.7-1.7-.6 1.7-.6L5 16z" />
          </svg>
        </div>

        <div className="text-2xl font-semibold tracking-tight text-slate-100">
          {title}
        </div>

        <div className="mt-2 text-sm leading-6 text-slate-500">
          {description}
        </div>
      </div>
    </div>
  );
}
