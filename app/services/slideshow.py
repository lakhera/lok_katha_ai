# app/services/slideshow.py
# Description: Generate a video slideshow from images with TTS narration and captions.
# Requires: imageio, imageio-ffmpeg, Pillow, numpy, ffmpeg

"""
Slideshow generation service.
Creates a video slideshow from (pre-generated) images with TTS narration,
and overlays per-frame captions derived from the story text.

Requires: imageio, imageio-ffmpeg, Pillow, numpy, ffmpeg
"""

# import libraries
from __future__ import annotations
import os, base64, tempfile, subprocess, math, io
from typing import Tuple, List
from PIL import Image, ImageDraw, ImageFont, ImageOps
import numpy as np
import imageio.v2 as imageio
import imageio_ffmpeg
from app.utils.log import log_event
from app.services.audio import synthesize_tts
from app.state import state  # holds state.images_b64, etc.

# Check ffmpeg availability
try:
    _FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
    _FFMPEG_OK = bool(_FFMPEG_EXE)
    _FFMPEG_ERR = ""
except Exception as e:
    _FFMPEG_EXE = None
    _FFMPEG_OK = False
    _FFMPEG_ERR = str(e)

# dependency check function
def _ensure_deps() -> tuple[bool, str]:
    if not _FFMPEG_OK:
        return False, f"ffmpeg not available: {_FFMPEG_ERR}"
    return True, "ok"

# helper functions
def _decode_base64_image(b64_str: str) -> Image.Image | None:
    """Decode a data:image/... base64 string to a PIL Image."""
    try:
        if not isinstance(b64_str, str) or not b64_str.startswith("data:image/"):
            return None
        _, data = b64_str.split(",", 1)
        raw = base64.b64decode(data)
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        return img
    except Exception as e:
        log_event("slideshow_decode_err", {"err": str(e)})
        return None

# letterbox function
def _letterbox(img: Image.Image, target_size: tuple[int, int], fill=(16,16,24)) -> Image.Image:
    """Resize with aspect-preserving letterbox to target_size."""
    tw, th = target_size
    iw, ih = img.size
    scale = min(tw / iw, th / ih)
    nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
    resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (tw, th), fill)
    x = (tw - nw) // 2
    y = (th - nh) // 2
    canvas.paste(resized, (x, y))
    return canvas

# sentence splitter
def _split_sentences(text: str) -> list[str]:
    """Simple sentence splitter (periods, ?, !, Devanagari danda)."""
    import re
    text = (text or "").strip()
    if not text:
        return []
    parts = re.split(r'(?<=[.?!।])\s+', text)
    return [p.strip() for p in parts if p.strip()]

# text overlay functions
def _wrap_lines(draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont, text: str, max_width: int) -> list[str]:
    words = (text or "").split()
    lines, cur = [], []
    for w in words:
        test = " ".join(cur + [w])
        if draw.textlength(test, font=font) <= max_width:
            cur.append(w)
        else:
            if cur: lines.append(" ".join(cur))
            cur = [w]
    if cur: lines.append(" ".join(cur))
    return lines or ["(empty)"]

# draw text with stroke for contrast
def _draw_text_with_stroke(draw, xy, text, font, fill=(240,240,245), stroke=2, stroke_fill=(10,10,12)):
    x, y = xy
    # Stroke around text for contrast
    for dx in (-stroke, 0, stroke):
        for dy in (-stroke, 0, stroke):
            if dx == 0 and dy == 0: 
                continue
            draw.text((x+dx, y+dy), text, font=font, fill=stroke_fill)
    draw.text((x, y), text, font=font, fill=fill)

# overlay caption function
def _overlay_caption(img: Image.Image, caption: str, pad: int = 20) -> Image.Image:
    """Overlay wrapped caption near the bottom with stroke; returns a copy."""
    W, H = img.size
    out = img.copy()
    d = ImageDraw.Draw(out)

    # pick a font
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 28)
    except Exception:
        font = ImageFont.load_default()

    max_w = int(W * 0.88)
    lines = _wrap_lines(d, font, caption or "", max_w)
    line_h = int(font.getbbox("Ag")[3] * 1.25) if hasattr(font, "getbbox") else 36
    total_h = line_h * len(lines)

    y = H - total_h - pad
    for line in lines:
        w = d.textlength(line, font=font)
        x = (W - int(w)) // 2
        _draw_text_with_stroke(d, (x, y), line, font)
        y += line_h

    return out

