import json
import time

from src.parser import read_pdf
from src.chunker import chunk_pages
from src.retriever import Retriever
from src.generator import Generator


# =========================================================
# CONFIG
# =========================================================

PDF_PATH = "data/sample.pdf"

CHUNK_SIZE = 100
CHUNK_OVERLAP = 20

TOP_K = 3

# Threshold hiện tại.
# Ta vẫn dùng nó để quyết định có gọi Gemini hay không,
# nhưng cuối chương trình sẽ tự phân tích threshold tốt hơn.
CURRENT_GATE_THRESHOLD = 0.82

OUTPUT_FILE = "results_threshold_test.json"

# Nghỉ nhẹ giữa các lần gọi Gemini
API_DELAY_SECONDS = 0.5


# =========================================================
# TEST DATASET
# =========================================================

# expected_in_document:
# True  = câu hỏi thuộc nội dung tài liệu
# False = câu hỏi ngoài tài liệu

QUESTIONS = [

    # -----------------------------------------------------
    # IN-DOCUMENT
    # -----------------------------------------------------

    {
        "question": "Machine Learning là gì?",
        "expected_in_document": True
    },

    {
        "question": "Supervised Learning là gì?",
        "expected_in_document": True
    },

    {
        "question": "Unsupervised Learning là gì?",
        "expected_in_document": True
    },

    {
        "question": "Reinforcement Learning là gì?",
        "expected_in_document": True
    },

    {
        "question": "Machine Learning có những loại nào?",
        "expected_in_document": True
    },

    {
        "question": "Machine Learning hoạt động như thế nào?",
        "expected_in_document": True
    },

    {
        "question": "Dữ liệu có vai trò gì trong Machine Learning?",
        "expected_in_document": True
    },

    {
        "question": "Quy trình Machine Learning gồm những bước nào?",
        "expected_in_document": True
    },

    {
        "question": "SVM là gì?",
        "expected_in_document": True
    },

    {
        "question": "Support Vector là gì?",
        "expected_in_document": True
    },

    {
        "question": "RBF kernel là gì?",
        "expected_in_document": True
    },


    # -----------------------------------------------------
    # OUT-OF-DOCUMENT
    # -----------------------------------------------------

    {
        "question": "Định luật Newton thứ hai là gì?",
        "expected_in_document": False
    },

    {
        "question": "Quang hợp là gì?",
        "expected_in_document": False
    },

    {
        "question": "DNA là gì?",
        "expected_in_document": False
    },

    {
        "question": "Thủ đô của Nhật Bản là gì?",
        "expected_in_document": False
    },

    {
        "question": "Blockchain là gì?",
        "expected_in_document": False
    },

    {
        "question": "HTTP hoạt động như thế nào?",
        "expected_in_document": False
    },

    {
        "question": "Cây nhị phân trong cấu trúc dữ liệu là gì?",
        "expected_in_document": False
    },

    {
        "question": "Chiến tranh thế giới thứ hai kết thúc năm nào?",
        "expected_in_document": False
    },

    {
        "question": "Công thức tính diện tích hình tròn là gì?",
        "expected_in_document": False
    },

    {
        "question": "Hệ điều hành quản lý bộ nhớ như thế nào?",
        "expected_in_document": False
    },
]


# =========================================================
# METRICS
# =========================================================

def calculate_metrics(records, threshold):
    """
    Đánh giá khả năng threshold phân biệt:
    - câu trong tài liệu
    - câu ngoài tài liệu
    """

    tp = 0
    tn = 0
    fp = 0
    fn = 0

    for record in records:
        actual = record["expected_in_document"]

        predicted = (
            record["top_score"] >= threshold
        )

        if actual and predicted:
            tp += 1

        elif not actual and not predicted:
            tn += 1

        elif not actual and predicted:
            fp += 1

        elif actual and not predicted:
            fn += 1

    total = tp + tn + fp + fn

    accuracy = (
        (tp + tn) / total
        if total > 0
        else 0
    )

    precision = (
        tp / (tp + fp)
        if (tp + fp) > 0
        else 0
    )

    recall = (
        tp / (tp + fn)
        if (tp + fn) > 0
        else 0
    )

    specificity = (
        tn / (tn + fp)
        if (tn + fp) > 0
        else 0
    )

    f1 = (
        2 * precision * recall
        / (precision + recall)
        if (precision + recall) > 0
        else 0
    )

    balanced_accuracy = (
        recall + specificity
    ) / 2

    return {
        "threshold": threshold,

        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,

        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "f1": f1,

        "balanced_accuracy":
            balanced_accuracy
    }


