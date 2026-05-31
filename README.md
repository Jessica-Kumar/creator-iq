An AI-powered RAG chatbot that compares two social media videos (YouTube + Instagram Reel) by ingesting transcripts, metadata, and engagement metrics. Built with LangGraph, FastAPI, Gemini (free tier), and ChromaDB.

## Features

- Input two video URLs (YouTube and Instagram Reel)
- Auto-extract transcripts and metadata (views, likes, comments, creator, follower count, hashtags, upload date, duration)
- Compute engagement rate: (likes + comments) / views × 100
- Chunk transcripts (500 tokens, 50 overlap) and store embeddings in ChromaDB
- Stream answers with source citations (video + chunk index)
- Maintain conversation history across turns

## Tech Stack

- **Frontend**: React (Vite) + Tailwind CSS
- **Backend**: FastAPI + LangGraph
- **LLM**: Gemini 1.5 Flash (free tier, streaming)
- **Embeddings**: all-MiniLM-L6-v2 (local, free)
- **Vector DB**: ChromaDB (persistent, zero-cost)
- **Transcription**: youtube-transcript-api + Whisper (base)

## Why this stack?

| Choice | Reason |
|--------|--------|
| Gemini 1.5 Flash | Free 15 req/min, excellent streaming quality |
| all-MiniLM-L6-v2 | 384-dim, fast CPU inference, no API cost |
| ChromaDB | Single-binary, 10ms queries, handles 10k+ chunks easily |
| 500-token chunks | Best balance for hook analysis and precise retrieval |
| LangGraph | Native streaming, memory, minimal boilerplate |
| FastAPI | Async, SSE streaming out-of-the-box |

## Scalability

- At 1,000 creators/day (~2,000 videos), ChromaDB runs on a $20/month VM.
- Embeddings and transcription run locally → zero API cost.
- Gemini free tier covers chat requests.
- For millions of users, swap ChromaDB to Qdrant Cloud (same API) and LLM to Groq/Llama (80% cheaper).

## Getting Started

1. Get a [free Gemini API key](https://aistudio.google.com/apikey)
2. Clone the repo
3. **Backend**:
cd backend
python -m venv venv
source venv/Scripts/activate # or venv/bin/activate
pip install -r requirements.txt
echo 'GOOGLE_API_KEY=your-key' > .env
python main.py

text
4. **Frontend**:
cd frontend
npm install
npm run dev

text
5. Open http://localhost:5173

## Environment Variables

- `GOOGLE_API_KEY` – Gemini API key (mandatory)

## Project Structure
creator-iq/
├── backend/
│ ├── main.py
│ ├── ingest.py
│ ├── rag_pipeline.py
│ ├── requirements.txt
│ └── .env.example
├── frontend/
│ ├── src/
│ │ ├── App.jsx
│ │ └── components/
│ │ ├── VideoCard.jsx
│ │ ├── ChatPanel.jsx
│ │ └── Citation.jsx
│ └── ...
└── README.md

