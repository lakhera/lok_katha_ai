# app/services/video.py
# Description: Generate a video with TTS audio and rendered text slide (MoviePy path)
# Requires: moviepy, Pillow, numpy, imageio-ffmpeg

from typing import Tuple
import os, tempfile
from app.utils.log import log_event
from app.services.audio import synthesize_tts

_MOVIEPY_OK = True; _PIL_OK = True; _NP_OK = True; _FFMPEG_OK = True

try:
    import numpy as np
except Exception as e:
    _NP_OK = False; _NP_ERR = str(e)

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception as e:
    _PIL_OK = False; _PIL_ERR = str(e)

try:
    from moviepy.editor import AudioFileClip, ImageClip
except Exception as e:
    _MOVIEPY_OK = False; _MOVIEPY_ERR = str(e)

try:
    import imageio_ffmpeg
    _ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    _FFMPEG_OK = bool(_ffmpeg_path)
except Exception as e:
    _FFMPEG_OK = False; _FFMPEG_ERR = str(e)


def _deps_ready():
    if not _NP_OK: return False, f"numpy not available: {_NP_ERR}"
    if not _PIL_OK: return False, f"Pillow not available: {_PIL_ERR}"
    if not _MOVIEPY_OK: return False, f"moviepy not available: {_MOVIEPY_ERR}"
    if not _FFMPEG_OK: return False, f"ffmpeg not available: {globals().get('_FFMPEG_ERR','unknown')}"
    return True, "ok"


def missing_deps_list():
    missing = []
    if not _NP_OK: missing.append("numpy")
    if not _PIL_OK: missing.append("Pillow")
    if not _MOVIEPY_OK: missing.append("moviepy")
    if not _FFMPEG_OK: missing.append("ffmpeg (imageio-ffmpeg)")
    return missing


def _wrap_text(text, draw, font, max_width):
    words = (text or '').split(); lines, cur = [], []
    for w in words:
        test = ' '.join(cur + [w])
        if draw.textlength(test, font=font) <= max_width: cur.append(w)
        else:
            if cur: lines.append(' '.join(cur))
            cur = [w]
    if cur: lines.append(' '.join(cur))
    return '\n'.join(lines)


def _render_slide(text: str, size=(1280, 720)):
    if not _PIL_OK: raise RuntimeError("Pillow not available")
    from PIL import Image, ImageDraw, ImageFont
    W, H = size
    img = Image.new('RGB', size, (16, 16, 20))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype('DejaVuSans.ttf', 46)
    except Exception:
        font = ImageFont.load_default()
    margin = 80
    wrapped = _wrap_text((text or '').strip(), d, font, W - 2 * margin)
    lines = wrapped.split('\n') if wrapped else []
    line_h = int(font.getbbox('Ag')[3] * 1.25) if hasattr(font, 'getbbox') else 56
    block_h = max(line_h, line_h * len(lines))
    y = (H - block_h) // 2
    for line in lines or ['(empty)']:
        w = d.textlength(line, font=font)
        x = (W - int(w)) // 2
        d.text((x, y), line, fill=(235, 235, 240), font=font)
        y += line_h
    return img


def synthesize_video(text: str, accent: str) -> Tuple[bytes, tuple[str, str]]:
    text = (text or '').strip()
    if not text:
        return b'', ('fallback', 'none')

    ok, msg = _deps_ready()
    if not ok:
        log_event('video_deps_missing', {'reason': msg})
        return b'', ('missing-deps', msg)

    import numpy as np
    from moviepy.editor import AudioFileClip, ImageClip

    # TTS (uses your online/offline toggle inside synthesize_tts)
    audio_bytes, (tts_name, tts_model), mime = synthesize_tts(text, accent)
    if not audio_bytes:
        log_event('video_tts_failed')
        return b'', ('fallback', 'tts_failed')

    with tempfile.TemporaryDirectory(prefix='video_') as td:
        ap = os.path.join(td, 'audio.' + ('mp3' if mime == 'audio/mpeg' else 'wav'))
        with open(ap, 'wb') as f:
            f.write(audio_bytes)
        aclip = AudioFileClip(ap)
        dur = max(2.0, float(aclip.duration or 2.0))

        # single-frame clip with centered text
        frame_img = _render_slide(text, (1280, 720))
        frame = np.array(frame_img)
        vclip = ImageClip(frame).set_duration(dur).set_audio(aclip)

        vp = os.path.join(td, 'out.mp4')
        vclip.write_videofile(
            vp, fps=24, codec='libx264', audio_codec='aac',
            preset='veryfast', bitrate='1200k',
            verbose=False, logger=None
        )

        payload = open(vp, 'rb').read()
        backend = ('moviepy+tts', f'{tts_name} | {tts_model}')
        log_event('video_ok', {'bytes': len(payload), 'dur': dur, 'backend': backend})
        return payload, backend
