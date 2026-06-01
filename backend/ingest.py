import re, json, os, logging, subprocess, tempfile
from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp, whisper, instaloader
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

logging.basicConfig(level=logging.INFO)

embed_model = SentenceTransformer("all-MiniLM-L6-v2")
db_client = PersistentClient(path="./chroma_db")
collection = db_client.get_or_create_collection("video_chunks")

def get_db():
    return collection

def clean_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50):
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        chunk = " ".join(words[start:start+chunk_size])
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

def extract_youtube_id(url: str) -> str:
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11})(?:[?&/]|$)",
        r"youtu\.be\/([0-9A-Za-z_-]{11})(?:[?&/]|$)",
        r"embed\/([0-9A-Za-z_-]{11})",
        r"shorts\/([0-9A-Za-z_-]{11})"
    ]
    for p in patterns:
        match = re.search(p, url)
        if match:
            return match.group(1)
    raise ValueError("Invalid YouTube URL")

def get_youtube_auto_captions(url: str) -> str:
    """Use yt-dlp to fetch auto-generated captions (English) without downloading video."""
    with tempfile.TemporaryDirectory() as tmpdir:
        outtmpl = os.path.join(tmpdir, '%(id)s')
        ydl_opts = {
            'writeautomaticsub': True,
            'subtitleslangs': ['en'],
            'skip_download': True,
            'outtmpl': outtmpl,
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        # Find the generated .vtt file
        for f in os.listdir(tmpdir):
            if f.endswith('.en.vtt'):
                with open(os.path.join(tmpdir, f), 'r', encoding='utf-8') as fp:
                    content = fp.read()
                # Remove VTT headers and timestamps, keep text lines
                lines = []
                for line in content.splitlines():
                    if '-->' in line or line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:') or line.strip().isdigit():
                        continue
                    if line.strip():
                        lines.append(line.strip())
                return ' '.join(lines)
        raise RuntimeError('No auto-captions found')

def get_youtube_transcript(url: str) -> str:
    video_id = extract_youtube_id(url)
    # Try official transcript API first
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        try:
            transcript = transcript_list.find_transcript(['en'])
        except Exception:
            # Fallback to the first available transcript
            transcript = next(iter(transcript_list))
        
        if transcript.language_code != 'en':
            transcript = transcript.translate('en')
            
        data = transcript.fetch()
        return " ".join([entry.text for entry in data])
    except Exception as e:
        logging.warning(f"Transcript API failed ({e}), trying auto-captions via yt-dlp...")
        try:
            return get_youtube_auto_captions(url)
        except Exception as e2:
            raise RuntimeError(f"Could not get transcript: {e2}")

def transcribe_audio(url: str, cookiefile: str = None) -> str:
    """Download audio (for Instagram) and transcribe with Whisper."""
    audio_path = "temp_audio"
    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best[ext=webm]/best[ext=mp4]/best",
        "outtmpl": f"{audio_path}.%(ext)s",
        "quiet": True,
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}],
        "ignoreerrors": True,
    }
    if cookiefile:
        ydl_opts["cookiefile"] = cookiefile
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    final_audio = "temp_audio.mp3"
    if not os.path.exists(final_audio):
        raise FileNotFoundError(f"Could not download/extract audio for {url}. The video may be restricted or have no audio stream.")
    try:
        model = whisper.load_model("base")
        result = model.transcribe(final_audio)
        transcript = result["text"]
    finally:
        if os.path.exists(final_audio):
            try:
                os.remove(final_audio)
            except Exception:
                pass
    return transcript

