import sqlite3
import sqlite_vec
import struct
from sentence_transformers import SentenceTransformer

# --- CONFIGURATION ---
DB_FILE = "resonance.db"
MODEL_NAME = "BAAI/bge-small-en-v1.5"
DIMENSIONS = 384 # BGE-small uses 384 dimensions

def serialize_vector(vector):
    """Converts a numpy array of floats into raw bytes for SQLite."""
    return struct.pack(f"{len(vector)}f", *vector)

def init_db():
    print(f"Loading local embedding model ({MODEL_NAME})...")
    # This downloads the model the first time, then loads locally forever after
    model = SentenceTransformer(MODEL_NAME)

    print("Initializing SQLite Vector Database...")
    db = sqlite3.connect(DB_FILE)
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)

    # 1. Create the standard table for our text and metadata
    db.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            essay_id TEXT,
            title TEXT,
            author TEXT,
            content TEXT
        )
    """)

    # 2. Create the virtual table for our 384-dimensional math
    # We use sqlite-vec's syntax to define a float vector of size 384
    db.execute(f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS chunk_embeddings USING vec0(
            embedding float[{DIMENSIONS}]
        )
    """)

    db.commit()
    print(f"Database created successfully at {DB_FILE}!")

    # --- THE TEST RUN ---
    test_text = "The universe is change; our life is what our thoughts make it."
    print("\nGenerating mathematical vector for test text...")
    
    # Generate the 384-dimensional array
    vector = model.encode(test_text)
    vector_bytes = serialize_vector(vector)

    # Insert the text into the standard table
    cursor = db.execute(
        "INSERT INTO chunks (essay_id, title, author, content) VALUES (?, ?, ?, ?)",
        ("test-01", "Meditations", "Marcus Aurelius", test_text)
    )
    chunk_id = cursor.lastrowid

    # Insert the vector into the math table, linking it by ID
    db.execute(
        "INSERT INTO chunk_embeddings (rowid, embedding) VALUES (?, ?)",
        (chunk_id, vector_bytes)
    )

    db.commit()
    print("Test text and vector successfully injected into the database.")
    
    # Prove that the vector was saved by reading it back
    count = db.execute("SELECT count(*) FROM chunk_embeddings").fetchone()[0]
    print(f"Total vectors currently stored: {count}")

    db.close()

if __name__ == "__main__":
    init_db()