def find_best_threshold(records):
    """
    Thử threshold nằm giữa các score
    và chọn threshold có Balanced Accuracy tốt nhất.
    """

    scores = sorted(
        set(
            record["top_score"]
            for record in records
        )
    )

    if not scores:
        return None, []

    candidates = []

    # Nhỏ hơn score thấp nhất một chút
    candidates.append(
        max(
            0.0,
            scores[0] - 0.000001
        )
    )

    # Threshold nằm giữa hai score liên tiếp
    for i in range(
        len(scores) - 1
    ):
        threshold = (
            scores[i]
            + scores[i + 1]
        ) / 2

        candidates.append(
            threshold
        )

    # Lớn hơn score cao nhất một chút
    candidates.append(
        min(
            1.0,
            scores[-1] + 0.000001
        )
    )


    evaluations = []

    for threshold in candidates:
        metrics = calculate_metrics(
            records,
            threshold
        )

        evaluations.append(
            metrics
        )


    # Ưu tiên:
    # 1. Balanced Accuracy
    # 2. Specificity
    # 3. Recall
    # 4. F1

    best = max(
        evaluations,
        key=lambda x: (
            x["balanced_accuracy"],
            x["specificity"],
            x["recall"],
            x["f1"]
        )
    )

    return best, evaluations


# =========================================================
# BUILD INDEX
# =========================================================

print("=" * 80)
print("BUILDING RAG INDEX")
print("=" * 80)


pages = read_pdf(
    PDF_PATH
)

print(
    f"Total pages: "
    f"{len(pages)}"
)


chunks = chunk_pages(
    pages,
    chunk_size=CHUNK_SIZE,
    overlap=CHUNK_OVERLAP
)

print(
    f"Total chunks: "
    f"{len(chunks)}"
)


retriever = Retriever()


print(
    "\nCreating embeddings..."
)

embedding_start = (
    time.perf_counter()
)

retriever.index(
    chunks
)

embedding_time = (
    time.perf_counter()
    - embedding_start
)


print(
    f"Embedding completed in "
    f"{embedding_time:.2f} seconds!"
)


generator = Generator()


# =========================================================
# RUN TESTS
# =========================================================

all_results = []


