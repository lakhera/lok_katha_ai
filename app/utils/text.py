# app/utils/text.py
# Description: Text processing utilities for sentence tokenization, bullet formatting, Devanagari detection
# Requires: nltk

# import libraries
import re, nltk
from nltk.tokenize import sent_tokenize

try: 
    nltk.data.find("tokenizers/punkt")
except LookupError: nltk.download("punkt", quiet=True)

# text utilities
def tokenize_sentences(text: str) -> list[str]:
    text = (text or "").strip()
    if not text: return []
    try: return sent_tokenize(text)
    except Exception: return [s.strip() for s in re.split(r'(?<=[.?!।])\s+', text) if s.strip()]

# format list of sentences as numbered bullets
def bullets(sents: list[str]) -> str:
    return "\n".join(f"{i+1}. {s}" for i, s in enumerate(sents) if s.strip())

# check if text contains Devanagari characters
def needs_devanagari(*texts: str) -> bool:
    deva = re.compile(r'[\u0900-\u097F]')
    return any((t and deva.search(t)) for t in texts)

# system directive for story generation
def system_directive(genre="Folk Tale", region="All-India", lang="English"):
    return (f"You are LokKatha.ai, a culturally sensitive Indian storyteller for middle-school learners (ages 10–14).\n"
            f"Write a {genre.lower()} in {lang}, set in {region}.\n"
            "Rules:\n- Safe & respectful; no stereotypes or sensitive content; age-appropriate\n"
            "- Simple words (A2–B1), 150–220 words, 1–2 named characters\n"
            "End with “Takeaway:” summarizing the lesson.")