# get audio duration function
def _get_audio_duration(audio_path: str) -> float:
    """Parse duration from ffmpeg stderr. Return seconds."""
    try:
        proc = subprocess.run([_FFMPEG_EXE, "-i", audio_path], capture_output=True, text=True)
        for line in (proc.stderr or "").splitlines():
            if "Duration:" in line:
                t = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = t.split(":")
                return float(h) * 3600 + float(m) * 60 + float(s)
    except Exception as e:
        log_event("duration_check_err", {"err": str(e)})
    return 10.0

# build slideshow video function
def build_slideshow_video(
    text: str,
    images_b64: List[str],
    accent: str = "Indian",
    width: int = 640,
    height: int = 360
) -> Tuple[bytes, tuple[str, str]]:
    """
    Build a slideshow MP4 using (pre-generated) images with a caption per-frame,
    synchronized to the TTS audio duration.

    Returns (video_bytes, (backend_name, model_info))
    """
    ok, msg = _ensure_deps()
    if not ok:
        log_event("slideshow_deps_err", {"msg": msg})
        return b"", ("missing-deps", msg)

    story = (text or "").strip()
    # Build caption list from sentences
    captions = _split_sentences(story) or [story or ""]

    with tempfile.TemporaryDirectory(prefix="slideshow_") as td:
        # 1) TTS first
        audio_bytes, (tts_name, tts_model), mime = synthesize_tts(story, accent)
        if not audio_bytes:
            return b"", ("error", "TTS generation failed")

        aext = "mp3" if mime == "audio/mpeg" else "wav"
        apath = os.path.join(td, f"audio.{aext}")
        with open(apath, "wb") as f:
            f.write(audio_bytes)

        # 2) Collect images: pre-generated first, then new
        all_b64 = []
        if getattr(state, "images_b64", None):
            all_b64.extend([b for b in state.images_b64 if isinstance(b, str)])
        if images_b64:
            all_b64.extend([b for b in images_b64 if isinstance(b, str)])

        # Decode & letterbox
        frames_raw: list[Image.Image] = []
        for b64 in all_b64:
            img = _decode_base64_image(b64)
            if not img:
                continue
            frames_raw.append(_letterbox(img, (width, height)))
        if not frames_raw:
            # Fallback: single text frame
            bg = Image.new("RGB", (width, height), (16,16,24))
            frames_raw = [bg]

        # 3) Assign captions to frames (1 caption per frame; if fewer captions than frames reuse last)
        frames_with_text: list[Image.Image] = []
        for i, base in enumerate(frames_raw):
            cap = captions[i] if i < len(captions) else captions[-1]
            frames_with_text.append(_overlay_caption(base, cap))

        # 4) Compute duration + frame repetition at 24fps
        duration = max(3.0, _get_audio_duration(apath))  # minimum 3s
        fps = 24
        n_unique = max(1, len(frames_with_text))
        seconds_per_frame = duration / float(n_unique)
        frames_per_image = max(1, int(round(seconds_per_frame * fps)))

        # 5) Write silent video
        vpath = os.path.join(td, "silent.mp4")
        try:
            writer = imageio.get_writer(
                vpath,
                format="ffmpeg",
                mode="I",
                fps=fps,
                codec="libx264",
                pixelformat="yuv420p",
                quality=7,
            )
            for i in range(n_unique):
                frame = np.asarray(frames_with_text[i])
                # repeat current frame frames_per_image times
                for _ in range(frames_per_image):
                    writer.append_data(frame)
            writer.close()
        except Exception as e:
            log_event("slideshow_writer_err", {"err": str(e)})
            return b"", ("error", "video_writer_failed")

        # 6) Mux audio + video (shortest)
        out = os.path.join(td, "out.mp4")
        cmd = [
            _FFMPEG_EXE, "-y",
            "-i", vpath,
            "-i", apath,
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            out
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            log_event("slideshow_ffmpeg_err", {"err": str(e)})
            return b"", ("error", "ffmpeg_failed")

        payload = open(out, "rb").read()
        log_event("slideshow_ok", {
            "unique_frames": n_unique,
            "duration_s": round(duration, 2),
            "fps": fps,
            "frames_per_image": frames_per_image,
            "bytes": len(payload)
        })
        return payload, ("slideshow+tts", f"{tts_name} | {tts_model}")