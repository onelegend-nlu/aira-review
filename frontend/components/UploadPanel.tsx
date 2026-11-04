import { ChangeEvent, DragEvent, useRef, useState } from "react";

interface UploadPanelProps {
  uploading: boolean;
  // Khi đã có tài liệu ready, khu upload thu gọn thành một
  // thanh nhỏ để nhường khung cho chat; chưa có tài liệu thì
  // hiển thị dạng đầy đủ, dễ thấy.
  compact?: boolean;
  // Chọn/thả file là TỰ ĐỘNG upload ngay (không còn nút
  // "Upload PDF" riêng) — trang cha nhận file và gọi API.
  onFileChosen: (file: File) => void;
}

function isPdfFile(file: File) {
  return file.name.toLowerCase().endsWith(".pdf");
}

export default function UploadPanel({
  uploading,
  compact = false,
  onFileChosen,
}: UploadPanelProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragging, setDragging] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);

  function acceptFile(file: File | null) {
    if (!file || uploading) {
      return;
    }

    if (!isPdfFile(file)) {
      setFileError("Chỉ nhận file PDF (.pdf).");
      return;
    }

    setFileError(null);
    onFileChosen(file);
  }

  function handleInputChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;

    // Reset ngay để chọn lại đúng file đó (sau lỗi hoặc sau
    // khi đã upload xong) vẫn kích hoạt sự kiện change.
    event.target.value = "";

    acceptFile(file);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);

    acceptFile(event.dataTransfer.files?.[0] ?? null);
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <div
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={`flex items-center gap-2 rounded-2xl border border-dashed transition ${
          compact ? "px-1.5 py-1" : "px-2 py-1"
        } ${
          dragging
            ? "border-blue-400 bg-blue-500/10 shadow-[0_0_0_1px_rgba(96,165,250,0.45),0_0_16px_rgba(59,130,246,0.25)]"
            : "border-slate-700/70"
        }`}
      >
        <input
          ref={inputRef}
          id="pdf-input"
          type="file"
          accept=".pdf,application/pdf"
          onChange={handleInputChange}
          className="hidden"
        />

        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
          className={`flex min-h-[40px] items-center rounded-xl border border-slate-700/70 bg-slate-800/80 text-slate-200 transition duration-150 hover:bg-slate-700 active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-50 ${
            compact ? "px-3 py-1.5 text-xs" : "px-4 py-2 text-sm"
          }`}
        >
          {uploading ? "Đang xử lý..." : compact ? "+ Thêm PDF" : "Chọn PDF"}
        </button>

        {!compact && (
          <span className="flex max-w-48 items-center gap-1.5 truncate text-sm text-slate-400">
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-4 w-4 shrink-0 text-red-400/80"
            >
              <path d="M14 2.5H6.5a2 2 0 0 0-2 2v15a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V8z" />
              <path d="M14 2.5V8h5.5" />
              <path d="M8.5 13.5h7M8.5 17h4.5" />
            </svg>

            <span className="min-w-0 truncate">
              {uploading ? "Đang tải lên..." : "Kéo thả PDF vào đây"}
            </span>
          </span>
        )}
      </div>

      {fileError && <div className="text-xs text-red-300">{fileError}</div>}
    </div>
  );
}
