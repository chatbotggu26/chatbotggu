# 🏛️ Godavari Global University (GGU) — Multimodal AI Chatbot

A production-grade, feature-rich **Multimodal AI Chatbot Single-Page Application (SPA)** built with Python Flask, the official Google GenAI SDK (`google-genai`), and an ultra-modern **Liquid Glass (Glassmorphism)** user interface.

Grounding institutional knowledge about **Godavari Global University (GGU)** with conversational memory, multi-session history, file analysis (Images & PDFs), and complete **Voice Assistant capabilities (Speech-to-Text & Text-to-Speech)**.

---

## ✨ Key Features

- 💎 **Liquid Glass UI (Glassmorphism)**: Frosted glass elements, dynamic refraction, edge-to-edge fullpage responsive layout with live campus wallpaper.
- 🖼️ **Multimodal File Analysis**: Upload and analyze `.png`, `.jpg`, and `.pdf` documents directly within the conversation.
- 🎙️ **Full Voice Assistant**:
  - **Speech Input**: Record questions via microphone with real-time audio visualization.
  - **Text-to-Speech (TTS)**: Automatic response read-aloud via Web Speech API with individual message replay and a global mute/unmute toggle.
- 🗂️ **Sidebar Chat History**: Multi-session management allowing users to browse, revisit, and delete past conversations stored server-side.
- 🎓 **GGU Institutional Knowledge**: Grounded with verified knowledge about Godavari Global University (300-acre campus, programs, admissions, placement records, and faculties).
- 🔒 **Enterprise-Grade Security**:
  - Environment variable isolation (`python-dotenv`) protecting API keys.
  - Automatic post-processing file cleanup in `uploads/`.
  - Secure filename sanitization via Werkzeug.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.10+, Flask, `google-genai` SDK, `Flask-Session`, `Werkzeug`
- **Frontend**: HTML5, Vanilla CSS3 (Custom Glassmorphism design system), Vanilla JavaScript (ES6+)
- **Markdown & Code Rendering**: `marked.js`
- **Audio & Media**: HTML5 `MediaRecorder` API, Web Speech API (`speechSynthesis`)

---

## 📂 Project Architecture

```plaintext
aichatbot(ggu)/
├── app.py                  # Flask web server, Gemini multimodal router & session manager
├── knowledge_base.py       # GGU institutional knowledge retrieval & system prompt grounding
├── requirements.txt        # Python dependency manifest
├── .env.example            # Environment template for API keys & settings
├── .gitignore              # Ignores .env, sessions, uploads, and caches
├── README.md               # Project documentation
├── data/
│   └── ggu_knowledge.json  # Structured GGU campus facts & institutional knowledge
├── static/
│   └── images/
│       └── ggu-bg.jpg      # High-resolution campus background wallpaper
├── templates/
│   └── index.html          # Responsive Single-Page Application (SPA) frontend
└── uploads/                # Temporary local storage for multimodal uploads (auto-cleaned)
```

---

## 🚀 Quickstart Guide

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/chatbotggu.git
cd chatbotggu
```

### 2. Create and Activate a Virtual Environment
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env` and insert your Gemini API Key from [Google AI Studio](https://aistudio.google.com/):
```bash
cp .env.example .env
```
Edit `.env`:
```ini
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash
SECRET_KEY=generate_a_random_secret_key
PORT=5000
HOST=0.0.0.0
```

### 5. Launch the Server
```bash
python app.py
```
Open your browser and navigate to:
**`http://localhost:5000`** (or `http://127.0.0.1:5000`)

---

## 🔒 Security Best Practices

- **Never commit `.env`**: Always ensure `.env` remains in `.gitignore`.
- **API Key Protection**: Never hardcode API credentials into frontend JavaScript or server code.
- **Session Protection**: Flask sessions are kept server-side in `flask_session/` and excluded from git tracking.

---

## 📄 License
This project is licensed under the MIT License — see the LICENSE file for details.
