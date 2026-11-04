import { RagDocument } from "@/lib/types";

interface DocumentLibraryProps {
  documents: RagDocument[];
}

export default function DocumentLibrary({ documents }: DocumentLibraryProps) {
  return (
    <div className="mt-1 flex flex-wrap gap-2">
      {documents.map((document) => (
        <span
          key={document.id}
          className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs ${
            document.status === "ready"
              ? "border-emerald-500/40 bg-emerald-950/70 text-emerald-300 shadow-[0_0_10px_rgba(16,185,129,0.25)]"
              : document.status === "failed"
                ? "border-red-800 bg-red-950 text-red-300"
                : "border-amber-800 bg-amber-950 text-amber-300"
          }`}
        >
          {document.status === "ready" && (
            <span className="relative flex h-1.5 w-1.5 shrink-0">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-400" />
            </span>
          )}

          {document.name}
          {" · "}
          {document.status}
        </span>
      ))}
    </div>
  );
}
