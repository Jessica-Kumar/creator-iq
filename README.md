# 🎬 CreatorIQ RAG Video Analytics

An AI-powered RAG (Retrieval-Augmented Generation) dashboard that ingests, transcribes, and analyzes YouTube Videos and Instagram Reels. Using LangGraph, FastAPI, ChromaDB, and local embeddings, this system allows users to chat with their video transcripts and run comparative hook/engagement audits with live metrics.

---

## ✨ Core Features

*   **Dual Platform Ingestion**: Support for YouTube Videos and Instagram Reels.
*   **Zero-Credential Instagram Auth**: Utilizes a desktop Selenium window popup (non-headless) to log into Instagram directly on their official domain, capturing session state securely without exposing passwords to our backend.
*   **Enriched RAG Ingestion**: Automatically computes engagement rates and prepends detailed metadata cards (Views, Likes, Comments, Followers, Upload Date, Duration, and Hashtags) to chunks so the LLM can answer precise analytical and metrics questions.
*   **Flexible Model Fallbacks**: Automatically falls back across Gemini versions (`gemini-2.0-flash` ➡️ `gemini-1.5-flash` ➡️ `gemini-1.5-pro` ➡️ `gemini-2.5-flash`) depending on key tier access, quotas, or region limitations.
*   **Local Audio processing**: Direct audio downloading via `yt-dlp` using captured cookies, local Whisper transcribing, and local `all-MiniLM-L6-v2` vector embedding (0% API costs for extraction).
*   **Streaming Chat**: Real-time response streaming with interactive source citations (linking directly to the video and chunk index).

---

## 🛠️ Tech Stack

| Layer | Component | Description |
| :--- | :--- | :--- |
| **Frontend** | React + Vite + Tailwind CSS | Ultra-sleek dark mode UI with interactive charts, chat panels, and popups. |
| **Backend** | FastAPI + Uvicorn | High-performance async server offering SSE streaming endpoints. |
| **Orchestration** | LangGraph | State-driven workflow engine supporting chat history and memory. |
| **Vector Search** | ChromaDB | Persistent local vector store managing metadata filtering. |
| **Embeddings** | `all-MiniLM-L6-v2` | Sentence-transformers model running locally on CPU. |
| **Transcription** | OpenAI Whisper (Local) | Generates transcriptions locally from downloaded video audios. |
| **Scraping/Download**| Selenium + `yt-dlp` | Automates session state extraction and video audio pulling. |

---

## 📐 System Architecture

```mermaid
graph TD
    %% Styling
    classDef main fill:#1e293b,stroke:#8b5cf6,stroke-width:2px,color:#f8fafc;
    classDef external fill:#0f172a,stroke:#3b82f6,stroke-width:1px,stroke-dasharray: 5 5,color:#94a3b8;
    classDef local fill:#111827,stroke:#10b981,stroke-width:1.5px,color:#f8fafc;

    %% Elements
    UI[React Frontend App]:::main
    API[FastAPI Server]:::main
    Sel[Selenium Desktop Window]:::external
    IG[Instagram Login Page]:::external
    YTDL[yt-dlp Downloader]:::local
    Whisper[Local Whisper Engine]:::local
    Chroma[(ChromaDB Vector Store)]:::local
    Gemini[Gemini LLM (with Fallbacks)]:::external

    %% Relations
    UI -->|Connects Instagram| API
    API -->|Spawns Browser| Sel
    Sel -->|Manual User Log In| IG
    IG -->|Returns Cookie Sessions| API
    UI -->|Ingests Video URLs| API
    API -->|Downloads Audio| YTDL
    YTDL -->|Transcribes Audio| Whisper
    Whisper -->|Stores Chunks + Metadata| Chroma
    UI -->|Sends Chats| API
    API -->|Queries Context| Chroma
    API -->|Generates Answer| Gemini
    Gemini -->|Streams Tokens| UI
```

---

## 🔒 Selenium Instagram Authentication Flow

Due to Instagram's aggressive bot protection on password input fields, our backend launches a standard desktop Chrome/Edge browser window on the host. 

```
[User clicks Connect] -> [FastAPI returns loading screen popup]
                                 ↓
                     [Selenium launches on Host Desktop]
                                 ↓
                 [User logs in directly on Instagram]
                                 ↓
               [FastAPI detects session, caches cookies]
                                 ↓
                  [Popup closes automatically]
```
This guarantees authentication success without triggering Instagram's account blocks, and translates the active session file directly to Netscape format for `yt-dlp` extraction.

---

## 🚀 Getting Started

### Prerequisites
*   Python 3.10+
*   Node.js 18+
*   Google Chrome or Microsoft Edge installed on the host system

### 1. Configure the Backend

1.  Navigate to the backend directory:
    ```bash
    cd backend
    ```
2.  Create a virtual environment and activate it:
    ```bash
    python -m venv venv
    # On Windows:
    venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```
3.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Create a `.env` file in the `backend` folder:
    ```env
    GOOGLE_API_KEY=your_gemini_api_key_here
    GEMINI_MODEL=gemini-2.0-flash
    ```
5.  Start the FastAPI backend server:
    ```bash
    python main.py
    ```
    The server will start running on `http://localhost:8000`.

### 2. Configure the Frontend

1.  Navigate to the frontend directory:
    ```bash
    cd ../frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Start the development server:
    ```bash
    npm run dev
    ```
4.  Open your browser and navigate to `http://localhost:5173`. Alternatively, access `http://localhost:8000` to run the fully compiled production build.

---

## 📂 Project Structure

```text
creator-iq/
├── backend/
│   ├── main.py                # FastAPI endpoints & static routing
│   ├── ingest.py              # Selenium login, Whisper transcribing, and audio parsing
│   ├── rag_pipeline.py        # LangGraph workflow & Gemini fallback selection
│   ├── requirements.txt       # Backend dependencies
│   ├── .env                   # Local configuration (ignored by git)
│   └── .env.example           # Shared placeholder configuration
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Core dashboard shell
│   │   ├── index.css          # Styling system & dark mode tokens
│   │   └── components/
│   │       ├── VideoCard.jsx  # Ingested video cards & engagement statistics
│   │       ├── ChatPanel.jsx  # Real-time streaming conversation container
│   │       └── Citation.jsx   # Source citations mapping back to transcripts
│   └── ...
└── README.md                  # Detailed documentation
```
