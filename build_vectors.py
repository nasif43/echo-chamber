import os
import json
import sqlite3
import sqlite_vec
import struct
import time
from sentence_transformers import SentenceTransformer

# --- CONFIGURATION ---
MANIFEST_FILE = 'manifest.json'
CLEAN_DIR = 'corpus/clean'
DB_FILE = 'resonance.db'
MODEL_NAME = 'BAAI/bge-small-en-v1.5'
CHUNK_SIZE = 500  # Words per chunk
OVERLAP = 50      # Words to overlap to preserve context

def serialize_vector(vector):
    """Converts a numpy array into raw bytes for SQLite."""
    return struct.pack(f"{len(vector)}f", *vector)

def chunk_text(text, chunk_size, overlap):
    """Slices a text into overlapping windows of words."""
    words = text.split()
    chunks = []
    
    # If the text is shorter than a chunk, just return it
    if len(words) <= chunk_size:
        return [" ".join(words)]
        
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
        if i + chunk_size >= len(words):
            break
            
    return chunks

def build_vectors():
    print(f"Loading Local Model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    
    # Connect to the database
    db = sqlite3.connect(DB_FILE)
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    
    # Load the manifest to get metadata
    with open(MANIFEST_FILE, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    # Find out which books are already in the database
    cursor = db.execute("SELECT DISTINCT essay_id FROM chunks")
    existing_ids = {row[0] for row in cursor.fetchall()}

    print(f"\nStarting Ingestion Pipeline. Found {len(manifest)} texts in manifest.")
    print("-" * 50)

    total_chunks_processed = 0

    for index, item in enumerate(manifest):
        essay_id = item['id']
        file_path = os.path.join(CLEAN_DIR, f"{essay_id}.txt")
        
        # --- RESUME LOGIC ---
        if essay_id in existing_ids:
            print(f"[{index + 1}/{len(manifest)}] Skipping (Already Embedded): {item['title']}")
            continue
            
        if not os.path.exists(file_path):
            print(f"[{index + 1}/{len(manifest)}] Warning: Raw text missing for {item['title']}")
            continue

        print(f"[{index + 1}/{len(manifest)}] Processing: {item['title']}...")
        
        # 1. Read the text
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_text = f.read()
            
        # 2. Chunk the text
        chunks = chunk_text(raw_text, CHUNK_SIZE, OVERLAP)
        print(f"    -> Sliced into {len(chunks)} chunks. Generating math...")
        
        # 3. Batch Embed (This is where the CPU does the heavy lifting)
        start_time = time.time()
        # model.encode() automatically processes a list of strings efficiently
        vectors = model.encode(chunks) 
        duration = time.time() - start_time
        
        print(f"    -> Math generated in {duration:.2f} seconds. Saving to DB...")

        # 4. Insert into Database (Atomic Transaction)
        try:
            db.execute("BEGIN TRANSACTION;")
            for chunk_text_data, vector in zip(chunks, vectors):
                # Insert text
                cur = db.execute(
                    "INSERT INTO chunks (essay_id, title, author, content) VALUES (?, ?, ?, ?)",
                    (essay_id, item['title'], item['author'], chunk_text_data)
                )
                chunk_id = cur.lastrowid
                
                # Insert vector
                db.execute(
                    "INSERT INTO chunk_embeddings (rowid, embedding) VALUES (?, ?)",
                    (chunk_id, serialize_vector(vector))
                )
            db.execute("COMMIT;")
            total_chunks_processed += len(chunks)
            
        except Exception as e:
            db.execute("ROLLBACK;")
            print(f"    -> [Error] Database insertion failed: {e}")

    # Final tally
    cursor = db.execute("SELECT count(*) FROM chunk_embeddings")
    final_count = cursor.fetchone()[0]
    db.close()
    
    print("-" * 50)
    print("Ingestion Complete!")
    print(f"New chunks added this session: {total_chunks_processed}")
    print(f"Total semantic nodes in the Resonance Engine: {final_count}")

if __name__ == "__main__":
    build_vectors()