import sqlite3
import sqlite_vec
import struct
from sentence_transformers import SentenceTransformer

# --- CONFIGURATION ---
DB_FILE = 'resonance.db'
MODEL_NAME = 'BAAI/bge-small-en-v1.5'

def serialize_vector(vector):
    """Converts a numpy array into raw bytes for SQLite."""
    return struct.pack(f"{len(vector)}f", *vector)

def query_engine():
    print(f"Waking up the Resonance Engine ({MODEL_NAME})...")
    model = SentenceTransformer(MODEL_NAME)
    
    # Connect to the database
    db = sqlite3.connect(DB_FILE)
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)

    print("\n" + "="*50)
    print(" ENGINE ONLINE. PASTE YOUR FREEWRITING BELOW.")
    print(" (Press Enter twice to submit, or type 'exit' to quit)")
    print("="*50 + "\n")

    while True:
        # Collect multi-line input
        lines = []
        while True:
            line = input()
            if line.strip() == "exit":
                db.close()
                return
            if line == "":
                break
            lines.append(line)
            
        user_text = "\n".join(lines).strip()
        if not user_text:
            continue

        print("\n[Translating thought into geometry...]")
        
        # 1. Embed the user's text
        query_vector = model.encode(user_text)
        
        # print("\n[Applying Semantic Steering and translating into geometry...]")
        # # --- THE GHOST PROMPT ---
        # # This invisible text acts as a mathematical gravity well, 
        # # dragging your raw freewriting into the realm of pure intent and systems logic.
        # ghost_prompt = "The underlying philosophical thesis, abstract intent, and psychological framework regarding the following thought: "
        # steered_text = f"{ghost_prompt} {user_text}"
        # # 1. Embed the STEERED text, overriding the pure writing style
        # query_vector = model.encode(steered_text)
        query_bytes = serialize_vector(query_vector)

        # 2. Perform the Vector Search 
        # We ask for the top 15 closest matches to give us room to filter
        cursor = db.execute("""
            SELECT 
                chunks.essay_id,
                chunks.title, 
                chunks.author, 
                chunks.content,
                chunk_embeddings.distance
            FROM chunk_embeddings
            JOIN chunks ON chunks.id = chunk_embeddings.rowid
            WHERE chunk_embeddings.embedding MATCH ? AND k = 15
            ORDER BY chunk_embeddings.distance
        """, (query_bytes,))

        results = cursor.fetchall()

        # 3. The Diversity Filter
        unique_matches = []
        seen_books = set()
        
        for essay_id, title, author, content, distance in results:
            if essay_id not in seen_books:
                unique_matches.append((title, author, content, distance))
                seen_books.add(essay_id) # Mark this book as "seen"
            
            # Stop once we have 3 completely distinct sources
            if len(unique_matches) == 3:
                break

        # 4. Display the Output
        print("\n" + "~"*50)
        print(" RESONANCE DETECTED (DIVERSIFIED):")
        print("~"*50)
        
        for i, (title, author, content, distance) in enumerate(unique_matches):
            match_strength = max(0, 100 - (distance * 100)) 
            
            print(f"\n[Match {i+1} | Strength: ~{match_strength:.1f}%]")
            print(f"Source: {title} by {author}")
            print(f"Snippet: \"{content}\"\n")
            
        print("="*50)
        print("Paste your next thought (or 'exit'):")

if __name__ == "__main__":
    query_engine()