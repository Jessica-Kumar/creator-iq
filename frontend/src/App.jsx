import { useState } from 'react'
import VideoCard from './components/VideoCard'
import ChatPanel from './components/ChatPanel'

export default function App() {
  const [urlA, setUrlA] = useState('')
  const [urlB, setUrlB] = useState('')
  
  // Instagram connection state persisted in browser localStorage
  const [isLoggedIn, setIsLoggedIn] = useState(() => localStorage.getItem('insta_connected') === 'true')
  
  const [sessionId, setSessionId] = useState(null)
  const [metadata, setMetadata] = useState(null)
  const [loading, setLoading] = useState(false)
  const [connecting, setConnecting] = useState(false)

  const handleLogin = (e) => {
    e.preventDefault()
    setConnecting(true)
    const width = 500
    const height = 700
    const left = (window.screen.width - width) / 2
    const top = (window.screen.height - height) / 2
    
    const popup = window.open(
      '/api/instagram/login-popup',
      'Instagram Login',
      `width=${width},height=${height},left=${left},top=${top}`
    )
    
    const interval = setInterval(async () => {
      if (!popup || popup.closed) {
        clearInterval(interval)
        setConnecting(false)
        try {
          const res = await fetch('/api/instagram/status')
          const data = await res.json()
          if (data.logged_in) {
            localStorage.setItem('insta_connected', 'true')
            setIsLoggedIn(true)
          } else {
            alert('Instagram connection failed or was cancelled.')
          }
        } catch (e) {
          console.error(e)
          alert('Error checking connection status: ' + e.message)
        }
      }
    }, 1000)
  }

  const handleLogout = async () => {
    try {
      await fetch('/api/instagram/logout')
    } catch (e) {
      console.error('Logout failed:', e)
    }
    localStorage.removeItem('insta_connected')
    setIsLoggedIn(false)
  }

  const ingest = async () => {
    if (!urlA.trim() || !urlB.trim()) {
      alert('Please fill in both video URLs')
      return
    }
    setLoading(true)
    try {
      const res = await fetch('/api/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          urls: [urlA, urlB],
          instagram_username: 'instagram_user'
        })
      })
      const data = await res.json()
      if (res.ok) {
        setSessionId(data.session_id)
        setMetadata(data.metadata)
      } else {
        alert(data.detail || 'Failed to ingest and process videos. Please make sure the URLs are correct.')
      }
    } catch (e) {
      console.error(e)
      alert('Network error while processing videos: ' + e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col font-sans">
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50 p-4 flex justify-between items-center px-8">
        <div className="flex items-center gap-2">
          <span className="text-2xl font-black bg-gradient-to-r from-violet-500 to-fuchsia-500 bg-clip-text text-transparent tracking-wider">
            CreatorIQ
          </span>
          <span className="text-xs bg-violet-500/20 text-violet-300 border border-violet-500/30 px-2 py-0.5 rounded-full font-semibold">
            RAG Analyser v1.0
          </span>
        </div>
        <div className="text-sm text-slate-400 font-medium">
          Compare YouTube & Instagram Reels
        </div>
      </header>

      {!sessionId ? (
        <div className="flex-1 flex flex-col items-center justify-center p-8 max-w-4xl mx-auto w-full">
          {!isLoggedIn ? (
            /* Mandatory Login Screen */
            <div className="max-w-md w-full flex flex-col items-center">
              <div className="text-center mb-8">
                <span className="inline-flex items-center justify-center p-3.5 bg-gradient-to-br from-fuchsia-500/10 to-violet-500/10 border border-violet-500/20 rounded-2xl mb-4 shadow-inner">
                  <svg className="w-8 h-8 text-fuchsia-400" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                    <rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect>
                    <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path>
                    <line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line>
                  </svg>
                </span>
                <h2 className="text-3xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-white to-slate-400 mb-2">
                  Connect Instagram
                </h2>
                <p className="text-slate-450 text-sm max-w-sm mx-auto leading-relaxed">
                  Interactive authentication is required to connect your Instagram account securely on Instagram's actual site.
                </p>
              </div>

              <form onSubmit={handleLogin} className="w-full bg-slate-955/50 border border-slate-800/80 rounded-2xl p-6 shadow-2xl backdrop-blur-md space-y-4">
                <div className="flex gap-2.5 p-3 rounded-lg bg-violet-500/10 border border-violet-500/20 text-violet-200/90 text-xs leading-relaxed">
                  <svg className="w-5 h-5 flex-shrink-0 text-violet-450 mt-0.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                    <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                  </svg>
                  <span>
                    We do not store or transmit your password. You will log in directly on Instagram's official login window.
                  </span>
                </div>

                <button 
                  type="submit"
                  disabled={connecting}
                  className="w-full mt-2 bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white font-bold p-3.5 rounded-xl shadow-lg hover:from-violet-500 hover:to-fuchsia-500 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed hover:-translate-y-0.5 active:translate-y-0"
                >
                  {connecting ? 'Waiting for login window...' : 'Connect Instagram'}
                </button>
              </form>
            </div>
          ) : (
            /* Main Ingestion Controls */
            <>
              <div className="text-center mb-8">
                <h2 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-white to-slate-400 mb-3">
                  Analyse Content Performance with RAG
                </h2>
                <p className="text-slate-400 max-w-xl mx-auto text-base">
                  Paste a YouTube video/Short URL and an Instagram Reel URL. Our system will extract the transcripts, scrape engagement metrics, and set up a stateful LLM chatbot to compare them.
                </p>
              </div>

              <div className="w-full max-w-2xl bg-slate-950/40 border border-slate-800/80 rounded-2xl p-6 shadow-2xl backdrop-blur-md space-y-5">
                {/* Active Session / Logout Panel */}
                <div className="flex items-center justify-between p-3.5 rounded-xl bg-emerald-500/5 border border-emerald-500/10 text-slate-300">
                  <div className="flex items-center gap-2.5">
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                    </span>
                    <span className="text-xs font-semibold">
                      Instagram Status: <strong className="text-emerald-400 font-bold">Connected</strong>
                    </span>
                  </div>
                  <button 
                    onClick={handleLogout}
                    className="flex items-center gap-1 text-[11px] text-rose-450 hover:text-rose-400 bg-rose-500/10 hover:bg-rose-500/15 border border-rose-500/20 px-2.5 py-1.5 rounded-lg font-bold transition-all"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                      <polyline points="16 17 21 12 16 7"></polyline>
                      <line x1="21" y1="12" x2="9" y2="12"></line>
                    </svg>
                    Logout
                  </button>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-slate-300 mb-2">Video A: YouTube Video / Short</label>
                  <input 
                    placeholder="https://www.youtube.com/watch?v=... or https://youtube.com/shorts/..." 
                    className="w-full p-3.5 bg-slate-900/60 border border-slate-800 rounded-xl focus:border-violet-500/60 focus:ring-1 focus:ring-violet-500/60 outline-none text-slate-200 transition-all placeholder:text-slate-600"
                    value={urlA} 
                    onChange={e => setUrlA(e.target.value)} 
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-semibold text-slate-300 mb-2">Video B: Instagram Reel</label>
                  <input 
                    placeholder="https://www.instagram.com/reel/... or https://www.instagram.com/p/..." 
                    className="w-full p-3.5 bg-slate-900/60 border border-slate-800 rounded-xl focus:border-violet-500/60 focus:ring-1 focus:ring-violet-500/60 outline-none text-slate-200 transition-all placeholder:text-slate-600"
                    value={urlB} 
                    onChange={e => setUrlB(e.target.value)} 
                  />
                </div>

                <button 
                  onClick={ingest} 
                  disabled={loading}
                  className="w-full mt-4 bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white font-bold p-4 rounded-xl shadow-lg hover:from-violet-500 hover:to-fuchsia-500 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed hover:-translate-y-0.5 active:translate-y-0"
                >
                  {loading ? (
                    <span className="flex items-center justify-center gap-2">
                      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Processing and Transcribing Videos...
                    </span>
                  ) : 'Analyse & Compare'}
                </button>
              </div>
            </>
          )}
        </div>
      ) : (
        /* Results View */
        <div className="flex-1 flex flex-col lg:flex-row gap-6 p-6 max-h-[calc(100vh-73px)] overflow-hidden">
          <div className="lg:w-1/2 flex flex-col gap-6 overflow-y-auto pr-2 custom-scrollbar">
            <VideoCard data={metadata?.video_0} label="Video A (YouTube)" isYouTube={true} />
            <VideoCard data={metadata?.video_1} label="Video B (Instagram)" isYouTube={false} />
          </div>
          <div className="lg:w-1/2 h-full flex flex-col border border-slate-800 bg-slate-950/30 rounded-2xl overflow-hidden shadow-xl">
            <ChatPanel sessionId={sessionId} />
          </div>
        </div>
      )}
    </div>
  )
}
