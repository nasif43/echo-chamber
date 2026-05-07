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
        
        # Determine the Read Link
        book_info = manifest_data.get(essay_id, {})
        read_link = book_info.get('url', f"/read/{essay_id}") 
        
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
@app.route('/read/<essay_id>')
def read_book(essay_id):
    # Sanitize the input to prevent directory traversal
    safe_id = os.path.basename(essay_id)
    
    # Check for the file (handling whether essay_id includes .txt or not)
    filepath = os.path.join('corpus', 'clean', f"{safe_id}.txt")
    if not os.path.exists(filepath):
        filepath = os.path.join('corpus', 'clean', safe_id)
        if not os.path.exists(filepath):
            return "Book not found in corpus.", 404
            
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Serve it in a clean, dark-mode reading view that matches your UI
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Reading: {safe_id}</title>
        <style>
            body {{
                background-color: #0f172a;
                color: #e2e8f0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                line-height: 1.8;
                padding: 40px 20px;
                margin: 0;
            }}
            .reader-container {{
                max-width: 800px;
                margin: 0 auto;
                background: #1e293b;
                padding: 40px 60px;
                border-radius: 16px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }}
            .back-btn {{
                color: #38bdf8;
                text-decoration: none;
                font-weight: bold;
                display: inline-block;
                margin-bottom: 30px;
            }}
            .back-btn:hover {{ text-decoration: underline; }}
            pre {{
                white-space: pre-wrap;
                font-family: inherit;
                font-size: 16px;
            }}
        </style>
    </head>
    <body>
        <div class="reader-container">
            <a href="/" class="back-btn">&larr; Back to Resonance Engine</a>
            <pre>{content}</pre>
        </div>
    </body>
    </html>
    """
    return html
if __name__ == '__main__':
    app.run(debug=True, port=5000)