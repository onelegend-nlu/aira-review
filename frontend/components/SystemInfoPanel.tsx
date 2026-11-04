const PIPELINE_STEPS = [
  "Chia đoạn 512 token (chồng lấp 10%)",
  "Embedding multilingual-e5-small",
  "Truy xuất lai: Dense + BM25",
  "Hợp nhất RRF (k=60)",
  "Pool 40 ứng viên",
  "Reranker bge-reranker-base",
  "Top-5 đoạn",
  "Gemini sinh câu trả lời có trích dẫn",
];

// Ba chế độ tốc độ truy xuất: chỉ khác nhau ở pool đưa
// vào reranker. Thời gian rerank tương đối và ExcerptHit
// của Trung bình/Nhanh đo trên tập dev (kiểm định E7);
// chỉ Lâu (mặc định) có số test chính thức 94,1%.
const SPEED_MODE_ROWS: Array<[string, string, string, string]> = [
  ["Lâu (mặc định)", "40", "100% (chuẩn)", "0,907 (dev) · 94,1% (test)"],
  ["Trung bình", "20", "~53%", "0,884 (dev)"],
  ["Nhanh", "10", "~28–32%", "0,872 (dev)"],
];

const CONFIG_ROWS: Array<[string, string]> = [
  ["Chunking", "512 token / overlap 10%"],
  ["Embedding", "multilingual-e5-small"],
  ["Retrieval", "Dense + BM25"],
  ["Fusion", "RRF, k=60"],
  ["Candidate Pool", "40"],
  ["Reranker", "bge-reranker-base"],
  ["Final Top-K", "5"],
  ["Generation", "Gemini"],
];

