# app/services/text_gen.py
# Description: This module handles text generation using various APIs.
# Requires: requests

import os, requests
from typing import Tuple
from dotenv import load_dotenv
from app.utils.log import log_event
from app.utils.text import system_directive
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_PREFS_OPENROUTER = [m.strip() for m in (os.getenv("MODEL_PREFS_OPENROUTER") or
                    "openrouter/auto,anthropic/claude-3.7-sonnet,google/gemini-2.0-flash-thinking-exp,openai/gpt-4o-mini").split(",")]
MODEL_NAME_GEMINI = os.getenv("MODEL_NAME_GEMINI", "gemini-1.5-flash")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
try:
    import google.generativeai as genai
    if GOOGLE_API_KEY:
        genai.configure(api_key=GOOGLE_API_KEY)
        _gemini_model = genai.GenerativeModel(MODEL_NAME_GEMINI)
    else:
        _gemini_model = None
except Exception:
    _gemini_model = None
def generate_story(seed: str, lang="English", genre="Folk Tale", region="All-India",
                   forced_model: str | None = None) -> Tuple[str, tuple[str, str]]:
    system = system_directive(genre, region, lang)
    user   = f"USER SEED:\n{seed}\n\nTASK:\nGenerate one story per system rules."
    if OPENROUTER_API_KEY:
        trial = [forced_model] if forced_model else MODEL_PREFS_OPENROUTER[:]
        for mdl in trial:
            try:
                r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}",
                             "Content-Type": "application/json",
                             "HTTP-Referer": "http://localhost", "X-Title": "LokKatha.ai"},
                    json={"model": mdl, "messages": [{"role":"system","content":system},{"role":"user","content":user}], "temperature":0.8,"top_p":0.9},
                    timeout=60)
                if r.status_code == 200:
                    txt = r.json()["choices"][0]["message"]["content"].strip()
                    if txt: log_event("openrouter_ok", {"model": mdl, "chars": len(txt)}); return txt, ("openrouter", mdl)
                else:
                    if r.status_code in (401,402,403,429): log_event("openrouter_skip", {"model": mdl, "code": r.status_code}); continue
                    log_event("openrouter_http", {"model": mdl, "code": r.status_code})
            except Exception as e: log_event("openrouter_exc", {"model": mdl, "err": str(e)})
    try:
        if _gemini_model:
            resp = _gemini_model.generate_content(system + "\n\n" + user, generation_config={"temperature":0.8,"top_p":0.9,"max_output_tokens":512})
            txt = getattr(resp, "text", None)
            if not txt:
                try: txt = resp.candidates[0].content.parts[0].text
                except Exception: txt = None
            if txt: txt = txt.strip(); log_event("gemini_ok", {"chars": len(txt)}); return txt, ("gemini", MODEL_NAME_GEMINI)
    except Exception as e: log_event("gemini_exc", {"err": str(e)})
    return "Story generation failed. Tip: set GOOGLE_API_KEY for Gemini fallback or fix OpenRouter billing/key.", ("fallback", "none")
