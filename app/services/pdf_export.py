# app/services/pdf_export.py
# Description: This module handles PDF export functionality.
# Requires: reportlab

import os, urllib.request, datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak, XPreformatted
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from app.utils.log import log_event
from app.utils.text import needs_devanagari
FONT_DIR = os.path.abspath("fonts"); os.makedirs(FONT_DIR, exist_ok=True)
def _register_hindi_font_if_needed() -> str | None:
    for name, url in [("Hind","https://raw.githubusercontent.com/google/fonts/main/ofl/hind/Hind-Regular.ttf"),
                      ("NotoSansDevanagari","https://raw.githubusercontent.com/google/fonts/main/ofl/notosansdevanagari/NotoSansDevanagari-Regular.ttf"),
                      ("NotoSerifDevanagari","https://raw.githubusercontent.com/google/fonts/main/ofl/notoserifdevanagari/NotoSerifDevanagari-Regular.ttf")]:
        try:
            path = os.path.join(FONT_DIR, f"{name}.ttf")
            if not os.path.exists(path): urllib.request.urlretrieve(url, path)
            pdfmetrics.registerFont(TTFont(name, path)); log_event("font_ok", {"name": name}); return name
        except Exception as e: log_event("font_dl_err", {"name": name, "err": str(e)})
    return None
def build_pdf(story: str, translation: str | None, image_paths: list[str] | None, out_path: str = "lokkatha_story.pdf") -> str:
    story_txt = (story or "").replace("\r\n","\n").replace("\r","\n")
    trans_txt = (translation or "").replace("\r\n","\n").replace("\r","\n")
    body_font = "Helvetica"
    if needs_devanagari(story_txt, trans_txt):
        dev = _register_hindi_font_if_needed(); body_font = dev or "Helvetica"
        if dev is None: log_event("font_fallback_helvetica")
    doc  = SimpleDocTemplate(out_path, pagesize=A4, leftMargin=2.2*cm, rightMargin=2.2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet(); styles.add(ParagraphStyle(name="BodyWrap", fontName=body_font, fontSize=12.5, leading=16, wordWrap='CJK'))
    heading = styles["Heading2"]
    def _cover(c,_): w,h=A4; c.setFont("Helvetica-Bold",20); c.drawCentredString(w/2,h*0.70,"Smart Cultural Storyteller — Reviving heritage with AI"); c.setFont("Helvetica",11); c.drawCentredString(w/2,h*0.66,"Design & Developed By Amit Lakhera"); c.setFont("Helvetica",10); c.drawCentredString(w/2,h*0.62,datetime.datetime.now().strftime('%d %b %Y'))
    def _hf(c,doc): w,h=A4; c.setFont("Helvetica-Bold",12); c.drawCentredString(w/2,h-1.5*cm,"Smart Cultural Storyteller — Reviving heritage with AI"); c.setFont("Helvetica",10); c.drawCentredString(w/2,h-2.0*cm,"Design & Developed By Amit Lakhera"); c.line(2*cm,h-2.2*cm,w-2*cm,h-2.2*cm); c.line(2*cm,1.8*cm,w-2*cm,1.8*cm); c.setFont("Helvetica",9); c.drawString(2*cm,1.4*cm,"LokKatha.ai"); c.drawRightString(w-2*cm,1.4*cm,f"Page {doc.page}")
    flow=[Paragraph("Story",heading), XPreformatted(story_txt,styles["BodyWrap"],maxLineLength=110), Spacer(1,10)]
    if trans_txt.strip(): flow += [Paragraph("Translation",heading), XPreformatted(trans_txt,styles["BodyWrap"],maxLineLength=110), Spacer(1,10)]
    if image_paths:
        for p in image_paths:
            try:
                if not os.path.exists(p): continue
                from reportlab.lib import utils as U; img=U.ImageReader(p); iw,ih=img.getSize(); max_w,max_h=A4[0]-(doc.leftMargin+doc.rightMargin), A4[1]-5*cm; scale=min(max_w/iw,max_h/ih,1.0)
                flow += [PageBreak(), RLImage(p, iw*scale, ih*scale)]
            except Exception: pass
    doc.build(flow); return out_path
