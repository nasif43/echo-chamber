# Resonance Engine - Production Deployment

This is the production-ready version of the Resonance Engine, configured for deployment on Render (or other platforms).

## Overview
The Resonance Engine finds semantic connections between user text and a corpus of classic literature using vector embeddings and semantic search.

## Deployment on Render

### Prerequisites
1. Push this repository to GitHub
2. Have a Groq API key (get from https://console.groq.com/)

### Deployment Steps
1. Create a new Web Service on Render
2. Connect to your GitHub repository
3. Render will automatically detect:
   - `render.yaml` (or `Procfile`)
   - `requirements.txt`
   - `runtime.txt`
4. Add environment variable in Render dashboard:
   - **Key**: `GROQ_API_KEY`
   - **Value**: [your Groq API key]
   - **Keep secret**: Checked
5. Click "Create Web Service"

### Files Used
- `requirements.txt` - Python dependencies
- `runtime.txt` - Python version (3.11.0)
- `render.yaml` - Render service configuration
- `Procfile` - Alternative deployment config
- `app.py` - Main Flask application (production ready)
- `engine_core.py` - Search engine (thread-safe)
- `manifest.json` - Book metadata
- `resonance.db` - Vector database (28MB)

### Local Development
To run locally for development:
```bash
python run_dev.py
```
Or:
```bash
pip install -r requirements.txt
python app.py  # Uses debug mode
```

## Architecture Notes
- **Thread Safety**: The `ResonanceEngine` class uses a threading lock around the sentence transformer model encoding to ensure safe concurrent access in production.
- **Data Flow**: 
  - User text → (optional) Groq intent extraction → Vector search → Results
  - Results link to Project Gutenberg for full book access
- **No Local Corpus Storage**: The application does not require or store local text corpora files. All book references link directly to Project Gutenberg for legal access to full texts.

## Security
- Never commit `.env` file - contains API keys
- The `.gitignore` file excludes sensitive files
- Groq API key is stored as an environment variable on Render