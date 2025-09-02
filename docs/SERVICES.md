# Service Module Interfaces — LokKatha.ai

This document summarizes the public interfaces of each service module in `app/services/`.

---

## text_gen.py
- `generate_story(seed, lang="English", genre="Folk Tale", region="All-India", forced_model=None) -> (story: str, backend: tuple)`
  - Generates a story using LLM APIs (OpenRouter, Gemini).

## translate.py
- `translate_text(text, target_lang, forced_model=None) -> (translation: str, backend: tuple)`
  - Translates text using LLM APIs (OpenRouter, Gemini).

## images.py
- `generate_images_b64(prompt, n=2, style="none") -> (images_b64: list, backend: tuple)`
  - Generates images via Hugging Face APIs. Returns base64-encoded PNGs.

## audio.py
- `synthesize_tts(text, accent) -> (audio_bytes, backend, mime)`
  - Synthesizes speech using gTTS (online) or pyttsx3 (offline fallback).

## pdf_export.py
- `build_pdf(story, translation, image_paths, out_path="lokkatha_story.pdf") -> str`
  - Exports story and images to PDF, with Hindi font support if needed.

## slideshow.py
- `build_slideshow_video(text, images_b64, accent, fps=1) -> (video_bytes, backend)`
  - Creates a video slideshow from text and images, with TTS audio.

## video.py
- `synthesize_video(text, accent) -> (video_bytes, backend)`
  - Generates a video using MoviePy and TTS audio.

---

- All modules use `log_event` for logging and expect UTF-8 text.
- For details, see docstrings in each module.
