import sys
from groq import Groq
from engine_core import ResonanceEngine
from dotenv import load_dotenv
load_dotenv()
def extract_intent(client, raw_text):
    """Uses Groq to distill the thesis. Fails fast if offline."""
    try:
        completion = client.chat.completions.create(
            model="groq/compound",
            messages=[
                {
                    "role": "system",
                    "content": "You are a philosophical extractor. Read the following journal entry. Strip away all emotional venting, personal context, and diary formatting. Extract the core philosophical, systemic, or psychological thesis. Output a single, dry sentence. Do not include introductory text."
                },
                {
                    "role": "user",
                    "content": raw_text
                }
            ],
            temperature=0.1,
            timeout=3.0  # If offline, give up after 3 seconds and trigger fallback
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"    -> [Groq Error] {e}")
        # Catches network errors, timeouts, or missing API keys
        return None

def print_results(title, results):
    print(f"\n{'-'*60}")
    print(f" {title}")
    print(f"{'-'*60}")
    for i, (book_title, author, content, distance) in enumerate(results):
        match_strength = max(0, 100 - (distance * 100))
        print(f"\n[Match {i+1} | Strength: ~{match_strength:.1f}%]")
        print(f"Source: {book_title} by {author}")
        print(f"Snippet: \"{content}\"\n")

def run_lens():
    # Initialize the local brain (loads BGE model into RAM)
    engine = ResonanceEngine()
    
    # Initialize the cloud translation layer
    try:
        groq_client = Groq()
    except Exception:
        groq_client = None

    print("\n" + "="*60)
    print(" DUAL-LENS ENGINE ONLINE. PASTE YOUR FREEWRITING.")
    print("="*60 + "\n")

    while True:
        lines = []
        while True:
            try:
                line = input()
            except EOFError:
                break
            if line.strip() == "exit":
                sys.exit(0)
            if line == "":
                break
            lines.append(line)

        user_text = "\n".join(lines).strip()
        if not user_text:
            continue

        print("\n[Processing...]")

        # --- PATH A: GROQ ABSTRACTION ---
        abstracted_text = None
        if groq_client:
            abstracted_text = extract_intent(groq_client, user_text)

        if abstracted_text:
            print(f"    -> Groq Extracted Thesis: \"{abstracted_text}\"")
            print("    -> Querying database for Intent...")
            abstracted_results = engine.search(abstracted_text, is_abstracted=True)
        else:
            print("    -> [Groq Offline/Failed] Network fallback engaged. Skipping abstraction.")
            abstracted_results = None

        # --- PATH B: RAW LOCAL TEXT ---
        print("    -> Querying database for Raw Vibe/Style...")
        raw_results = engine.search(user_text, is_abstracted=False)

        # --- DISPLAY COMPARISON ---
        if abstracted_results:
            print_results("LENS 1: PURE INTENT (Abstracted via Groq)", abstracted_results)
            print_results("LENS 2: VIBE & STYLE (Raw Text)", raw_results)
        else:
            print_results("LENS: VIBE & STYLE (Offline Fallback)", raw_results)

        print("="*60)

if __name__ == "__main__":
    run_lens()