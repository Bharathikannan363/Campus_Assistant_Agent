"""RAG foundations with explicit college-filtered chunk metadata."""
from datetime import datetime, timezone
from database import get_connection

def chunk_text(text, size=800, overlap=100):
    words = text.split()
    return [" ".join(words[i:i + size]) for i in range(0, len(words), max(1, size - overlap))]

def index_page(college_id, college_name, source_url, page_type, title, content):
    db = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    chunks = chunk_text(content)
    for i, chunk in enumerate(chunks):
        db.execute("INSERT INTO rag_chunks (college_id,college_name,source_url,page_type,title,content,chunk_index,scraped_at) VALUES (?,?,?,?,?,?,?,?)",
                   (college_id, college_name, source_url, page_type, title, chunk, i, now))
    db.commit(); db.close()
    return len(chunks)

def retrieve(query, college_id, limit=5):
    terms = [x for x in query.lower().split() if len(x) > 2]
    db = get_connection()
    rows = db.execute("SELECT * FROM rag_chunks WHERE college_id=? ORDER BY scraped_at DESC LIMIT ?",
                      (college_id, limit * 5)).fetchall()
    db.close()
    ranked = sorted((dict(r) for r in rows), key=lambda r: sum(t in r["content"].lower() for t in terms), reverse=True)
    return ranked[:limit]