def run_interactive_instagram_login(username: str, browser_type: str = "chrome") -> dict:
    driver = None
    
    if browser_type == "edge":
        try:
            from selenium.webdriver.edge.service import Service as EdgeService
            from webdriver_manager.microsoft import EdgeChromiumDriverManager
            from selenium.webdriver.edge.options import Options as EdgeOptions
            
            options = EdgeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--window-size=500,700")
            
            logging.info("Starting visible Edge for manual Instagram login...")
            service = EdgeService(EdgeChromiumDriverManager().install())
            driver = webdriver.Edge(service=service, options=options)
        except Exception as e:
            logging.warning(f"Failed to start Edge driver ({e}). Falling back to Chrome...")
            browser_type = "chrome"
            
    if browser_type == "chrome" or driver is None:
        options = webdriver.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=500,700")
        
        logging.info("Starting visible Chrome for manual Instagram login...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
    try:
        driver.get("https://www.instagram.com/accounts/login/")
        
        cookies_dict = {}
        # Wait up to 3 minutes
        for _ in range(180):
            time.sleep(1)
            
            # Detect manual browser window closure
            try:
                _ = driver.title
            except Exception:
                logging.info("Selenium browser window was closed by the user.")
                break
                
            current_cookies = driver.get_cookies()
            if any(c['name'] == 'sessionid' for c in current_cookies):
                cookies_dict = {c['name']: c['value'] for c in current_cookies}
                break
                
        if not cookies_dict:
            raise ValueError("Instagram login was not completed or the browser was closed.")
            
        L = instaloader.Instaloader()
        session_file = os.path.join(tempfile.gettempdir(), f"instaloader_session_{username}")
        L.load_session(username, cookies_dict)
        L.save_session_to_file(filename=session_file)
        logging.info(f"Instaloader session cached successfully for username: {username}")
        
        return cookies_dict
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

def write_netscape_cookie_file_from_dict(cookies_dict: dict, filepath: str):
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("# Netscape HTTP Cookie File\n")
        f.write("# This file is generated by CreatorIQ. Do not edit.\n\n")
        expiry = int(time.time() + 30 * 24 * 3600) # 30 days from now
        for name, value in cookies_dict.items():
            f.write(f".instagram.com\tTRUE\t/\tTRUE\t{expiry}\t{name}\t{value}\n")

def get_instagram_info_via_instaloader(url: str, username: str) -> tuple[dict, dict]:
    shortcode_match = re.search(r"instagram\.com/(?:reel|p)/([A-Za-z0-9_-]+)", url)
    if not shortcode_match:
        raise ValueError("Invalid Instagram Reel/Post URL format")
    shortcode = shortcode_match.group(1)
    
    L = instaloader.Instaloader()
    session_file = os.path.join(tempfile.gettempdir(), f"instaloader_session_{username}")
    
    import sys, builtins, getpass
    orig_input = builtins.input
    orig_stdin = sys.stdin
    orig_getpass = getpass.getpass
    
    class NonInteractiveStdin:
        def read(self, *args, **kwargs):
            raise EOFError("Interactive input is disabled.")
        def readline(self, *args, **kwargs):
            raise EOFError("Interactive input is disabled.")
        def isatty(self):
            return False
            
    def non_interactive_input(prompt=""):
        raise EOFError("Interactive input is disabled.")
        
    def non_interactive_getpass(prompt="", stream=None):
        raise EOFError("Interactive input is disabled.")
        
    builtins.input = non_interactive_input
    sys.stdin = NonInteractiveStdin()
    getpass.getpass = non_interactive_getpass
    
    try:
        if not os.path.exists(session_file):
            raise ValueError(f"No active Instagram session found for @{username}. Please connect Instagram first.")
            
        try:
            L.load_session_from_file(username, filename=session_file)
            logging.info("Instaloader session loaded successfully from cache.")
        except Exception as e:
            raise ValueError(f"Instagram session expired or invalid: {str(e)}. Please reconnect your account.")
            
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        profile = post.owner_profile
        hashtags = list(post.caption_hashtags)[:5]
        
        metadata = {
            "likes": post.likes or 0,
            "comments": post.comments or 0,
            "views": post.video_view_count or 0,
            "creator": profile.username,
            "follower_count": profile.followers or 0,
            "hashtags": hashtags,
            "upload_date": str(post.date.date()).replace("-", ""),
            "duration": post.video_duration or 0
        }
        return metadata, L.context._session.cookies.get_dict()
    finally:
        builtins.input = orig_input
        sys.stdin = orig_stdin
        getpass.getpass = orig_getpass

def get_instagram_info(
    url: str, 
    username: str = None, 
    password: str = None,
    sessionid: str = None,
    csrftoken: str = None
) -> dict:
    active_user = username or os.environ.get("INSTAGRAM_USERNAME")
    
    if not active_user:
        raise ValueError("Instagram username is mandatory to ingest Reel metrics.")
        
    try:
        metadata, cookies_dict = get_instagram_info_via_instaloader(url, active_user)
    except Exception as e:
        err_msg = str(e)
        logging.error(f"Instaloader fetch failed: {err_msg}")
        raise ValueError(
            f"Instagram fetch failed: {err_msg}. "
            "Please reconnect your Instagram account in the app."
        )
        
    cookiefile_path = None
    try:
        fd, cookiefile_path = tempfile.mkstemp(suffix=".txt", prefix="ig_cookies_")
        os.close(fd)
        write_netscape_cookie_file_from_dict(cookies_dict, cookiefile_path)
        
        logging.info(f"Downloading/transcribing audio with temporary cookies: {cookiefile_path}")
        transcript = transcribe_audio(url, cookiefile=cookiefile_path)
    except Exception as e:
        logging.error(f"Failed to transcribe Instagram Reel audio: {e}")
        raise RuntimeError(f"Failed to transcribe Instagram Reel audio: {str(e)}")
    finally:
        if cookiefile_path and os.path.exists(cookiefile_path):
            try:
                os.remove(cookiefile_path)
            except Exception:
                pass
                
    return {
        "transcript": transcript,
        "metadata": metadata
    }

def get_youtube_info(url: str) -> dict:
    # 1. Try transcript, raising error if it fails
    try:
        transcript = get_youtube_transcript(url)
    except Exception as e:
        logging.error(f"Failed to get YouTube transcript: {e}")
        raise RuntimeError(f"Failed to get YouTube transcript: {str(e)}")

    # 2. Try metadata, raising error if it fails
    try:
        ydl_opts = {"quiet": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        likes = info.get("like_count", 0) or 0
        comments = info.get("comment_count", 0) or 0
        views = info.get("view_count", 0) or 0
        uploader = info.get("uploader", "unknown")
        follower_count = info.get("channel_follower_count") or info.get("uploader_follower_count") or info.get("subscriber_count") or 0
        hashtags = info.get("tags", []) or []
        upload_date = info.get("upload_date", "")
        duration = info.get("duration", 0) or 0
    except Exception as e:
        logging.error(f"Failed to extract YouTube metadata: {e}")
        raise RuntimeError(f"Failed to extract YouTube metadata: {str(e)}")

    return {
        "transcript": transcript,
        "metadata": {
            "likes": likes,
            "comments": comments,
            "views": views,
            "creator": uploader,
            "follower_count": follower_count,
            "hashtags": hashtags,
            "upload_date": upload_date,
            "duration": duration
        }
    }

def compute_engagement(metadata: dict) -> float:
    likes = metadata.get("likes", 0) or 0
    comments = metadata.get("comments", 0) or 0
    views = metadata.get("views", 0) or 0
    if views <= 0 or views < (likes + comments):
        if likes > 0:
            views = int(likes * 25)
        else:
            views = 1
    return round((likes + comments) / views * 100, 2)

def ingest_video(
    url: str, 
    video_id: str, 
    instagram_username: str = None, 
    instagram_password: str = None,
    instagram_sessionid: str = None,
    instagram_csrftoken: str = None
):
    if "youtube.com" in url or "youtu.be" in url:
        data = get_youtube_info(url)
    elif "instagram.com" in url:
        data = get_instagram_info(
            url, 
            instagram_username, 
            instagram_password, 
            instagram_sessionid, 
            instagram_csrftoken
        )
    else:
        raise ValueError("Unsupported URL")
    metadata = data["metadata"]
    metadata["engagement_rate"] = compute_engagement(metadata)
    transcript = data["transcript"]
    
    # Prepare metadata for ChromaDB by stringifying non-primitive lists (like hashtags)
    db_metadata = {}
    for k, v in metadata.items():
        if isinstance(v, list):
            db_metadata[k] = ", ".join(v)
        else:
            db_metadata[k] = v
            
    chunks = chunk_text(clean_text(transcript))

    # Prepend metadata summary to every chunk so AI can answer metric questions
    meta_summary = f"""[Video {video_id} Stats]
Creator: {metadata.get('creator', 'unknown')}
Views: {metadata.get('views', 0)}
Likes: {metadata.get('likes', 0)}
Comments: {metadata.get('comments', 0)}
Followers: {metadata.get('follower_count', 0)}
Engagement Rate: {metadata.get('engagement_rate', 0)}%
Upload Date: {metadata.get('upload_date', '')}
Duration: {metadata.get('duration', 0)} seconds
Hashtags: {', '.join(metadata.get('hashtags', [])) if isinstance(metadata.get('hashtags'), list) else metadata.get('hashtags', '')}

[Transcript]
"""

    # Delete old chunks for this video ID to prevent overlap/leakage of previous runs
    try:
        collection.delete(where={"video_id": video_id})
        logging.info(f"Deleted existing chunks for {video_id} from ChromaDB.")
    except Exception as e:
        logging.warning(f"Could not delete existing chunks for {video_id}: {e}")

    for i, chunk in enumerate(chunks):
        enriched_chunk = meta_summary + chunk if i == 0 else chunk
        embedding = embed_model.encode(enriched_chunk).tolist()
        collection.upsert(
            embeddings=[embedding],
            documents=[enriched_chunk],
            metadatas=[{**db_metadata, "chunk_index": i, "video_id": video_id}],
            ids=[f"{video_id}_chunk_{i}"]
        )
    with open(f"{video_id}_metadata.json", "w") as f:
        json.dump(metadata, f)
        
    return metadata