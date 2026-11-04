"""
Cấu hình tập trung của AIRA.

Mọi hằng số dùng chung (chunking, retrieval, upload, model)
chỉ định nghĩa MỘT lần tại đây để tránh lệch nhau giữa
api.py / main.py / ingest / generator như trước đây.

Giá trị có thể ghi đè bằng biến môi trường trong .env.
"""

import os

from dotenv import load_dotenv


load_dotenv()


# =========================================================
# CHUNKING (production)
# =========================================================

# Chế độ chunking production:
#   "token"    = cửa sổ token 512/51 — cấu hình thắng E7
#                (test excerpt-hit 0.941 so với 0.706 của
#                cấu hình gốc; xem PATCH_NOTES_V2.md).
#   "sentence" = chunker theo câu của bản vá v1 (100 từ/20).
CHUNK_MODE = os.getenv("AIRA_CHUNK_MODE", "token")

CHUNK_SIZE_TOKENS = int(os.getenv("AIRA_CHUNK_SIZE_TOKENS", "512"))
CHUNK_OVERLAP_TOKENS = int(os.getenv("AIRA_CHUNK_OVERLAP_TOKENS", "51"))

# Chỉ dùng khi CHUNK_MODE=sentence.
CHUNK_SIZE = int(os.getenv("AIRA_CHUNK_SIZE", "100"))
CHUNK_OVERLAP = int(os.getenv("AIRA_CHUNK_OVERLAP", "20"))


# =========================================================
# RETRIEVAL
# =========================================================

# hybrid = dense + BM25 hợp nhất RRF rồi rerank trên pool
# (cấu hình thắng E7). dense = hành vi cũ của bản vá v1.
RETRIEVAL_MODE = os.getenv("AIRA_RETRIEVAL_MODE", "hybrid")
BM25_K1 = float(os.getenv("AIRA_BM25_K1", "1.5"))
BM25_B = float(os.getenv("AIRA_BM25_B", "0.75"))
RRF_K = int(os.getenv("AIRA_RRF_K", "60"))

CANDIDATE_K = int(os.getenv("AIRA_CANDIDATE_K", "40"))
TOP_K = int(os.getenv("AIRA_TOP_K", "5"))


# =========================================================
# CHẾ ĐỘ TỐC ĐỘ TRUY XUẤT (chọn theo từng request chat)
# =========================================================

# Ba chế độ chỉ khác nhau ở POOL ứng viên đưa vào reranker
# (khâu chiếm gần như toàn bộ thời gian truy xuất theo đo
# kiểm định Pareto). Mọi khâu còn lại — chunking, embedding,
# BM25, RRF k=60, top-5, prompt, fallback — giữ nguyên cấu
# hình winner E7 ở mọi chế độ.
#
#   lau        = pool 40: winner E7 nguyên bản, MẶC ĐỊNH
#                (ExcerptHit dev 0,907; con số test chính
#                thức 94,1% chỉ thuộc về chế độ này).
#   trung_binh = pool 20: thời gian rerank ~53%,
#                ExcerptHit dev 0,884.
#   nhanh      = pool 10: thời gian rerank ~28–32%,
#                ExcerptHit dev 0,872.
#
# Số của trung_binh/nhanh đo trên tập DEV trong kiểm định,
# không phải số test chính thức. Ánh xạ này là nguồn duy
# nhất cho pool theo chế độ; CANDIDATE_K phía trên không
# đổi và vẫn là pool của chế độ mặc định.
RETRIEVAL_MODES = {
    "lau": 40,
    "trung_binh": 20,
    "nhanh": 10,
}

DEFAULT_MODE = "lau"


def candidate_k_for_mode(mode):
    """Pool rerank ứng với một chế độ tốc độ.

    mode thiếu (None/rỗng) hoặc không thuộc RETRIEVAL_MODES
    -> pool của chế độ mặc định. Không bao giờ ném lỗi:
    lựa chọn ở UI không được làm hỏng request chat.
    """

    return RETRIEVAL_MODES.get(
        mode,
        RETRIEVAL_MODES[DEFAULT_MODE],
    )
RECENT_MESSAGE_LIMIT = int(
    os.getenv("AIRA_RECENT_MESSAGE_LIMIT", "3")
)


# =========================================================
# UPLOAD
# =========================================================

# Giới hạn kích thước PDF upload (MB). Vượt quá -> HTTP 413.
MAX_UPLOAD_MB = float(os.getenv("AIRA_MAX_UPLOAD_MB", "50"))
MAX_UPLOAD_BYTES = int(MAX_UPLOAD_MB * 1024 * 1024)


# =========================================================
# GENERATOR
# =========================================================

# Khớp với GEMINI_MODEL trong .env.example.
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"


# =========================================================
# AUTH (tùy chọn)
# =========================================================

# Đặt AIRA_API_KEY trong .env để bật kiểm tra header
# X-API-Key cho mọi route /api/v1/*.
# Để trống = tắt auth (chỉ phù hợp khi chạy local một mình).
API_KEY = os.getenv("AIRA_API_KEY", "").strip()


# =========================================================
# RATE LIMIT (demo public)
# =========================================================

# Giới hạn số request POST chat/upload mỗi IP trong một phút
# (chống spam đốt quota, không phải cơ chế bảo mật).
# Đặt AIRA_RATE_LIMIT_PER_MIN=0 để tắt.
RATE_LIMIT_PER_MIN = int(
    os.getenv("AIRA_RATE_LIMIT_PER_MIN", "30")
)


# =========================================================
# PARSER
# =========================================================

# AIRA_OCR=1: thử OCR (pytesseract, nếu đã cài) cho trang
# PDF scan không có text layer. Mặc định tắt.
OCR_ENABLED = os.getenv("AIRA_OCR", "0") == "1"
