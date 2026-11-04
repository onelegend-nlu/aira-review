"""
Chunking theo câu (sentence-aware), thay cho cửa sổ từ mù trước đây.

Nguyên tắc:
- Không cắt giữa câu nếu tránh được: đóng gói các câu nguyên vẹn
  vào chunk cho tới khi đạt ~chunk_size từ.
- Câu đơn lẻ dài hơn chunk_size mới bị cắt bằng cửa sổ từ.
- Overlap ở mức câu: chunk sau mở đầu bằng (các) câu cuối của
  chunk trước, tổng số từ của phần overlap <= overlap.
- Vẫn chunk trong từng trang (giữ đúng page cho citation/eval),
  định dạng trả về không đổi: {chunk_id, page, text}.

Default 100/20 khớp production (trước đây default của hàm là
180/30 trong khi mọi nơi gọi đều truyền 100/20 - bẫy config).
"""

import re


_SENTENCE_SPLIT_RE = re.compile(
    r"(?<=[.!?…])"          # kết thúc câu
    r"[\"”’\)\]]*\s+"       # dấu đóng + khoảng trắng
    r"(?=[A-ZÀ-Ỹ0-9\"“])"   # câu mới bắt đầu
)


def _split_segments(text):
    """Tách text thành các đoạn nhỏ: theo dòng, rồi theo câu."""
    segments = []

    for line in text.splitlines():
        line = " ".join(line.split())

        if not line:
            continue

        parts = _SENTENCE_SPLIT_RE.split(line)

        for part in parts:
            part = part.strip()

            if part:
                segments.append(part)

    return segments


def _word_window_split(segment, chunk_size, overlap):
    """Cắt một câu/đoạn quá dài bằng cửa sổ từ (hành vi cũ)."""
    words = segment.split()
    pieces = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        piece = " ".join(words[start:end])

        if piece.strip():
            pieces.append(piece)

        if end >= len(words):
            break

        start += max(1, chunk_size - overlap)

    return pieces


def chunk_pages(pages, chunk_size=100, overlap=20):
    chunks = []
    chunk_id = 0

    if chunk_size <= 0:
        raise ValueError("chunk_size phải > 0")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap phải thỏa 0 <= overlap < chunk_size")

    for page in pages:
        segments = _split_segments(page["text"])

        current = []        # list[(segment, word_count)]
        current_words = 0

        def flush():
            nonlocal chunk_id, current, current_words

            if not current:
                return

            text = " ".join(seg for seg, _ in current)

            if text.strip():
                chunks.append({
                    "chunk_id": chunk_id,
                    "page": page["page"],
                    "text": text,
                })
                chunk_id += 1

        for segment in segments:
            seg_words = len(segment.split())

            # Đoạn quá dài: đóng chunk hiện tại rồi cắt cửa sổ từ.
            if seg_words > chunk_size:
                flush()
                current = []
                current_words = 0

                for piece in _word_window_split(
                    segment, chunk_size, overlap
                ):
                    chunks.append({
                        "chunk_id": chunk_id,
                        "page": page["page"],
                        "text": piece,
                    })
                    chunk_id += 1

                continue

            # Đủ chỗ: thêm vào chunk hiện tại.
            if current_words + seg_words <= chunk_size:
                current.append((segment, seg_words))
                current_words += seg_words
                continue

            # Hết chỗ: đóng chunk, mang overlap (theo câu) sang.
            previous = current
            flush()

            carry = []
            carry_words = 0

            for seg, count in reversed(previous):
                if carry_words + count > overlap:
                    break

                carry.append((seg, count))
                carry_words += count

            carry.reverse()

            # Tránh lặp vô hạn khi carry + segment vẫn quá lớn:
            # chỉ giữ carry nếu cộng segment vẫn trong giới hạn.
            if carry_words + seg_words <= chunk_size:
                current = carry
                current_words = carry_words
            else:
                current = []
                current_words = 0

            current.append((segment, seg_words))
            current_words += seg_words

        flush()

    return chunks


# =========================================================
# TOKEN CHUNKER (cấu hình thắng E7: 512 token / overlap 51)
# Port nguyên bản cửa sổ trượt token theo trang từ harness
# thí nghiệm (token_chunk_pages) để app chạy đúng cấu hình
# đã đo: chunk 512 token, overlap 10%, cắt theo trang.
# =========================================================

_TOKENIZER = None


def _get_tokenizer():
    global _TOKENIZER

    if _TOKENIZER is None:
        from transformers import AutoTokenizer

        _TOKENIZER = AutoTokenizer.from_pretrained(
            "intfloat/multilingual-e5-small"
        )

    return _TOKENIZER


def chunk_pages_token(pages, size_tokens=512, overlap_tokens=51):
    if size_tokens <= 0:
        raise ValueError("size_tokens phải > 0")

    if overlap_tokens < 0 or overlap_tokens >= size_tokens:
        raise ValueError("overlap_tokens phải thỏa 0 <= overlap < size")

    tokenizer = _get_tokenizer()

    chunks = []
    chunk_id = 0
    step = max(1, size_tokens - overlap_tokens)

    for page in pages:
        ids = tokenizer.encode(
            page["text"],
            add_special_tokens=False
        )

        for start in range(0, max(1, len(ids)), step):
            window = ids[start:start + size_tokens]

            if not window:
                continue

            text = tokenizer.decode(window).strip()

            if text:
                chunks.append({
                    "chunk_id": chunk_id,
                    "page": page["page"],
                    "text": text,
                })
                chunk_id += 1

            if start + size_tokens >= len(ids):
                break

    return chunks


def chunk_pages_production(pages):
    """Điểm vào chunking duy nhất của ingest.

    CHUNK_MODE=token (mặc định, cấu hình thắng E7):
        chunk_pages_token với CHUNK_SIZE_TOKENS /
        CHUNK_OVERLAP_TOKENS từ src.config.
    CHUNK_MODE=sentence (hành vi của bản vá v1):
        chunk_pages theo câu với CHUNK_SIZE / CHUNK_OVERLAP.
    """
    from src import config

    if config.CHUNK_MODE == "token":
        return chunk_pages_token(
            pages,
            size_tokens=config.CHUNK_SIZE_TOKENS,
            overlap_tokens=config.CHUNK_OVERLAP_TOKENS,
        )

    return chunk_pages(
        pages,
        chunk_size=config.CHUNK_SIZE,
        overlap=config.CHUNK_OVERLAP,
    )
