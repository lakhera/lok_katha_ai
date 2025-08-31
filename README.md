# LokKatha.ai — Full FastAPI App (with TTS toggle)

- Story, Translate, Transcript, Images, **Audio (TTS)** — each with progress bar + model badge
- OpenRouter → Gemini fallback (skips 401/402/403/429)
- HF images (styles)
- Hindi-safe PDF export
- TXT export
- **TTS toggle**: `TTS_PROVIDER=gtts` (online, default) or `offline` (pyttsx3)
- `.gitignore` ignores `.env`

## Run
1. `python -m venv .venv && source .venv/bin/activate`  (Windows: `.venv\Scripts\activate`)
2. `pip install -r requirements.txt`
3. Copy `.env.example` → `.env` and set keys (needed for story/translate/images)
4. `uvicorn app.main:app --reload`
5. Open http://localhost:8000
