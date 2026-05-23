# echo-chamber

You paste something you wrote — a journal entry, a paragraph, a thought — and echo-chamber finds the books that resonate with it. Not by keyword, by meaning and writing style.

The corpus is books under 150 pages from Project Gutenberg. The matching is done with vector embeddings and semantic search, with an optional Groq pass to extract intent before searching.

## How it works

**Building the corpus:** `mine_corpus.py` scrapes Project Gutenberg for short books (under 150 pages), cleans and chunks the text. `build_vectors.py` embeds each chunk using a sentence transformer model and stores the vectors in SQLite via sqlite-vec. The resulting `resonance.db` ships with the repo (28MB).

**Search pipeline:**
1. User submits text via the Flask web interface
2. Optionally, Groq extracts the underlying intent — what the text is *about* beyond its surface meaning
3. The text (or extracted intent) is embedded and compared against the corpus vectors
4. The closest matches are returned with links to the full text on Project Gutenberg

**Thread safety:** The `ResonanceEngine` class uses a threading lock around the sentence transformer encoding, so concurrent requests in production don't corrupt the model state.

## Tech stack

| | |
|---|---|
| Embeddings | sentence-transformers |
| Vector search | sqlite-vec |
| Intent extraction | Groq |
| Web framework | Flask |
| Corpus source | Project Gutenberg |
| Deployment | Render |

## Run locally

```bash
pip install -r requirements.txt
python run_dev.py
```

Or directly:
```bash
python app.py
```

Add a `.env` file with:
```
GROQ_API_KEY=your_groq_api_key
```

Groq is used for intent extraction — if the key is missing, the search falls back to direct embedding of the input text.

## Deploy to Render

The repo includes `render.yaml` and `Procfile`. Connect the repo to a Render Web Service, add `GROQ_API_KEY` as an environment variable, and deploy. Render detects the config automatically.

`resonance.db` is committed to the repo so no build step is needed for the corpus — it's ready on first deploy.

## Notes

The corpus intentionally excludes books over 150 pages. Shorter works tend to have more concentrated style and voice, which makes the matching more interesting — a paragraph you wrote is more likely to resonate with a focused essay or short story than a sprawling novel.

No full book text is stored locally. Search results link directly to Project Gutenberg.
