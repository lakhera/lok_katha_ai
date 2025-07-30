# LokKatha.ai - Folk stories AI

**LokKatha.ai** is a Smart Cultural Storyteller that uses artificial intelligence to preserve, retell, and celebrate folk tales, oral histories, and traditional narratives in interactive and multimodal formats.

---

## Project Highlights

- **AI-powered storytelling** using GPT models
- **Text-to-Speech narration** with emotion and local accents (ElevenLabs, Coqui TTS)
- **AI-generated visuals** for characters and scenes (D-ID, Pika, SD)
- **Multilingual support** for regional reach
- **LangChain-powered interaction flow** for “Choose Your Own Adventure” experiences
- Based on FastAPI + SQLite for simple and scalable deployment

---

## Repository Structure

```bash
smart-cultural-storyteller/
├── backend/                # FastAPI backend
│   ├── db/                 # SQLite setup
│   ├── models/             # SQLAlchemy models
│   ├── routers/            # API endpoints
│   ├── schemas/            # Pydantic schemas
│   └── services/           # NLP, TTS, image generation services
├── ai_models/              # Wrappers for GPT, TTS, visual tools
├── data/                   # Folk stories, translations, samples
├── gradio_app/             # Interactive storytelling demo
├── tests/                  # Unit and integration tests
├── scripts/                # Data and tool scripts
├── docs/                   # Proposal, diagrams, documentation
└── README.md
```

---

##  Started

### Prerequisites

- Python 3.11+
- `pip install -r requirements.txt`
- SQLite installed (default setup)

### Run Backend

```bash
cd backend
uvicorn main:app --reload
```

### Visit API Docs

- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Example Use Case

> Upload or type a folk tale → Choose your language → Select “Story Mode” or “Adventure Mode” → LokKatha.ai retells the story using AI with images and audio.

---

## Environment Variables (Example)

Create a `.env` file with:
```
OPENAI_API_KEY=your-key
TTS_API_KEY=your-tts-key
LANGCHAIN_API_KEY=your-key
```

---

## License

MIT License

---

## Acknowledgements

- Inspired by India's oral storytelling heritage
- Powered by OpenAI, Coqui, ElevenLabs, LangChain, and Gradio
