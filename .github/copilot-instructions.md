# Copilot Instructions for LokKatha.ai

## Project Overview

## Key Architectural Patterns

## Developer Workflows
  - Use `start.sh` (Linux/macOS) or run `uvicorn app.main:app --reload` (Windows) from the project root.
  - App runs at `http://localhost:8000`.
  - Install with `pip install -r requirements.txt`.
  - TTS and image/video features require ffmpeg and system voices (see README for details).
  - No formal test suite; validate by running the app and using the UI.
  - Check `storyteller_log.txt` for runtime logs.
  - Use `app/utils/log.py` for debug output.

## Project-Specific Conventions

## Integration Points

## Architecture Diagram (mermaid.js)

```mermaid
flowchart TD
  A[Frontend (HTML/JS/CSS)\napp/static/] -->|HTTP| B(FastAPI Server\napp/main.py)
  B -->|API Calls| C[Services Layer\napp/services/]
  C -->|Uses| D[State/Config\napp/state.py]
  C -->|Uses| E[Utilities\napp/utils/]
  C -->|Integrates| F[External APIs\n(OpenRouter, Gemini, Hugging Face, gTTS, pyttsx3, MoviePy, ffmpeg)]
  C -->|PDF Fonts| G[Fonts\n/fonts]
  B -->|Serves| A
```
## Examples
- To add a new translation language, extend `app/services/translate.py` and update UI prompts in `app/static/app.js`.
---
