# app/main.py
# Description: Main entry point for the FastAPI application.
# Requires: FastAPI, Pydantic, dotenv

import os, io, base64, tempfile, pathlib
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from app.utils.log import log_event
from app.utils.text import tokenize_sentences, bullets
from app.state import state
from app.services.text_gen import generate_story
from app.services.translate import translate_text
from app.services.images import generate_images_b64
from app.services.pdf_export import build_pdf
from app.services.audio import synthesize_tts
from app.services.video import synthesize_video, _deps_ready as _moviepy_ready, missing_deps_list as _moviepy_missing
from app.services.slideshow import build_slideshow_video, _ensure_deps as _slideshow_ready

load_dotenv()

app = FastAPI(title="Smart Cultural Storyteller")

# serve static UI
static_dir = pathlib.Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/", response_class=HTMLResponse)
def root():
    return (static_dir / "index.html").read_text(encoding="utf-8")

# -------- Story --------
class GenReq(BaseModel):
    lang: str
    genre: str
    region: str
    seed: str
    forced_model: str | None = None

@app.post("/api/generate")
def api_generate(req: GenReq):
    if not req.seed or len(req.seed) < 10 or len(req.seed) > 300:
        return JSONResponse({"error": "Seed length invalid (10-300)."}, status_code=400)
    story, backend = generate_story(req.seed.strip(), req.lang, req.genre, req.region, req.forced_model)
    state.story = story
    state.backend_story = backend
    transcript = bullets(tokenize_sentences(story))
    log_event("ui_generate_done", {"backend": backend, "len": len(story)})
    return {"story": story, "transcript": transcript, "backend": backend}

# -------- Translate --------
class TranslateReq(BaseModel):
    target_lang: str
    forced_model: str | None = None
    text: str | None = None

@app.post("/api/translate")
def api_translate(req: TranslateReq):
    base_text = (req.text or state.story or "").strip()
    if not base_text:
        return JSONResponse({"error": "No story to translate."}, status_code=400)
    t, backend = translate_text(base_text, req.target_lang, forced_model=req.forced_model)
    state.translation = t
    state.backend_translate = backend
    log_event("ui_translate_done", {"target": req.target_lang, "len": len(t), "backend": backend})
    return {"translation": t, "backend": backend}

# -------- Images --------
class ImagesReq(BaseModel):
    count: int = 2
    style: str = "none"
    prompt: str

@app.post("/api/images")
def api_images(req: ImagesReq):
    imgs, backend = generate_images_b64(req.prompt, n=req.count, style=req.style)
    state.images_b64 = imgs
    log_event("ui_images_done", {"count": len(imgs), "backend": backend})
    return {"images_b64": imgs, "backend": backend}

# -------- Audio --------
class AudioReq(BaseModel):
    text: str
    accent: str = "Indian"

@app.post("/api/audio")
def api_audio(req: AudioReq):
    txt = (req.text or "").trim()
    if not txt:
        return JSONResponse({"error": "No text to synthesize."}, status_code=400)
    audio_bytes, backend, mime = synthesize_tts(txt, req.accent)
    if not audio_bytes:
        return JSONResponse({"error": "TTS failed."}, status_code=500)
    fname = "lokkatha_audio.mp3" if mime == "audio/mpeg" else "lokkatha_audio.wav"
    headers = {"Content-Disposition": f"attachment; filename={fname}", "X-Backend": f"{backend[0]}|{backend[1]}"}
    return StreamingResponse(io.BytesIO(audio_bytes), media_type=mime, headers=headers)

# -------- Video --------
class VideoReq(BaseModel):
    text: str
    style: str = "slideshow"  # slideshow | shortclip | video
    accent: str = "Indian"

@app.get("/api/video/availability")
def video_availability():
    ok_moviepy, _ = _moviepy_ready()
    ok_slide, _ = _slideshow_ready()
    return {"moviepy_ok": ok_moviepy, "slideshow_ok": ok_slide}

