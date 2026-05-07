import sqlite3
import sqlite_vec
import struct
from sentence_transformers import SentenceTransformer

class ResonanceEngine:
    def __init__(self, db_file='resonance.db', model_name='BAAI/bge-small-en-v1.5'):
        self.db_file = db_file
        self.model_name = model_name
        print(f"[Core] Waking up the local model ({self.model_name})...")
        # Loads into RAM once upon initialization
        self.model = SentenceTransformer(self.model_name)

    def _serialize_vector(self, vector):
        return struct.pack(f"{len(vector)}f", *vector)

    def search(self, text, is_abstracted=False, top_k=3, search_k=15):
        """Generates vectors and queries the SQLite database."""
        # If it's the distilled Groq text, we apply the BGE instruction prefix
        if is_abstracted:
            query_text = f"Represent this sentence for searching relevant passages: {text}"
        else:
            query_text = text

        query_vector = self.model.encode(query_text)
        query_bytes = self._serialize_vector(query_vector)

        db = sqlite3.connect(self.db_file)
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)

        cursor = db.execute("""
            SELECT chunks.essay_id, chunks.title, chunks.author, chunks.content, chunk_embeddings.distance
            FROM chunk_embeddings
            JOIN chunks ON chunks.id = chunk_embeddings.rowid
            WHERE chunk_embeddings.embedding MATCH ? AND k = ?
            ORDER BY chunk_embeddings.distance
        """, (query_bytes, search_k))

        results = cursor.fetchall()
        db.close()

        # The Diversity Filter
        unique_matches = []
        seen_books = set()
        for essay_id, title, author, content, distance in results:
            if essay_id not in seen_books:
                unique_matches.append((essay_id,title, author, content, distance))
                seen_books.add(essay_id)
            if len(unique_matches) == top_k:
                break

        return unique_matches