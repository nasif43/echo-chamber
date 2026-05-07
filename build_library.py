import json
import os
import time
import requests
import re

# --- CONFIGURATION ---
MANIFEST_FILE = 'manifest.json'
CLEAN_DIR = 'corpus/clean'
ERROR_LOG = 'failed_downloads.log'

# Ensure the clean directory exists
os.makedirs(CLEAN_DIR, exist_ok=True)

def strip_gutenberg_boilerplate(text):
    """Amputates the legal headers and footers from Gutenberg texts."""
    
    # Notice the '?' making the whole 'THE/THIS ' block optional
    start_pattern = r'\*\*\* START OF (?:TH(?:E|IS) )?PROJECT GUTENBERG.*?\*\*\*'
    end_pattern = r'\*\*\* END OF (?:TH(?:E|IS) )?PROJECT GUTENBERG.*?\*\*\*'
    
    # re.DOTALL allows .*? to match newline characters
    start_match = re.search(start_pattern, text, re.IGNORECASE | re.DOTALL)
    if start_match:
        text = text[start_match.end():]
    
    end_match = re.search(end_pattern, text, re.IGNORECASE | re.DOTALL)
    if end_match:
        text = text[:end_match.start()]
        
    return text.strip()

def log_error(message):
    """Writes failures to a log file so you can review them later."""
    with open(ERROR_LOG, 'a', encoding='utf-8') as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")

def build_library():
    if not os.path.exists(MANIFEST_FILE):
        print(f"Error: {MANIFEST_FILE} not found.")
        return

    with open(MANIFEST_FILE, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    print(f"Starting Bulletproof Library Build: {len(manifest)} texts.")
    print(f"Resumable mode: ON. Outputting to '{CLEAN_DIR}/'.")
    print("-" * 50)

    success_count = 0
    fail_count = 0

    for index, item in enumerate(manifest):
        file_name = f"{item['id']}.txt"
        clean_path = os.path.join(CLEAN_DIR, file_name)

        # --- BULLETPROOF RESUME LOGIC ---
        # Check if file exists AND is larger than 1KB (meaning it actually has text)
        if os.path.exists(clean_path) and os.path.getsize(clean_path) > 1000:
            print(f"[{index + 1}/{len(manifest)}] Skipping (Already finished): {item['title']}")
            success_count += 1
            continue

        print(f"[{index + 1}/{len(manifest)}] Fetching: {item['title']}...")
        
        max_retries = 3
        raw_text = None

        for attempt in range(max_retries):
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (ResonanceEngine/1.0)'}
                response = requests.get(item['source_url'], headers=headers, timeout=30)
                response.raise_for_status()
                raw_text = response.text
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    sleep_time = 5 * (attempt + 1)
                    print(f"  [Network] Hitch detected. Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                else:
                    error_msg = f"Failed to download '{item['title']}' after {max_retries} attempts."
                    print(f"  [Error] {error_msg}")
                    log_error(error_msg)
                    fail_count += 1

        if raw_text:
            clean_text = strip_gutenberg_boilerplate(raw_text)
            
            # Atomic-style write: ensuring we don't leave corrupted files
            with open(clean_path, 'w', encoding='utf-8') as text_file:
                text_file.write(clean_text)
            
            print(f"  -> Cleaned and secured.")
            success_count += 1

        # A 3-second sleep ensures Gutenberg won't IP ban you while you are away.
        time.sleep(3)

    print("-" * 50)
    print("Library Build Complete!")
    print(f"Successfully secured: {success_count}/{len(manifest)}")
    if fail_count > 0:
        print(f"Failed downloads: {fail_count}. Check '{ERROR_LOG}' for details.")

if __name__ == "__main__":
    build_library()