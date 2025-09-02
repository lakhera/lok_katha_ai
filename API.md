# API Endpoints for LokKatha.ai

This document summarizes the main FastAPI endpoints exposed by the backend (`app/main.py`).

## Story Generation
- **POST `/api/generate`**
  - Input: `{ lang, genre, region, seed, forced_model? }`
  - Output: `{ story, transcript, backend }`
  - Calls: `generate_story()` in `text_gen.py`

## Translation
- **POST `/api/translate`**
  - Input: `{ target_lang, forced_model?, text? }`
  - Output: `{ translation, backend }`
  - Calls: `translate_text()` in `translate.py`

## Image Generation
- **POST `/api/images`**
  - Input: `{ count, style, prompt }`
  - Output: `{ images_b64, backend }`
  - Calls: `generate_images_b64()` in `images.py`

## Audio Synthesis (TTS)
- **POST `/api/audio`**
  - Input: `{ text, accent }`
  - Output: Audio stream (mp3/wav)
  - Calls: `synthesize_tts()` in `audio.py`

## Video Generation
- **GET `/api/video/availability`**
  - Output: `{ moviepy_ok, slideshow_ok }`
- **POST `/api/video`**
  - Input: `{ text, style, accent }`
  - Output: Video stream (mp4)
  - Calls: `build_slideshow_video()` or `synthesize_video()`

## Download
- **POST `/api/download/txt`**
  - Input: `{ story, translation? }`
  - Output: TXT file
- **POST `/api/download/pdf`**
  - Input: `{ story, translation?, images_b64? }`
  - Output: PDF file
  - Calls: `build_pdf()` in `pdf_export.py`

## Misc
- **POST `/api/reset`**
  - Resets backend state
- **GET `/health`**
  - Health check

---
For details on request/response formats, see Pydantic models in `app/main.py`.
