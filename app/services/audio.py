
import io, os, tempfile
from typing import Tuple
from dotenv import load_dotenv
from app.utils.log import log_event
try:
    from gtts import gTTS
    _has_gtts = True
except Exception:
    _has_gtts = False
try:
    import pyttsx3
    _has_pyttsx3 = True
except Exception:
    _has_pyttsx3 = False
load_dotenv()
TTS_PROVIDER = (os.getenv("TTS_PROVIDER") or "gtts").strip().lower()
OFFLINE_TTS_RATE = int(os.getenv("OFFLINE_TTS_RATE") or 180)
OFFLINE_TTS_VOICE_HINT = (os.getenv("OFFLINE_TTS_VOICE_HINT") or "auto").strip().lower()
_GTTs_ACCENT_MAP = { "Indian": {"lang": "en", "tld": "co.in"}, "British": {"lang": "en", "tld": "co.uk"} }
def _pick_pyttsx3_voice(engine, accent: str) -> str | None:
    voices = engine.getProperty("voices") or []
    hint = OFFLINE_TTS_VOICE_HINT
    want_indian = (accent.lower() == "indian")
    want_brit = (accent.lower() == "british")
    def _score(v):
        sid = f"{getattr(v,'id','')} {getattr(v,'name','')}".lower()
        sc=0
        if hint and hint!="auto" and hint in sid: sc+=100
        if want_indian and any(k in sid for k in ["en-in","hindi","india","indian"]): sc+=50
        if want_brit and any(k in sid for k in ["en-gb","british","uk"]): sc+=50
        if "en" in sid: sc+=10
        return sc
    if not voices: return None
    voices_sorted = sorted(voices, key=_score, reverse=True)
    return getattr(voices_sorted[0], "id", None)
def _speak_with_pyttsx3(text: str, accent: str):
    if not _has_pyttsx3: log_event("tts_offline_unavailable"); return b"", ("fallback","none"), "audio/wav"
    engine = pyttsx3.init()
    try:
        voice_id = _pick_pyttsx3_voice(engine, accent)
        if voice_id: engine.setProperty("voice", voice_id)
        engine.setProperty("rate", OFFLINE_TTS_RATE)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            engine.save_to_file(text, tmp.name); engine.runAndWait(); audio = tmp.read()
        model_id = f"pyttsx3|voice={voice_id or 'default'}|rate={OFFLINE_TTS_RATE}"
        log_event("tts_offline_ok", {"bytes": len(audio), "accent": accent, "model": model_id})
        return audio, ("pyttsx3", model_id), "audio/wav"
    except Exception as e:
        log_event("tts_offline_err", {"err": str(e)}); return b"", ("fallback","none"), "audio/wav"
    finally:
        try: engine.stop()
        except Exception: pass
def _speak_with_gtts(text: str, accent: str):
    if not _has_gtts: log_event("tts_online_unavailable"); return b"", ("fallback","none"), "audio/mpeg"
    cfg = _GTTs_ACCENT_MAP.get(accent, _GTTs_ACCENT_MAP["Indian"])
    try:
        tts = gTTS(text=text, lang=cfg["lang"], tld=cfg["tld"])
        buf = io.BytesIO(); tts.write_to_fp(buf); payload = buf.getvalue()
        model_id = f"gTTS|lang={cfg['lang']}|tld={cfg['tld']}"
        log_event("tts_online_ok", {"bytes": len(payload), "accent": accent, "model": model_id})
        return payload, ("gTTS", model_id), "audio/mpeg"
    except Exception as e:
        log_event("tts_online_err", {"err": str(e), "accent": accent}); return b"", ("fallback","none"), "audio/mpeg"
def synthesize_tts(text: str, accent: str):
    text = (text or "").strip()
    if not text: return b"", ("fallback","none"), "audio/mpeg"
    if TTS_PROVIDER == "offline": return _speak_with_pyttsx3(text, accent)
    audio, backend, mime = _speak_with_gtts(text, accent)
    if audio: return audio, backend, mime
    return _speak_with_pyttsx3(text, accent)
