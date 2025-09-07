# app/main.py
# Description: Main entry point for the FastAPI application.
# Requires: FastAPI, Pydantic, dotenv

# import libraries
import os, io, base64, tempfile, pathlib
from fastapi import FastAPI, HTTPException
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

# initialize FastAPI app
app = FastAPI(title="Smart Cultural Storyteller", version="1.1.0", docs_url="/api/docs", redoc_url="/api/redoc")

# serve static UI
static_dir = pathlib.Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# root endpoint serves the main HTML page
@app.get("/", response_class=HTMLResponse)
def root():
    return (static_dir / "index.html").read_text(encoding="utf-8")

# class for story generation request
class GenReq(BaseModel):
    lang: str
    genre: str
    region: str
    seed: str
    forced_model: str | None = None

# story generation endpoint
@app.post("/api/generate")
def api_generate(req: GenReq):
    if not req.seed or len(req.seed) < 10 or len(req.seed) > 300:
        raise HTTPException(status_code=400, detail="Seed length invalid (10-300).")
    story, backend = generate_story(req.seed.strip(), req.lang, req.genre, req.region, req.forced_model)
    state.story = story
    state.backend_story = backend
    transcript = bullets(tokenize_sentences(story))
    log_event("ui_generate_done", {"backend": backend, "len": len(story)})
    return {"story": story, "transcript": transcript, "backend": backend}

# class for translation request
class TranslateReq(BaseModel):
    target_lang: str
    forced_model: str | None = None
    text: str | None = None

# translation endpoint
@app.post("/api/translate")
def api_translate(req: TranslateReq):
    base_text = (req.text or state.story or "").strip()
    if not base_text:
        raise HTTPException(status_code=400, detail="No story to translate.")
    t, backend = translate_text(base_text, req.target_lang, forced_model=req.forced_model)
    state.translation = t
    state.backend_translate = backend
    log_event("ui_translate_done", {"target": req.target_lang, "len": len(t), "backend": backend})
    return {"translation": t, "backend": backend}

# class for image generation request
class ImagesReq(BaseModel):
    count: int = 2
    style: str = "none"
    prompt: str

# image generation endpoint
@app.post("/api/images")
def api_images(req: ImagesReq):
    imgs, backend = generate_images_b64(req.prompt, n=req.count, style=req.style)
    state.images_b64 = imgs
    log_event("ui_images_done", {"count": len(imgs), "backend": backend})
    return {"images_b64": imgs, "backend": backend}

# class for audio synthesis request
class AudioReq(BaseModel):
    text: str
    accent: str = "Indian"

# audio synthesis endpoint
@app.post("/api/audio")
def api_audio(req: AudioReq):
    txt = (req.text or "").strip()
    if not txt:
        raise HTTPException(status_code=400, detail="No text to synthesize.")
    audio_bytes, backend, mime = synthesize_tts(txt, req.accent)
    if not audio_bytes:
        raise HTTPException(status_code=500, detail="TTS failed.")
    fname = "lokkatha_audio.mp3" if mime == "audio/mpeg" else "lokkatha_audio.wav"
    headers = {"Content-Disposition": f"attachment; filename={fname}", "X-Backend": f"{backend[0]}|{backend[1]}"}
    return StreamingResponse(io.BytesIO(audio_bytes), media_type=mime, headers=headers)

# class for video synthesis request
class VideoReq(BaseModel):
    text: str
    style: str = "slideshow"  # slideshow | shortclip | video
    accent: str = "Indian"
    fps: int | None = None  # Optional FPS override

# video synthesis endpoint
@app.get("/api/video/availability")
def video_availability():
    ok_moviepy, msg_moviepy = _moviepy_ready()
    ok_slide, msg_slide = _slideshow_ready()
    return {
        "moviepy_ok": ok_moviepy,
        "slideshow_ok": ok_slide,
        "details": {
            "moviepy": msg_moviepy,
            "slideshow": msg_slide
        }
    }

