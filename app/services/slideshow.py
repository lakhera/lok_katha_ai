# app/services/slideshow.py
# Description: This module handles the creation of slideshows from images and audio.
# Requires: imageio, Pillow, imageio-ffmpeg

from __future__ import annotations
import os, io, base64, tempfile
from typing import Tuple, List
from app.utils.log import log_event
from app.services.audio import synthesize_tts

# ---- Dependency checks ------------------------------------------------------

try:
    import imageio.v2 as imageio
    _IMG_OK = True
    _IMG_ERR = ""
except Exception as e:
    _IMG_OK = False
    _IMG_ERR = str(e)

try:
    from PIL import Image, ImageDraw, ImageFont
    _PIL_OK = True
    _PIL_ERR = ""
except Exception as e:
    _PIL_OK = False
    _PIL_ERR = str(e)

try:
    import imageio_ffmpeg
    _FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
    _FFMPEG_OK = bool(_FFMPEG_EXE)
    _FFMPEG_ERR = ""
except Exception as e:
    _FFMPEG_EXE = None
    _FFMPEG_OK = False
    _FFMPEG_ERR = str(e)


def _ensure_deps() -> tuple[bool, str]:
    """Return (ok, message) for slideshow deps."""
    if not _IMG_OK:
        return False, f"imageio not available: {_IMG_ERR}"
    if not _PIL_OK:
        return False, f"Pillow not available: {_PIL_ERR}"
    if not _FFMPEG_OK:
        return False, f"ffmpeg not available: {_FFMPEG_ERR or 'imageio-ffmpeg not found'}"
    return True, "ok"


# ---- Helpers ----------------------------------------------------------------

def _decode_images(images_b64: List[str], tmpdir: str) -> list[str]:
    """Decode data: URLs into PNG files; return list of file paths."""
    paths: list[str] = []
    for i, b64url in enumerate(images_b64 or []):
        try:
            if not (isinstance(b64url, str) and b64url.startswith("data:image")):
                continue
            header, data = b64url.split(",", 1)
            raw = base64.b64decode(data)
            p = os.path.join(tmpdir, f"frame_{i:03d}.png")
            with open(p, "wb") as f:
                f.write(raw)
            paths.append(p)
        except Exception as e:
            log_event("slideshow_img_decode_err", {"i": i, "err": str(e)})
    return paths


def _wrap_text(draw: "ImageDraw.ImageDraw", font: "ImageFont.FreeTypeFont", text: str, max_width: int) -> list[str]:
    words = (text or "").split()
    if not words:
        return []
    lines, cur = [], []
    for w in words:
        test = " ".join(cur + [w])
        if draw.textlength(test, font=font) <= max_width:
            cur.append(w)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines


def _fallback_text_frames(text: str, tmpdir: str, count: int = 3, size=(640, 360)) -> list[str]:
    """Render a few simple text frames if no images provided."""
    paths: list[str] = []
    try:
        W, H = size
        for i in range(max(1, count)):
            img = Image.new("RGB", size, (16, 16, 20))
            d = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", 28)
            except Exception:
                font = ImageFont.load_default()

            margin = 24
            max_w = W - 2 * margin
            lines = _wrap_text(d, font, (text or "").strip() or "(empty)", max_w)
            line_h = int(font.getbbox("Ag")[3] * 1.25) if hasattr(font, "getbbox") else 36
            block_h = max(line_h, line_h * len(lines or ["(empty)"]))
            y = (H - block_h) // 2

            for line in lines or ["(empty)"]:
                w = d.textlength(line, font=font)
                x = (W - int(w)) // 2
                d.text((x, y), line, fill=(235, 235, 240), font=font)
                y += line_h

            p = os.path.join(tmpdir, f"frame_text_{i:03d}.png")
            img.save(p)
            paths.append(p)
    except Exception as e:
        log_event("slideshow_text_render_err", {"err": str(e)})
    return paths


def _resize_frames(paths: list[str], width: int, height: int) -> list["Image.Image"]:
    seq = []
    for p in paths:
        try:
            img = Image.open(p).convert("RGB").resize((width, height))
            seq.append(img)
        except Exception:
            pass
    return seq


def _write_video_no_audio(frames: list["Image.Image"], fps: int, out_path: str) -> bool:
    """Write a small MP4 using imageio. Returns True on success."""
    try:
        # Prefer explicit ffmpeg writer (via imageio-ffmpeg)
        writer = imageio.get_writer(out_path, format="ffmpeg", mode="I",
                                    fps=max(1, int(fps)),
                                    codec="libx264",
                                    quality=6,  # lower = smaller
                                    pixelformat="yuv420p")
        for img in frames:
            writer.append_data(imageio.asarray(img))
        writer.close()
        return True
    except Exception as e:
        log_event("slideshow_writer_err", {"err": str(e)})
        return False


# ---- Public API -------------------------------------------------------------

def build_slideshow_video(
    text: str,
    images_b64: List[str],
    accent: str = "Indian",
    fps: int = 1,
    width: int = 640,
    height: int = 360,
) -> Tuple[bytes, tuple[str, str]]:
    """
    Build a low-res slideshow MP4 and mux TTS audio.
    Returns (video_bytes, backend_tag_tuple).
    On missing deps -> (b"", ("missing-deps", reason))
    """
    ok, msg = _ensure_deps()
    if not ok:
        log_event("slideshow_deps_missing", {"reason": msg})
        return b"", ("missing-deps", msg)

    # 1) Synthesize audio (uses app.services.audio with online/offline toggle)
    audio_bytes, (tts_name, tts_model), mime = synthesize_tts(text or "", accent)
    if not audio_bytes:
        return b"", ("fallback", "tts_failed")

    with tempfile.TemporaryDirectory(prefix="slideshow_") as td:
        # 2) Decode provided images or render fallback text frames
        paths = _decode_images(images_b64, td)
        if not paths:
            paths = _fallback_text_frames((text or "")[:200], td, count=3, size=(width, height))

        # 3) Resize to target and write a small mp4 (no audio)
        frames = _resize_frames(paths, width, height)
        if not frames:
            return b"", ("fallback", "no_frames")

        raw_mp4 = os.path.join(td, "slideshow_no_audio.mp4")
        if not _write_video_no_audio(frames, fps=fps, out_path=raw_mp4):
            return b"", ("fallback", "video_writer_failed")

        # 4) Write audio to temp file
        aext = "mp3" if mime == "audio/mpeg" else "wav"
        ap = os.path.join(td, f"audio.{aext}")
        with open(ap, "wb") as f:
            f.write(audio_bytes)

        # 5) Mux audio + video using ffmpeg (shortest)
        out = os.path.join(td, "out.mp4")
        cmd = [
            _FFMPEG_EXE, "-y",
            "-i", raw_mp4,
            "-i", ap,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
            "-c:a", "aac",
            "-shortest",
            out
        ]
        try:
            import subprocess
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            log_event("slideshow_ffmpeg_err", {"err": str(e)})
            return b"", ("fallback", "ffmpeg_failed")

        payload = open(out, "rb").read()
        backend = ("imageio+ffmpeg", f"{tts_name} | {tts_model}")
        log_event("slideshow_ok", {"bytes": len(payload), "frames": len(frames), "fps": fps})
        return payload, backend