export default function SystemInfoPanel() {
  return (
    <div className="flex-1 overflow-y-auto px-3 py-4 sm:px-6 sm:py-6">
      <div className="mx-auto flex max-w-4xl flex-col gap-8">
        {/* MÔ TẢ */}
        <section>
          <h2 className="mb-3 flex items-center gap-2.5 text-base font-semibold tracking-tight text-slate-100">
            <span className="h-4 w-1 rounded-full bg-gradient-to-b from-blue-400 to-indigo-500" />
            AIRA là gì?
          </h2>

          <p className="text-sm leading-7 text-slate-300">
            AIRA (AI Retrieval Assistant) là trợ lý học tập giúp tra cứu và hỏi
            đáp trực tiếp trên tài liệu PDF tiếng Việt mà người dùng nạp vào.
            Mọi câu trả lời chỉ dựa trên nội dung tài liệu đã nạp, kèm trích
            dẫn tới đúng trang và đoạn nguồn; khi tài liệu không có căn cứ, hệ
            thống từ chối trả lời thay vì suy đoán.
          </p>
        </section>

        {/* PIPELINE */}
        <section>
          <h2 className="mb-3 flex items-center gap-2.5 text-base font-semibold tracking-tight text-slate-100">
            <span className="h-4 w-1 rounded-full bg-gradient-to-b from-blue-400 to-indigo-500" />
            Quy trình xử lý (pipeline)
          </h2>

          <div className="flex flex-wrap items-center gap-2">
            {PIPELINE_STEPS.map((step, index) => (
              <div key={step} className="flex items-center gap-2">
                <div className="flex items-center rounded-xl border border-blue-400/20 bg-gradient-to-br from-slate-900 to-slate-900/40 px-3 py-2 text-sm text-slate-200 shadow-md shadow-black/20">
                  <span className="mr-2 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 text-[11px] font-bold text-white shadow-sm shadow-blue-950/50">
                    {index + 1}
                  </span>

                  {step}
                </div>

                {index < PIPELINE_STEPS.length - 1 && (
                  <svg
                    aria-hidden="true"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="h-4 w-4 shrink-0 text-blue-400"
                  >
                    <path d="M4 12h15M13 6l6 6-6 6" />
                  </svg>
                )}
              </div>
            ))}
          </div>
        </section>

        {/* CẤU HÌNH */}
        <section>
          <h2 className="mb-3 flex items-center gap-2.5 text-base font-semibold tracking-tight text-slate-100">
            <span className="h-4 w-1 rounded-full bg-gradient-to-b from-blue-400 to-indigo-500" />
            Cấu hình chính thức
          </h2>

          <div className="overflow-x-auto rounded-2xl border border-slate-800 shadow-lg shadow-black/20">
            <div className="min-w-[320px]">
              {CONFIG_ROWS.map(([label, value], index) => (
                <div
                  key={label}
                  className={`flex items-center justify-between gap-4 px-4 py-3 text-sm transition hover:bg-blue-500/5 ${
                    index % 2 === 0 ? "bg-slate-900/60" : "bg-slate-950/60"
                  }`}
                >
                  <span className="text-slate-400">{label}</span>
                  <span className="font-medium text-slate-100">{value}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* BA CHẾ ĐỘ TRUY XUẤT */}
        <section>
          <h2 className="mb-3 flex items-center gap-2.5 text-base font-semibold tracking-tight text-slate-100">
            <span className="h-4 w-1 rounded-full bg-gradient-to-b from-blue-400 to-indigo-500" />
            Ba chế độ truy xuất
          </h2>

          <div className="overflow-x-auto rounded-2xl border border-slate-800 shadow-lg shadow-black/20">
            <div className="min-w-[480px]">
              <div className="grid grid-cols-[1.1fr_0.4fr_1fr_1.3fr] gap-4 bg-slate-900 px-4 py-2.5 text-[11px] font-medium uppercase tracking-wide text-slate-500">
                <span>Chế độ</span>
                <span>Pool</span>
                <span>Thời gian rerank (tương đối)</span>
                <span>ExcerptHit</span>
              </div>

              {SPEED_MODE_ROWS.map(([mode, pool, rerankTime, hit], index) => (
                <div
                  key={mode}
                  className={`grid grid-cols-[1.1fr_0.4fr_1fr_1.3fr] gap-4 px-4 py-3 text-sm transition hover:bg-blue-500/5 ${
                    index % 2 === 0 ? "bg-slate-900/60" : "bg-slate-950/60"
                  }`}
                >
                  <span className="font-medium text-slate-100">{mode}</span>
                  <span className="text-slate-300">{pool}</span>
                  <span className="text-slate-300">{rerankTime}</span>
                  <span className="text-slate-300">{hit}</span>
                </div>
              ))}
            </div>
          </div>

          <p className="mt-3 text-xs leading-5 text-slate-400">
            Số liệu của Trung bình và Nhanh đo trên tập dev trong kiểm định
            E7; chỉ chế độ Lâu có số test chính thức 94,1%. Ba chế độ chỉ
            khác nhau ở số ứng viên đưa vào reranker — mọi khâu còn lại giữ
            nguyên cấu hình winner E7.
          </p>
        </section>

        {/* KẾT QUẢ KIỂM ĐỊNH */}
        <section className="rounded-2xl border border-blue-500/30 bg-gradient-to-br from-blue-950/60 via-slate-900/60 to-indigo-950/40 px-5 py-5 shadow-lg shadow-blue-950/30">
          <h2 className="mb-3 flex items-center gap-2.5 text-base font-semibold tracking-tight text-slate-100">
            <span className="h-4 w-1 rounded-full bg-gradient-to-b from-blue-400 to-indigo-500" />
            Kết quả kiểm định
          </h2>

          <p className="text-sm leading-6 text-slate-300">
            ExcerptHit@5 trên tập test E7:
          </p>

          <div className="mt-1 flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className="bg-gradient-to-r from-blue-300 via-sky-300 to-indigo-300 bg-clip-text text-5xl font-extrabold tracking-tight text-transparent">
              94,1%
            </span>

            <span className="text-sm leading-6 text-slate-200">
              (cấu hình chính thức) so với{" "}
              <span className="font-semibold text-slate-100">70,6%</span>{" "}
              (cấu hình gốc).
            </span>
          </div>

          <p className="mt-3 text-xs leading-5 text-slate-400">
            Đánh giá trên bộ 120 câu hỏi tiếng Việt, tập test 34 câu (E7); hệ
            thống trả lời kèm trích dẫn và từ chối khi tài liệu không có căn
            cứ.
          </p>
        </section>
      </div>
    </div>
  );
}
