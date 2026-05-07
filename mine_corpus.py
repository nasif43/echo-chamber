import requests
import json
import os
import time

# --- CONFIGURATION ---
TARGET_COUNT = 500
MAX_BYTES = 200000   # ~100 pages (No minimum limit)
MANIFEST_FILE = 'manifest.json'

def get_text_url(formats):
    """Extracts the plain text URL from Gutendex formats."""
    for key, url in formats.items():
        if 'text/plain' in key and '.zip' not in url:
            return url
    return None

def check_file_size(url):
    """Uses a HEAD request to get file size without downloading the whole file."""
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        size = response.headers.get('Content-Length')
        if size:
            return int(size)
    except requests.RequestException:
        return None
    return None

def get_raw_snippet(url):
    """Grabs the first 500 characters of the text to use as a dumb synopsis."""
    try:
        # Fetch just the beginning of the file
        res = requests.get(url, headers={"Range": "bytes=0-1500"}, timeout=10)
        res.raise_for_status()
        text = res.text.replace('\r', ' ').replace('\n', ' ')
        
        # Try to strip away the Gutenberg boilerplate roughly
        if "*** START OF THE PROJECT GUTENBERG" in text:
            text = text.split("***")[2]
            
        # Return a clean 100-character snippet
        clean_text = " ".join(text.split())[:150] + "..."
        return clean_text.strip()
    except Exception:
        return "An open-domain text from Project Gutenberg."

def load_existing_manifest():
    if os.path.exists(MANIFEST_FILE):
        with open(MANIFEST_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_to_manifest(manifest):
    with open(MANIFEST_FILE, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=4, ensure_ascii=False)

def mine_texts():
    manifest = load_existing_manifest()
    collected_ids = {str(item['id']) for item in manifest}
    
    next_url = "https://gutendex.com/books/?languages=en"
    
    print(f"Starting miner. Goal: {TARGET_COUNT} documents (Max 100 pages).")
    print("-" * 50)
    
    while next_url and len(manifest) < TARGET_COUNT:
        # --- ROBUST RETRY LOGIC ---
        max_retries = 3
        data = None
        
        for attempt in range(max_retries):
            try:
                response = requests.get(next_url, timeout=30) # 30s timeout
                response.raise_for_status()
                data = response.json()
                break 
            except Exception as e:
                print(f"  [Network Warning] Failed to fetch Gutendex: {e}")
                if attempt < max_retries - 1:
                    sleep_time = 5 * (attempt + 1)
                    print(f"  Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    print("  [Fatal Error] Max retries reached for Gutendex API. Halting miner.")
                    return 
        
        if not data:
            break 
        # -----------------------------
            
        next_url = data.get('next')
        
        for book in data['results']:
            if len(manifest) >= TARGET_COUNT:
                break
                
            book_id = f"gutenberg-{book['id']}"
            if book_id in collected_ids:
                continue
                
            txt_url = get_text_url(book['formats'])
            if not txt_url:
                continue
                
            file_size = check_file_size(txt_url)
            
            # Unrestricted minimum, strictly bounded maximum
            if file_size and file_size <= MAX_BYTES:
                title = book['title'].replace('\r', '').replace('\n', ' ')
                author = book['authors'][0]['name'] if book['authors'] else "Unknown"
                
                print(f"Match found [{file_size} bytes]: {title} by {author}")
                
                # Grab a raw snippet instead of using an LLM
                snippet = get_raw_snippet(txt_url)
                
                entry = {
                    "id": book_id,
                    "title": title,
                    "author": author,
                    "year": "Unknown",
                    "region": "Global",
                    "source_url": txt_url,
                    "synopsis": snippet
                }
                
                manifest.append(entry)
                collected_ids.add(book_id)
                save_to_manifest(manifest)
                
            time.sleep(1) # Be kind to Gutendex servers

    print(f"\nMining complete! Total documents in manifest: {len(manifest)}")

if __name__ == "__main__":
    mine_texts()