# video synthesis endpoint
@app.post("/api/video")
def api_video(req: VideoReq):
    txt = (req.text or "").strip()
    if not txt:
        raise HTTPException(status_code=400, detail="No text to render as video.")
    
    style = (req.style or "slideshow").lower().strip()

    if style == "slideshow":
        # Let FPS be auto-calculated based on audio duration
        video_bytes, backend = build_slideshow_video(
            txt, 
            state.images_b64, 
            accent=req.accent
        )
        if not video_bytes:
            if backend and backend[0] == "missing-deps":
                return JSONResponse({
                    "ok": False, 
                    "error": backend[1], 
                    "missing": ["imageio","Pillow","ffmpeg"], 
                    "hint": "pip install imageio imageio-ffmpeg Pillow"
                }, status_code=200)
            return JSONResponse({"ok": False, "error": "Slideshow generation failed."}, status_code=200)
            
        headers = {
            "Content-Disposition": "attachment; filename=lokkatha_slideshow.mp4", 
            "X-Backend": f"{backend[0]}|{backend[1]}"
        }
        return StreamingResponse(io.BytesIO(video_bytes), media_type="video/mp4", headers=headers)

    elif style == "shortclip":
        # Higher FPS slideshow
        video_bytes, backend = build_slideshow_video(
            txt, 
            state.images_b64, 
            accent=req.accent,
            fps=2
        )
        if not video_bytes:
            return JSONResponse({"ok": False, "error": "Shortclip generation failed."}, status_code=200)
            
        headers = {
            "Content-Disposition": "attachment; filename=lokkatha_shortclip.mp4",
            "X-Backend": f"{backend[0]}|{backend[1]}|shortclip"
        }
        return StreamingResponse(io.BytesIO(video_bytes), media_type="video/mp4", headers=headers)

    else:  # "video" via MoviePy
        video_bytes, backend = synthesize_video(txt, req.accent)
        if backend and backend[0] == "missing-deps":
            return JSONResponse({
                "ok": False,
                "error": backend[1],
                "missing": _moviepy_missing(),
                "hint": "pip install moviepy Pillow imageio-ffmpeg numpy"
            }, status_code=200)
            
        if not video_bytes:
            return JSONResponse({"ok": False, "error": "Video generation failed."}, status_code=200)
            
        headers = {
            "Content-Disposition": "attachment; filename=lokkatha_video.mp4",
            "X-Backend": f"{backend[0]}|{backend[1]}"
        }
        return StreamingResponse(io.BytesIO(video_bytes), media_type="video/mp4", headers=headers)

# class for TXT download request
class TxtReq(BaseModel):
    story: str
    translation: str | None = None

# TXT download endpoint
@app.post("/api/download/txt")
def api_txt(req: TxtReq):
    if not (req.story or "").strip():
        raise HTTPException(status_code=400, detail="No story")
    content = req.story + (("\n\n---\nTRANSLATION:\n" + req.translation.strip()) if (req.translation and req.translation.strip()) else "")
    buf = io.BytesIO(content.encode("utf-8"))
    return StreamingResponse(
        buf, 
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition":"attachment; filename=lokkatha_story.txt"}
    )

# class for PDF download request
class PdfReq(BaseModel):
    story: str
    translation: str | None = None
    images_b64: list[str] | None = None

# PDF download endpoint
@app.post("/api/download/pdf")
def api_pdf(req: PdfReq):
    if not (req.story or "").strip():
        raise HTTPException(status_code=400, detail="No story")
        
    tmpdir = tempfile.mkdtemp(prefix="lokkatha_pdf_")
    img_paths = []
    
    for i, b64url in enumerate(req.images_b64 or []):
        try:
            if not b64url.startswith("data:image"):
                continue
            header, data = b64url.split(",", 1)
            raw = base64.b64decode(data)
            p = os.path.join(tmpdir, f"img_{i:02d}.png")
            with open(p, "wb") as f:
                f.write(raw)
            img_paths.append(p)
        except Exception as e:
            log_event("pdf_img_decode_err", {"i": i, "err": str(e)})
            continue
            
    out_path = os.path.join(tmpdir, "lokkatha_story.pdf")
    build_pdf(req.story, req.translation, img_paths, out_path)
    return FileResponse(out_path, media_type="application/pdf", filename="lokkatha_story.pdf")

# reset endpoint to clear state
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