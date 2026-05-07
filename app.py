import os
import json
import re
from flask import Flask, render_template, request, jsonify
from groq import Groq
from dotenv import load_dotenv
from engine_core import ResonanceEngine

load_dotenv()

app = Flask(__name__)
engine = ResonanceEngine()

# Initialize Groq (fails gracefully if no key or offline)
try:
    groq_client = Groq()
except Exception:
    groq_client = None

# Load your manifest to map essay_ids to book links
MANIFEST_FILE = 'manifest.json'
manifest_data = {}
if os.path.exists(MANIFEST_FILE):
    with open(MANIFEST_FILE, 'r', encoding='utf-8') as f:
        raw_manifest = json.load(f)
        for item in raw_manifest:
            manifest_data[item['id']] = item

def extract_intent(text):
    if not groq_client: return None
    try:
        completion = groq_client.chat.completions.create(
            # Change this to the exact model string you are using on Groq
            model="groq/compound", 
            messages=[
                {
                    "role": "system", 
                    "content": "You are a surgical intent extractor. Output ONLY the final thesis. Absolutely NO reasoning, NO lists, NO introductory text, and NO markdown formatting. Just a single, dry sentence."
                },
                {"role": "user", "content": text}
            ],
            temperature=0.1,
            timeout=5.0
        )
        
        result = completion.choices[0].message.content.strip()
        
        # The Safety Net: Slice off AI monologue if it disobeys
        if "**Extracted thesis" in result:
            result = result.split("**Extracted thesis")[-1]
        elif "Thesis:" in result:
            result = result.split("Thesis:")[-1]
            
        # Strip away stray markdown asterisks and quotes
        result = result.replace("*", "").replace('"', '').strip()
        
        # Remove any leading dashes or colons left behind
        result = re.sub(r'^[-:\s]+', '', result)
        
        return result
    except Exception as e:
        print(f"[Groq Error]: {e}")
        return None

def format_matches(results):
    """Helper to format the raw database results into UI-friendly dictionaries."""
    formatted = []
    for essay_id, title, author, content, distance in results:
        strength = max(0, 100 - (distance * 100))
        
        # Determine the Read Link - use source_url from manifest
        book_info = manifest_data.get(essay_id, {})
        source_url = book_info.get('source_url', '')
        
        # Convert text file URL to main book page URL for better UX
        # e.g., https://www.gutenberg.org/ebooks/1513.txt.utf-8 -> https://www.gutenberg.org/ebooks/1513
        if source_url:
            # Extract book ID from URL (everything after /ebooks/ that's a number)
            import re
            match = re.search(r'/ebooks/(\d+)', source_url)
            if match:
                book_id = match.group(1)
                read_link = f"https://www.gutenberg.org/ebooks/{book_id}"
            else:
                # Fallback: use the source_url as-is if we can't extract ID
                read_link = source_url
        else:
            read_link = "#"  # No link available
        
        formatted.append({
            "title": title,
            "author": author,
            "content": content,
            "strength": round(strength, 1),
            "link": read_link
        })
    return formatted

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/resonate', methods=['POST'])
def resonate():
    data = request.json
    user_text = data.get('text', '')
    
    if not user_text:
        return jsonify({"error": "No text provided"}), 400

    # 1. Get the Groq abstraction
    abstracted_text = extract_intent(user_text)
    
    # 2. ALWAYS query the raw text (Vibe & Style)
    raw_results = engine.search(user_text, is_abstracted=False, top_k=6)
    formatted_raw = format_matches(raw_results)

    # 3. If Groq succeeds, ALSO query the abstraction (Pure Intent)
    formatted_intent = []
    if abstracted_text:
        intent_results = engine.search(abstracted_text, is_abstracted=True, top_k=6)
        formatted_intent = format_matches(intent_results)

    return jsonify({
        "abstraction": abstracted_text,
        "intent_matches": formatted_intent,
        "raw_matches": formatted_raw
    })

if __name__ == '__main__':
    # Development only - production uses gunicorn
    app.run(debug=True, port=5000)