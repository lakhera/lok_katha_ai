# app/services/translate.py
# Description: This module handles text translation using various APIs.
# Requires: requests

# import libraries
import os, requests
from dotenv import load_dotenv
from app.utils.log import log_event

load_dotenv()

# environment variables and configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GOOGLE_API_KEY     = os.getenv("GOOGLE_API_KEY")
MODEL_PREFS_OPENROUTER = [m.strip() for m in (os.getenv("MODEL_PREFS_OPENROUTER") or "").split(",") if m.strip()]
MODEL_NAME_GEMINI  = os.getenv("MODEL_NAME_GEMINI", "gemini-1.5-flash")

try:
    import google.generativeai as genai
    if GOOGLE_API_KEY:
        genai.configure(api_key=GOOGLE_API_KEY)
        _gemini_model = genai.GenerativeModel(MODEL_NAME_GEMINI)
    else:
        _gemini_model = None
except Exception:
    _gemini_model = None

# translation function
def translate_text(text: str, target_lang: str, forced_model: str | None = None) -> tuple[str, tuple[str, str]]:
    if not (text or "").strip(): return "", ("fallback","none")
    prompt = f"Translate into {target_lang} for Indian middle-school readers (simple, respectful). Output only the translation.\n\n{text}"
    if OPENROUTER_API_KEY and MODEL_PREFS_OPENROUTER:
        trial = [forced_model] if forced_model else MODEL_PREFS_OPENROUTER[:]
        for mdl in trial:
            try:
                r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}","Content-Type":"application/json","HTTP-Referer":"http://localhost","X-Title":"LokKatha.ai"},
                    json={"model": mdl, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3}, timeout=60)
                if r.status_code == 200:
                    txt = r.json()["choices"][0]["message"]["content"].strip()
                    if txt: log_event("openrouter_translate_ok", {"model": mdl, "chars": len(txt)}); return txt, ("openrouter", mdl)
                else:
                    if r.status_code in (401,402,403,429): log_event("openrouter_translate_skip", {"model": mdl, "code": r.status_code}); continue
                    log_event("openrouter_translate_http", {"model": mdl, "code": r.status_code})
            except Exception as e: log_event("openrouter_translate_exc", {"model": mdl, "err": str(e)})
    try:
        if _gemini_model:
            resp = _gemini_model.generate_content(prompt, generation_config={"temperature":0.3,"max_output_tokens":512})
            txt = getattr(resp, "text", None)
            if not txt:
                try: txt = resp.candidates[0].content.parts[0].text
                except Exception: txt = None
            if txt: txt = txt.strip(); log_event("gemini_translate_ok", {"chars": len(txt)}); return txt, ("gemini", MODEL_NAME_GEMINI)
    except Exception as e: log_event("gemini_translate_exc", {"err": str(e)})
    return "Translation not available.", ("fallback","none")