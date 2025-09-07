# app/services/pdf_export.py
# Description: Generate a PDF document from story text, translation, and images.
# Requires: reportlab

# import statements
import os
import urllib.request
import datetime
from typing import Optional, List
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak, XPreformatted
)
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import utils as U
from app.utils.log import log_event
from app.utils.text import needs_devanagari

# Use a fonts directory relative to the project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONT_DIR = os.path.join(BASE_DIR, "fonts")
os.makedirs(FONT_DIR, exist_ok=True)

# Register Devanagari font if needed
def _register_hindi_font_if_needed() -> Optional[str]:
    fonts = [
        ("Hind", "https://raw.githubusercontent.com/google/fonts/main/ofl/hind/Hind-Regular.ttf"),
        ("NotoSansDevanagari", "https://raw.githubusercontent.com/google/fonts/main/ofl/notosansdevanagari/NotoSansDevanagari-Regular.ttf"),
        ("NotoSerifDevanagari", "https://raw.githubusercontent.com/google/fonts/main/ofl/notoserifdevanagari/NotoSerifDevanagari-Regular.ttf"),
    ]
    for name, url in fonts:
        try:
            path = os.path.join(FONT_DIR, f"{name}.ttf")
            if not os.path.exists(path):
                urllib.request.urlretrieve(url, path)
            pdfmetrics.registerFont(TTFont(name, path))
            log_event("font_ok", {"name": name})
            return name
        except Exception as e:
            log_event("font_dl_err", {"name": name, "err": str(e)})
    return None

# Main function to build the PDF
def build_pdf(
    story: str,
    translation: Optional[str],
    image_paths: Optional[List[str]],
    out_path: str = "lokkatha_story.pdf"
) -> str:
    import datetime

    story_txt = (story or "").replace("\r\n", "\n").replace("\r", "\n")
    trans_txt = (translation or "").replace("\r\n", "\n").replace("\r", "\n")
    body_font = "Helvetica"
    if needs_devanagari(story_txt, trans_txt):
        dev = _register_hindi_font_if_needed()
        body_font = dev or "Helvetica"
        if dev is None:
            log_event("font_fallback_helvetica")

    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=2.2 * cm,
        rightMargin=2.2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="BodyWrap",
        fontName=body_font,
        fontSize=12.5,
        leading=16,
        wordWrap='CJK'
    ))
    heading = styles["Heading2"]

    def _cover(c, _):
        w, h = A4
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(w / 2, h * 0.70, "Smart Cultural Storyteller — Reviving heritage with AI")
        c.setFont("Helvetica", 11)
        c.drawCentredString(w / 2, h * 0.66, "Design & Developed By Amit Lakhera")
        c.setFont("Helvetica", 10)
        c.drawCentredString(w / 2, h * 0.62, datetime.datetime.now().strftime('%d %b %Y'))

    def _hf(c, doc):
        w, h = A4
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(w / 2, h - 1.5 * cm, "Smart Cultural Storyteller — Reviving heritage with AI")
        c.setFont("Helvetica", 10)
        c.drawCentredString(w / 2, h - 2.0 * cm, "Design & Developed By Amit Lakhera")
        c.line(2 * cm, h - 2.2 * cm, w - 2 * cm, h - 2.2 * cm)
        c.line(2 * cm, 1.8 * cm, w - 2 * cm, 1.8 * cm)
        c.setFont("Helvetica", 9)
        c.drawString(2 * cm, 1.4 * cm, "LokKatha.ai")
        c.drawRightString(w - 2 * cm, 1.4 * cm, f"Page {doc.page}")

    flow = [
        Spacer(1, 200),  # Add space so cover text is centered
        PageBreak(),     # Start story on a new page
        Paragraph("Story", heading),
        Spacer(1, 12),
        Paragraph(story_txt.replace('\n', '<br/>'), styles["BodyWrap"]),
        Spacer(1, 10)
    ]
    if trans_txt.strip():
        flow += [
            Paragraph("Translation", heading),
            Spacer(1, 12),
            Paragraph(trans_txt.replace('\n', '<br/>'), styles["BodyWrap"]),
            Spacer(1, 10)
        ]
    if image_paths:
        for p in image_paths:
            try:
                if not os.path.exists(p):
                    continue
                img = U.ImageReader(p)
                iw, ih = img.getSize()
                max_w = A4[0] - (doc.leftMargin + doc.rightMargin)
                max_h = A4[1] - 5 * cm
                scale = min(max_w / iw, max_h / ih, 1.0)
                flow += [PageBreak(), RLImage(p, iw * scale, ih * scale)]
            except Exception as e:
                log_event("pdf_img_err", {"path": p, "err": str(e)})

    doc.build(flow, onFirstPage=_cover, onLaterPages=_hf)
    return out_path