for question_number, item in enumerate(
    QUESTIONS,
    start=1
):

    query = item["question"]

    expected_in_document = (
        item["expected_in_document"]
    )


    print("\n\n")
    print("#" * 80)

    print(
        f"QUESTION "
        f"{question_number}/"
        f"{len(QUESTIONS)}"
    )

    print("#" * 80)


    expected_label = (
        "IN-DOCUMENT"
        if expected_in_document
        else "OUT-OF-DOCUMENT"
    )


    print(
        f"\nExpected: "
        f"{expected_label}"
    )

    print(
        f"Question: "
        f"{query}"
    )


    # =====================================================
    # RETRIEVAL
    # =====================================================

    retrieval_start = (
        time.perf_counter()
    )


    results = retriever.search(
        query,
        top_k=TOP_K
    )


    retrieval_time = (
        time.perf_counter()
        - retrieval_start
    )


    if results:
        top_score = (
            results[0]["score"]
        )
    else:
        top_score = 0.0


    print(
        f"\nTop score: "
        f"{top_score:.4f}"
    )

    print(
        f"Retrieval time: "
        f"{retrieval_time:.4f}s"
    )


    # =====================================================
    # ALWAYS SAVE RETRIEVED SOURCES
    # =====================================================

    retrieved_sources = []


    for i, result in enumerate(
        results,
        start=1
    ):

        source = {
            "rank": i,
            "page":
                result["page"],

            "chunk_id":
                result["chunk_id"],

            "score":
                result["score"],

            "text":
                result["text"]
        }

        retrieved_sources.append(
            source
        )


    # =====================================================
    # CURRENT RELEVANCE GATE
    # =====================================================

    accepted = (
        len(results) > 0
        and
        top_score
        >= CURRENT_GATE_THRESHOLD
    )


    print(
        f"Current threshold: "
        f"{CURRENT_GATE_THRESHOLD:.4f}"
    )


    print(
        "Gate decision:",
        "PASS"
        if accepted
        else "REJECT"
    )


    # =====================================================
    # REJECTED
    # =====================================================

    if not accepted:

        answer = (
            "Không tìm thấy đủ "
            "thông tin trong tài liệu."
        )


        print(
            "\nANSWER:"
        )

        print(
            answer
        )


        print(
            "\nRetrieved candidates "
            "(không gửi cho Gemini):"
        )


        for source in retrieved_sources:

            print(
                f"[{source['rank']}] "
                f"Page {source['page']} "
                f"| Score: "
                f"{source['score']:.4f}"
            )


        all_results.append({

            "question":
                query,

            "expected_in_document":
                expected_in_document,

            "gate_accepted":
                False,

            "top_score":
                top_score,

            "retrieval_time":
                retrieval_time,

            "generation_time":
                0,

            "llm_refused":
                None,

            "answer":
                answer,

            # QUAN TRỌNG:
            # Không còn sources=[] nữa.
            # Ta vẫn lưu retrieval để phân tích.
            "retrieved_sources":
                retrieved_sources
        })


        continue


    # =====================================================
    # SHOW RETRIEVAL RESULTS
    # =====================================================

    print(
        "\nRetrieved context:"
    )


    for source in retrieved_sources:

        print(
            f"\n"
            f"[{source['rank']}] "
            f"Page {source['page']} "
            f"| Score: "
            f"{source['score']:.4f}"
        )

        print(
            source["text"]
        )


    # =====================================================
    # GENERATION
    # =====================================================

    generation_start = (
        time.perf_counter()
    )


    generation_error = None


    try:

        answer = generator.generate(
            query,
            results
        )


    except Exception as error:

        generation_error = (
            f"{type(error).__name__}: "
            f"{error}"
        )

        answer = (
            "[GENERATION ERROR] "
            + generation_error
        )


    generation_time = (
        time.perf_counter()
        - generation_start
    )


    # =====================================================
    # CHECK IF LLM REFUSED
    # =====================================================

    if generation_error:

        llm_refused = None

    else:

        llm_refused = (
            "không tìm thấy đủ thông tin"
            in answer.lower()
        )


    # =====================================================
    # PRINT ANSWER
    # =====================================================

    print(
        "\n"
        + "=" * 80
    )

    print(
        "ANSWER"
    )

    print(
        "=" * 80
    )


    print(
        answer
    )


    print(
        "\n"
        + "=" * 80
    )

    print(
        "SOURCES"
    )

    print(
        "=" * 80
    )


    for source in retrieved_sources:

        print(
            f"[{source['rank']}] "
            f"Page {source['page']} "
            f"| Score: "
            f"{source['score']:.4f}"
        )


    print(
        f"\nGeneration time: "
        f"{generation_time:.2f}s"
    )


    if llm_refused is True:

        print(
            "LLM decision: "
            "REFUSED due to insufficient context"
        )

    elif llm_refused is False:

        print(
            "LLM decision: "
            "ANSWERED"
        )


    # =====================================================
    # SAVE RESULT
    # =====================================================

    all_results.append({

        "question":
            query,

        "expected_in_document":
            expected_in_document,

        "gate_accepted":
            True,

        "top_score":
            top_score,

        "retrieval_time":
            retrieval_time,

        "generation_time":
            generation_time,

        "llm_refused":
            llm_refused,

        "generation_error":
            generation_error,

        "answer":
            answer,

        "retrieved_sources":
            retrieved_sources
    })


    time.sleep(
        API_DELAY_SECONDS
    )


# =========================================================
# THRESHOLD ANALYSIS
# =========================================================

print("\n\n")
print("=" * 80)
print("THRESHOLD ANALYSIS")
print("=" * 80)


best_threshold_result, evaluations = (
    find_best_threshold(
        all_results
    )
)


current_metrics = calculate_metrics(
    all_results,
    CURRENT_GATE_THRESHOLD
)


print(
    "\nCURRENT THRESHOLD"
)

