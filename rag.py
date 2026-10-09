"""Retrieval-Augmented Generation (RAG) chunking, indexing, and grounded retrieval."""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from database import get_connection


def chunk_text(text: str, size: int = 400, overlap: int = 50) -> List[str]:
    """Split text into manageable, overlapping passages for retrieval."""
    if not text:
        return []

    words = text.split()
    if len(words) <= size:
        return [" ".join(words)]

    chunks = []
    step = max(1, size - overlap)
    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i + size])
        if chunk and len(chunk.split()) >= 10:
            chunks.append(chunk)
    return chunks


def index_page(
    college_id: int,
    college_name: str,
    source_url: str,
    page_type: str,
    title: str,
    content: str,
) -> int:
    """Chunk and store document passages into rag_chunks table."""
    if not content or not content.strip():
        return 0

    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    chunks = chunk_text(content)

    for idx, chunk in enumerate(chunks):
        conn.execute(
            """
            INSERT INTO rag_chunks (
                college_id, college_name, source_url, page_type, title, content, chunk_index, scraped_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (college_id, college_name, source_url, page_type, title, chunk, idx, now),
        )

    conn.commit()
    conn.close()
    return len(chunks)


def retrieve(query: str, college_id: Optional[int] = None, limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieve relevant passages grounded with source URLs and titles."""
    terms = [w.lower() for w in re.findall(r"\b\w{3,}\b", query.lower()) if w not in ("what", "where", "show", "tell", "from", "with", "that")]
    if not terms:
        return []

    conn = get_connection()
    where_clause = ""
    args = []

    if college_id is not None:
        where_clause = "WHERE college_id = ?"
        args.append(college_id)

    # Fetch recent candidate chunks
    query_sql = f"SELECT * FROM rag_chunks {where_clause} ORDER BY scraped_at DESC LIMIT 50"
    rows = conn.execute(query_sql, args).fetchall()
    conn.close()

    results = []
    for r in rows:
        content_lower = r["content"].lower()
        score = sum(1 for term in terms if term in content_lower)
        if score > 0:
            results.append({
                "id": r["id"],
                "college_id": r["college_id"],
                "college_name": r["college_name"],
                "source_url": r["source_url"],
                "title": r["title"] or "Official Document",
                "content": r["content"],
                "score": score,
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def format_rag_context(chunks: List[Dict[str, Any]]) -> str:
    """Format retrieved passages into a structured reference prompt."""
    if not chunks:
        return ""

    passages = []
    for i, c in enumerate(chunks, 1):
        passages.append(
            f"[{i}] Source: {c.get('title')} ({c.get('source_url')})\n{c.get('content')}"
        )
    return "\n\n".join(passages)
