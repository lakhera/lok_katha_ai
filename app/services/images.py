
import os, base64, requests
from dotenv import load_dotenv
from app.utils.log import log_event
load_dotenv()
HF_API_KEY = os.getenv("HF_API_KEY")
HF_IMAGE_MODELS = [m.strip() for m in (os.getenv("HF_IMAGE_MODELS") or
                    "black-forest-labs/FLUX.1-dev,stabilityai/sd-turbo,stabilityai/stable-diffusion-xl-base-1.0").split(",")]
def _style_hint(style: str) -> str:
    styles = {
        "none": "kid-friendly illustration",
        "watercolor": "soft watercolor illustration, textured paper",
        "pencil": "clean pencil sketch, subtle shading",
        "flat-vector": "flat vector art, minimal shading",
        "anime": "anime style, vibrant, clean lineart, cel shading",
        "oil-painting": "rich oil painting on canvas, detailed brush strokes",
        "comic": "comic-book style, halftone, bold inking, dynamic",
        "clay": "claymation stop-motion look, soft lighting, sculpted shapes",
    }
    return styles.get((style or "none").strip().lower(), styles["none"])
def generate_images_b64(prompt: str, n: int = 2, style: str = "none") -> tuple[list[str], tuple[str, str]]:
    if not HF_API_KEY: log_event("hf_missing"); return [], ("fallback","none")
    results: list[str] = []
    for m in HF_IMAGE_MODELS:
        try:
            for _ in range(max(1, min(4, n))):
                r = requests.post(f"https://api-inference.huggingface.co/models/{m}",
                    headers={"Authorization": f"Bearer {HF_API_KEY}"}, json={"inputs": f"{_style_hint(style)}. Scene: {prompt}"}, timeout=90)
                if r.status_code == 200 and "image" in r.headers.get("content-type",""):
                    results.append("data:image/png;base64," + base64.b64encode(r.content).decode("utf-8"))
            if results: log_event("hf_ok", {"model": m, "count": len(results)}); return results, ("hf", m)
        except Exception as e: log_event("hf_exc", {"model": m, "err": str(e)})
    return results, ("fallback","none")