print(
    f"Threshold: "
    f"{CURRENT_GATE_THRESHOLD:.4f}"
)

print(
    f"Accuracy: "
    f"{current_metrics['accuracy']:.4f}"
)

print(
    f"Balanced accuracy: "
    f"{current_metrics['balanced_accuracy']:.4f}"
)

print(
    f"Precision: "
    f"{current_metrics['precision']:.4f}"
)

print(
    f"Recall: "
    f"{current_metrics['recall']:.4f}"
)

print(
    f"Specificity: "
    f"{current_metrics['specificity']:.4f}"
)

print(
    f"F1: "
    f"{current_metrics['f1']:.4f}"
)

print(
    f"TP={current_metrics['tp']} "
    f"TN={current_metrics['tn']} "
    f"FP={current_metrics['fp']} "
    f"FN={current_metrics['fn']}"
)


# =========================================================
# BEST THRESHOLD
# =========================================================

if best_threshold_result:

    recommended_threshold = (
        best_threshold_result[
            "threshold"
        ]
    )


    print(
        "\nRECOMMENDED THRESHOLD "
        "(experimental)"
    )


    print(
        f"Threshold: "
        f"{recommended_threshold:.4f}"
    )

    print(
        f"Accuracy: "
        f"{best_threshold_result['accuracy']:.4f}"
    )

    print(
        f"Balanced accuracy: "
        f"{best_threshold_result['balanced_accuracy']:.4f}"
    )

    print(
        f"Precision: "
        f"{best_threshold_result['precision']:.4f}"
    )

    print(
        f"Recall: "
        f"{best_threshold_result['recall']:.4f}"
    )

    print(
        f"Specificity: "
        f"{best_threshold_result['specificity']:.4f}"
    )

    print(
        f"F1: "
        f"{best_threshold_result['f1']:.4f}"
    )

    print(
        f"TP={best_threshold_result['tp']} "
        f"TN={best_threshold_result['tn']} "
        f"FP={best_threshold_result['fp']} "
        f"FN={best_threshold_result['fn']}"
    )


    # =====================================================
    # SHOW EVERY QUESTION
    # =====================================================

    print(
        "\n"
        + "-" * 80
    )

    print(
        "QUESTION CLASSIFICATION "
        "USING RECOMMENDED THRESHOLD"
    )

    print(
        "-" * 80
    )


    for record in all_results:

        actual = (
            record[
                "expected_in_document"
            ]
        )

        predicted = (
            record["top_score"]
            >= recommended_threshold
        )


        actual_text = (
            "IN "
            if actual
            else "OUT"
        )


        predicted_text = (
            "PASS  "
            if predicted
            else "REJECT"
        )


        correct = (
            actual == predicted
        )


        status = (
            "OK"
            if correct
            else "MISS"
        )


        print(
            f"{status:4} | "
            f"{actual_text:3} | "
            f"{predicted_text:6} | "
            f"{record['top_score']:.4f} | "
            f"{record['question']}"
        )


else:

    recommended_threshold = None


# =========================================================
# SAVE JSON
# =========================================================

output_data = {

    "config": {

        "pdf":
            PDF_PATH,

        "chunk_size":
            CHUNK_SIZE,

        "chunk_overlap":
            CHUNK_OVERLAP,

        "top_k":
            TOP_K,

        "current_gate_threshold":
            CURRENT_GATE_THRESHOLD
    },


    "embedding_time":
        embedding_time,


    "threshold_analysis": {

        "current_threshold_metrics":
            current_metrics,

        "recommended_threshold":
            recommended_threshold,

        "recommended_threshold_metrics":
            best_threshold_result
    },


    "results":
        all_results
}


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        output_data,
        file,
        ensure_ascii=False,
        indent=2
    )


# =========================================================
# FINISHED
# =========================================================

print("\n\n")
print("=" * 80)
print("FINISHED")
print("=" * 80)


print(
    f"Đã lưu kết quả vào: "
    f"{OUTPUT_FILE}"
)


if recommended_threshold is not None:

    print(
        f"Threshold hiện tại: "
        f"{CURRENT_GATE_THRESHOLD:.4f}"
    )

    print(
        f"Threshold đề xuất: "
        f"{recommended_threshold:.4f}"
    )