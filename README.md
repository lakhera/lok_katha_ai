# LokKatha.ai — Smart Cultural Storyteller

<p align="center">
  <img src="app/static/lokkatha_logo.png" alt="LokKatha.ai logo" width="140"/><br/>
  <b>Reviving heritage with AI</b><br/>
  <i>Preserve and share Indian folk tales, history & culture in engaging formats</i>
</p>

---

## 📚 Quick Links
- [API Reference](API.md)
- [Service Module Interfaces](docs/SERVICES.md)
- [Contribution Guidelines](CONTRIBUTING.md)
- [AI Agent Instructions](.github/copilot-instructions.md)

---

## ✨ Features
- 📖 **Interactive Story Generation** — Folk tales & historical narratives
- 🌐 **Multilingual Translation** — English ↔ Hindi (extendable to more)
- 🔊 **Audio Narration** — Indian / British accent TTS (gTTS + pyttsx3 fallback)
- 🖼️ **Visual Storytelling** — AI-generated illustrations (Hugging Face models, style options)
- 📄 **Export Options** — Hindi-safe PDF/TXT with embedded fonts
- 🎬 **Video Output** — Slideshow / Shortclip with captions + narration
- 🎨 **Modern UI** — Polished header, progress bars, model badges, colorful buttons

---

## 🛠️ Tech Stack
- **Backend:** FastAPI (Python)
- **Frontend:** HTML/CSS/JS (served via FastAPI StaticFiles)
- **AI Services:** OpenRouter LLMs, Gemini, Hugging Face image models
- **TTS:** gTTS (online) with pyttsx3 (offline fallback)
- **Media Processing:** Pillow, imageio, MoviePy, ffmpeg
- **Deployment:** Uvicorn

---

## 🚀 Installation
```bash
git clone https://github.com/lakhera/lok_katha_ai.git
cd lok_katha_ai
python -m venv .venv
source .venv/bin/activate   # (or .venv\Scripts\activate on Windows)
pip install -r requirements.txt
cp .env.example .env
```

### Run locally
```bash
uvicorn app.main:app --reload
# or
./start.sh
```

Then open [http://localhost:8000](http://localhost:8000)

---

## 👥 Contributors
- **Amit Lakhera** — Design & Development  
  *(Student code: iitrprai_24082167)*

---

## 📜 License
This project is licensed under the [MIT License](LICENSE).
