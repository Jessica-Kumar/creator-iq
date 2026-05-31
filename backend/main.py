from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncio, json, os, traceback, logging, tempfile
from dotenv import load_dotenv
load_dotenv()

from ingest import ingest_video, run_interactive_instagram_login
from rag_pipeline import create_rag_graph

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

sessions = {}

@app.get("/api/instagram/login-popup")
async def instagram_login_popup(background_tasks: BackgroundTasks, user_agent: str | None = Header(None)):
    browser_type = "chrome"
    if user_agent and "Edg/" in user_agent:
        browser_type = "edge"
        
    logging.info(f"Initiating interactive Instagram login popup using browser: {browser_type}")
    background_tasks.add_task(run_interactive_instagram_login, "instagram_user", browser_type)
    
    loading_html = """
    <html>
    <head>
        <title>Connecting Instagram</title>
        <style>
            body {
                background-color: #0f172a;
                color: #f8fafc;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
                text-align: center;
                overflow: hidden;
            }
            .card {
                background: #1e293b;
                padding: 40px;
                border-radius: 20px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
                max-width: 380px;
                border: 1px solid #334155;
                display: flex;
                flex-direction: column;
                align-items: center;
            }
            .spinner {
                width: 50px;
                height: 50px;
                border: 5px solid #334155;
                border-top: 5px solid #8b5cf6;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin-bottom: 25px;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            h2 {
                font-size: 22px;
                margin: 0 0 10px 0;
                font-weight: 800;
                background: linear-gradient(to right, #a78bfa, #ec4899);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            p {
                color: #94a3b8;
                font-size: 14px;
                line-height: 1.6;
                margin: 0 0 20px 0;
            }
            .badge {
                background: rgba(139, 92, 246, 0.1);
                color: #c084fc;
                border: 1px solid rgba(139, 92, 246, 0.2);
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
                margin-top: 15px;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="spinner" id="spinner"></div>
            <h2 id="title">Secure Connection</h2>
            <p id="desc">A separate browser window has been opened on your desktop. Please enter your credentials and log in there.</p>
            <div class="badge">Awaiting Authentication</div>
        </div>
        
        <script>
            const interval = setInterval(async () => {
                try {
                    const res = await fetch('/api/instagram/status');
                    const data = await res.json();
                    if (data.logged_in) {
                        clearInterval(interval);
                        
                        document.getElementById('spinner').style.display = 'none';
                        const title = document.getElementById('title');
                        title.innerText = 'Connected!';
                        title.style.background = 'linear-gradient(to right, #34d399, #059669)';
                        title.style.webkitBackgroundClip = 'text';
                        
                        document.getElementById('desc').innerText = 'Instagram account connected successfully. Closing window...';
                        
                        const badge = document.querySelector('.badge');
                        badge.innerText = 'Success';
                        badge.style.background = 'rgba(16, 185, 129, 0.1)';
                        badge.style.color = '#34d399';
                        badge.style.borderColor = 'rgba(16, 185, 129, 0.2)';
                        
                        setTimeout(() => {
                            window.close();
                        }, 1500);
                    }
                } catch (e) {
                    console.error("Status polling failed:", e);
                }
            }, 1000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=loading_html, status_code=200)

@app.get("/api/instagram/status")
def instagram_status():
    session_file = os.path.join(tempfile.gettempdir(), "instaloader_session_instagram_user")
    logged_in = os.path.exists(session_file)
    return {"logged_in": logged_in}

@app.get("/api/instagram/logout")
def instagram_logout():
    session_file = os.path.join(tempfile.gettempdir(), "instaloader_session_instagram_user")
    if os.path.exists(session_file):
        try:
            os.remove(session_file)
        except Exception:
            pass
    return {"logged_in": False}

class IngestRequest(BaseModel):
    urls: list[str]
    instagram_username: str | None = None
    instagram_password: str | None = None
    instagram_sessionid: str | None = None
    instagram_csrftoken: str | None = None

class ChatRequest(BaseModel):
    session_id: str
    message: str

@app.post("/ingest")
@app.post("/api/ingest")
async def ingest_videos(req: IngestRequest):
    if len(req.urls) != 2:
        raise HTTPException(400, "Exactly two URLs required")
    video_ids = []
    metadata_dict = {}
    for i, url in enumerate(req.urls):
        vid = f"video_{i}"
        try:
            metadata = await asyncio.to_thread(
                ingest_video, 
                url, 
                vid, 
                req.instagram_username, 
                req.instagram_password,
                req.instagram_sessionid,
                req.instagram_csrftoken
            )
            video_ids.append(vid)
            metadata_dict[vid] = metadata
        except Exception as e:
            raise HTTPException(400, f"Failed to ingest {url}: {str(e)}")
    session_id = "default"
    sessions[session_id] = {"video_ids": video_ids, "graph": create_rag_graph(), "history": []}
    return {"session_id": session_id, "video_ids": video_ids, "metadata": metadata_dict}

@app.post("/chat")
@app.post("/api/chat")
async def chat(req: ChatRequest):
    session = sessions.get(req.session_id)
    if not session:
        raise HTTPException(400, "Session not found")
    async def event_stream():
        graph = session["graph"]
        inputs = {"question": req.message, "history": session["history"], "video_ids": session["video_ids"]}
        final_answer = ""
        try:
            async for event in graph.astream_events(inputs, version="v2"):
                kind = event["event"]
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        final_answer += content
                        yield f"data: {json.dumps({'token': content})}\n\n"
                elif kind == "on_chain_end" and event["name"] == "generate_answer":
                    output = event["data"]["output"]
                    final = output.get("answer", "")
                    yield f"data: {json.dumps({'final': final})}\n\n"
            # Store memory history
            session["history"].append({"role": "user", "content": req.message})
            session["history"].append({"role": "assistant", "content": final_answer})
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "Quota" in err_msg or "ResourceExhausted" in err_msg:
                friendly_error = "\n\n**[System Alert]** Gemini API Quota Exceeded (429). The `GOOGLE_API_KEY` provided in the backend `.env` file has a daily limit of 0 or has reached its rate limit. Please update the `.env` file with a valid Google AI Studio API key."
            elif "404" in err_msg or "NotFound" in err_msg:
                friendly_error = f"\n\n**[System Alert]** Model not found (404). The model `gemini-2.0-flash` is not supported for your API key version. Error: {err_msg}"
            else:
                friendly_error = f"\n\n**[System Alert]** An error occurred while invoking the model: {err_msg}"
            yield f"data: {json.dumps({'token': friendly_error})}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")

if os.path.exists("../frontend/dist"):
    app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
