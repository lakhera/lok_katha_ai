# app/services/images.py
# Description: Robust image generation via Hugging Face Inference API with retries/backoff + fallbacks.
# Requires: requests, Pillow
# Env (all optional except HF_API_KEY):
#   HF_API_KEY=
#   HF_IMAGE_MODELS=stabilityai/sd-turbo,black-forest-labs/FLUX.1-dev,stabilityai/stable-diffusion-xl-base-1.0
#   HF_TIMEOUT_CONNECT=10
#   HF_TIMEOUT_READ=180
#   HF_MAX_RETRIES=3
#   HF_IMG_WIDTH=512
#   HF_IMG_HEIGHT=512

# import libraries
from __future__ import annotations
import os, time, base64, json, random, io
from typing import List, Tuple, Optional, Dict, Any
import requests
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from app.utils.log import log_event

load_dotenv()

# environment variables and configuration
HF_API_KEY = (os.getenv("HF_API_KEY") or "").strip()

# Try quicker model first by default
HF_IMAGE_MODELS = [
    m.strip() for m in (
        os.getenv("HF_IMAGE_MODELS")
        or "stabilityai/sd-turbo,black-forest-labs/FLUX.1-dev,stabilityai/stable-diffusion-xl-base-1.0"
    ).split(",")
    if m.strip()
]

# sane defaults
TIMEOUT_CONNECT = int(os.getenv("HF_TIMEOUT_CONNECT", 10))
TIMEOUT_READ    = int(os.getenv("HF_TIMEOUT_READ", 180))
MAX_RETRIES     = int(os.getenv("HF_MAX_RETRIES", 3))
IMG_W           = int(os.getenv("HF_IMG_WIDTH", 512))
IMG_H           = int(os.getenv("HF_IMG_HEIGHT", 512))

_SESSION = requests.Session()

if HF_API_KEY:
    _SESSION.headers.update({
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "*/*",
        # Inference API options — most backends support these
        "x-wait-for-model": "true",
        "x-use-cache": "true",
        "User-Agent": "LokKatha.ai (images)"
    })

# helper functions
def _style_hint(style: str) -> str:
    s = (style or "none").strip().lower()
    styles = {
        "none":          "kid-friendly illustration",
        "watercolor":    "soft watercolor illustration, textured paper",
        "pencil":        "clean pencil sketch, subtle shading",
        "flat-vector":   "flat vector art, minimal shading",
        "anime":         "anime style, vibrant, clean lineart, cel shading",
        "oil-painting":  "rich oil painting on canvas, detailed brush strokes",
        "comic":         "comic-book style, halftone, bold inking, dynamic composition",
        "clay":          "claymation stop-motion look, soft lighting, sculpted shapes",
    }
    return styles.get(s, styles["none"])

# Model-specific sane defaults (kept modest to reduce latency)
_MODEL_HINTS: Dict[str, Dict[str, Any]] = {
    "stabilityai/sd-turbo": {
        "num_inference_steps": 4,
        "guidance_scale": 1.5,
    },
    "black-forest-labs/FLUX.1-dev": {
        "num_inference_steps": 12,
        "guidance_scale": 3.0,
    },
    "stabilityai/stable-diffusion-xl-base-1.0": {
        "num_inference_steps": 18,
        "guidance_scale": 5.0,
    },
}

# core functions
def _payload_for(model: str, prompt: str, style: str) -> Dict[str, Any]:
    base_params = {
        "width": IMG_W,
        "height": IMG_H,
    }
    # merge hints if any
    hints = _MODEL_HINTS.get(model, {})
    base_params.update(hints)

    return {
        "inputs": f"{_style_hint(style)}. Scene: {prompt}",
        "parameters": base_params,
        "options": {"wait_for_model": True, "use_cache": True},
    }

# exponential backoff with jitter
def _backoff(attempt: int) -> float:
    # jittered exponential backoff
    return (1.6 ** attempt) + random.random()

# single POST attempt
def _post_once(model: str, payload: Dict[str, Any]) -> Optional[bytes]:
    url = f"https://api-inference.huggingface.co/models/{model}"
    try:
        resp = _SESSION.post(url, data=json.dumps(payload),
                             timeout=(TIMEOUT_CONNECT, TIMEOUT_READ))
    except requests.RequestException as e:
        log_event("hf_req_exc", {"model": model, "err": str(e)})
        return None

    ct = (resp.headers.get("content-type") or "").lower()
    if resp.status_code == 200 and "image/" in ct:
        return resp.content

    # transient / queue states
    if resp.status_code in (429, 503):
        try:
            j = resp.json()
        except Exception:
            j = {"text": resp.text[:200]}
        log_event("hf_busy", {"model": model, "status": resp.status_code, "msg": j})
        return None

    # other errors — log and bail
    try:
        err = resp.json()
    except Exception:
        err = {"text": resp.text[:200]}
    log_event("hf_http_error", {"model": model, "status": resp.status_code, "error": err})
    return None

# placeholder image generator
def _placeholder_image_b64(text: str) -> str:
    # Always return something so UI isn't empty
    W, H = 512, 320
    img = Image.new("RGB", (W, H), (22, 24, 28))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 18)
    except Exception:
        font = ImageFont.load_default()
    msg = (text or "LokKatha.ai").strip()[:120]
    w = d.textlength(msg, font=font)
    d.text(((W - int(w)) // 2, H // 2 - 10), msg, fill=(235, 235, 240), font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")

# main function
def generate_images_b64(
    prompt: str,
    n: int = 2,
    style: str = "none",
) -> Tuple[List[str], Tuple[str, str]]:
    """
    Try models in order; stop at first that returns images.
    Returns (data_urls, ('hf'|'fallback', model_name))
    """
    if not HF_API_KEY:
        log_event("hf_missing")
        # return placeholder so UI shows something
        return [_placeholder_image_b64(prompt)], ("fallback", "no_api_key")

    prompt = (prompt or "").strip()
    if not prompt:
        return [_placeholder_image_b64("Empty prompt")], ("fallback", "empty_prompt")

    want = max(1, min(4, int(n or 1)))
    for model in HF_IMAGE_MODELS:
        got: List[str] = []
        for i in range(want):
            payload = _payload_for(model, prompt, style)
            raw = None
            # retry loop per image request
            for attempt in range(1, MAX_RETRIES + 1):
                raw = _post_once(model, payload)
                if raw:
                    break
                wait = _backoff(attempt)
                log_event("hf_retry", {"model": model, "attempt": attempt, "wait_s": round(wait, 2)})
                time.sleep(wait)

            if not raw:
                continue

            got.append("data:image/png;base64," + base64.b64encode(raw).decode("utf-8"))

        if got:
            log_event("hf_ok", {"model": model, "count": len(got)})
            return got, ("hf", model)

        log_event("hf_model_exhausted", {"model": model})

    # If every model timed out/failed, return one friendly placeholder
    log_event("hf_all_failed", {"models_tried": HF_IMAGE_MODELS})
    return [_placeholder_image_b64(prompt)], ("fallback", "none")