@app.post("/api/video")
def api_video(req: VideoReq):
    txt = (req.text or "").strip()
    if not txt:
        return JSONResponse({"ok": False, "error": "No text to render as video."}, status_code=400)
    style = (req.style or "slideshow").lower().strip()

    if style == "slideshow":
        video_bytes, backend = build_slideshow_video(txt, state.images_b64, accent=req.accent)
        if not video_bytes and backend and backend[0] == "missing-deps":
            return JSONResponse({"ok": False, "error": backend[1], "missing": ["imageio","Pillow","ffmpeg"], "hint": "pip install imageio imageio-ffmpeg Pillow"}, status_code=200)
        if not video_bytes:
            return JSONResponse({"ok": False, "error": "Slideshow generation failed."}, status_code=200)
        headers = {"Content-Disposition": "attachment; filename=lokkatha_slideshow.mp4", "X-Backend": f"{backend[0]}|{backend[1]}"}
        return StreamingResponse(io.BytesIO(video_bytes), media_type="video/mp4", headers=headers)

    elif style == "shortclip":
        # fallback to slideshow at higher fps
        video_bytes, backend = build_slideshow_video(txt, state.images_b64, accent=req.accent, fps=2)
        if not video_bytes:
            return JSONResponse({"ok": False, "error": "Shortclip fallback failed (slideshow)."}, status_code=200)
        headers = {"Content-Disposition": "attachment; filename=lokkatha_shortclip.mp4", "X-Backend": f"{backend[0]}|{backend[1]}|fallback"}
        return StreamingResponse(io.BytesIO(video_bytes), media_type="video/mp4", headers=headers)

    else:  # "video" via MoviePy
        video_bytes, backend = synthesize_video(txt, req.accent)
        if backend and backend[0] == "missing-deps":
            return JSONResponse({"ok": False, "error": backend[1], "missing": _moviepy_missing(), "hint": "pip install moviepy Pillow imageio-ffmpeg numpy"}, status_code=200)
        if not video_bytes:
            return JSONResponse({"ok": False, "error": "Video generation failed."}, status_code=200)
        headers = {"Content-Disposition": "attachment; filename=lokkatha_video.mp4", "X-Backend": f"{backend[0]}|{backend[1]}"}
        return StreamingResponse(io.BytesIO(video_bytes), media_type="video/mp4", headers=headers)

# -------- Download TXT/PDF --------
class TxtReq(BaseModel):
    story: str
    translation: str | None = None

@app.post("/api/download/txt")
def api_txt(req: TxtReq):
    if not (req.story or "").strip():
        return JSONResponse({"error": "No story"}, status_code=400)
    content = req.story + (("\n\n---\nTRANSLATION:\n" + req.translation.strip()) if (req.translation and req.translation.strip()) else "")
    buf = io.BytesIO(content.encode("utf-8"))
    return StreamingResponse(buf, media_type="text/plain; charset=utf-8",
                             headers={"Content-Disposition":"attachment; filename=lokkatha_story.txt"})

class PdfReq(BaseModel):
    story: str
    translation: str | None = None
    images_b64: list[str] | None = None

@app.post("/api/download/pdf")
def api_pdf(req: PdfReq):
    if not (req.story or "").strip():
        return JSONResponse({"error": "No story"}, status_code=400)
    tmpdir = tempfile.mkdtemp(prefix="lokkatha_pdf_")
    img_paths = []
    for i, b64url in enumerate(req.images_b64 or []):
        try:
            if not b64url.startswith("data:image"): continue
            header, data = b64url.split(",", 1)
            raw = base64.b64decode(data)
            p = os.path.join(tmpdir, f"img_{i:02d}.png")
            with open(p, "wb") as f: f.write(raw)
            img_paths.append(p)
        except Exception:
            pass
    out_path = os.path.join(tmpdir, "lokkatha_story.pdf")
    build_pdf(req.story, req.translation, img_paths, out_path)
    return FileResponse(out_path, media_type="application/pdf", filename="lokkatha_story.pdf")

# -------- Misc --------
@app.post("/api/reset")
def api_reset():
    state.story = ""
    state.translation = ""
    state.images_b64 = []
    state.backend_story = ("","")
    state.backend_translate = ("","")
    log_event("ui_reset_done")
    return {"ok": True}

@app.get("/health")
def health():
    return {"ok": True}

