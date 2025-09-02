# LokKatha.ai — Smart Cultural Storyteller

## 📚 Quick Links
- [API Reference](API.md)
- [Service Module Interfaces](docs/SERVICES.md)
- [Contribution Guidelines](CONTRIBUTING.md)
- [AI Agent Instructions](.github/copilot-instructions.md)

Reviving heritage with AI to preserve and share Indian cultural narratives.

## ✨ Features
- 📖 **Interactive Story Generation** — Folk tales & historical narratives
- 🌐 **Multilingual Translation** — English ↔ Hindi and more
- 🔊 **Audio Narration** — Indian / British accent TTS (gTTS + pyttsx3 fallback)
- 🖼️ **Visual Storytelling** — AI-generated images (Hugging Face models)
- 📄 **Export Options** — Hindi-safe PDF/TXT with fonts
- 🎬 **Video Output** — Slideshow / Shortclip / Full MoviePy video
- 🎨 **Modern UI** — Progress bars, model badges, colorful buttons

## 🛠️ Tech Stack
- **Backend:** FastAPI (Python)
- **Frontend:** HTML/CSS/JS (served via FastAPI StaticFiles)
- **AI Services:** OpenRouter LLMs, Gemini, Hugging Face image models
- **TTS:** gTTS (online) with pyttsx3 (offline fallback)
- **Media Processing:** Pillow, imageio, MoviePy, ffmpeg
- **Deployment:** Uvicorn

## 🚀 Installation
```bash
git clone https://github.com/lakhera/lok_katha_ai.git
cd lok_katha_ai
python -m venv .venv
source .venv/bin/activate   # (or .venv\Scripts\activate on Windows)
pip install -r requirements.txt
cp .env.example .env
./start.sh

Then open http://localhost:8000

👥 Contributors
```bash
* Amit Lakhera — Design & Development
