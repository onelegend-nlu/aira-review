AIRA - FLASHCARD PHASE 1 (BACKEND)
===================================

MUC TIEU
- Them bang flashcards vao PostgreSQL.
- Sinh flashcard bang Gemini tu cac chunk cua PDF ready trong session.
- Luu flashcard vao DB.
- API list va xoa tung flashcard.

FILE CAN THAY THE / THEM MOI
1. api.py                          (thay the full file)
2. src/models.py                  (thay the full file)
3. src/schemas.py                 (thay the full file)
4. src/generator.py               (thay the full file)
5. src/flashcard_service.py       (file moi)

SAU KHI COPY FILE
1. Dam bao Docker Desktop dang chay.
2. O thu muc my-rag-assistant:

   .venv\Scripts\activate
   docker compose up -d
   python init_db.py

   Lenh python init_db.py se tao them bang flashcards bang Base.metadata.create_all().

3. Chay lai backend:

   uvicorn api:app --reload --port 8000

4. Mo:

   http://127.0.0.1:8000/docs

TEST API
A. Tao flashcard
POST /api/v1/sessions/{session_id}/flashcards/generate

Body:
{
  "count": 5,
  "replace_existing": true
}

B. Xem flashcard da luu
GET /api/v1/sessions/{session_id}/flashcards

C. Xoa 1 flashcard
DELETE /api/v1/sessions/{session_id}/flashcards/{flashcard_id}

LUU Y
- Session phai co it nhat 1 PDF status=ready.
- replace_existing=true: moi lan generate se thay bo flashcard cu cua session bang bo moi.
- count cho phep 1..20.
- Flashcard chi duoc tao tu chunk tai lieu, co document_name va source_page de truy vet.
- Chua sua frontend o phase nay. Hay test backend thanh cong truoc.
