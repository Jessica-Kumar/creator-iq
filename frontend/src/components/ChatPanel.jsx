import { useState, useRef, useEffect } from 'react'
import Citation from './Citation'

export default function ChatPanel({ sessionId }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const chatEndRef = useRef(null)

  useEffect(() => { 
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }) 
  }, [messages])

  const suggestions = [
    "Why did Video A get more engagement than Video B?",
    "What's the engagement rate of each?",
    "Compare the hooks in the first 5 seconds.",
    "Who's the creator of Video B and what's their follower count?",
    "Suggest improvements for B based on what worked in A."
  ]

  const formatMessageContent = (content) => {
    if (!content) return null

    // Split by citations: [video_0 chunk 1] or similar
    const parts = []
    const regex = /\[(video_[01]|video_A|video_B) chunk (\d+)\]/g
    let lastIndex = 0
    let match

    while ((match = regex.exec(content)) !== null) {
      const matchIndex = match.index
      if (matchIndex > lastIndex) {
        parts.push(content.substring(lastIndex, matchIndex))
      }
      const video = match[1]
      const chunk = match[2]
      parts.push(
        <Citation
          key={matchIndex}
          video={video}
          chunk={chunk}
          text={`Source chunk ${chunk} from ${video}`}
        />
      )
      lastIndex = regex.lastIndex
    }

    if (lastIndex < content.length) {
      parts.push(content.substring(lastIndex))
    }

    const renderTextWithFormatting = (textOrArray) => {
      if (typeof textOrArray !== 'string') return textOrArray
      
      const lines = textOrArray.split('\n')
      return lines.map((line, idx) => {
        const isBullet = line.trim().startsWith('* ') || line.trim().startsWith('- ')
        let lineText = isBullet ? line.trim().substring(2) : line

        // Handle bold **text**
        const boldRegex = /\*\*(.*?)\*\*/g
        const elements = []
        let lastTextIndex = 0
        let boldMatch

        while ((boldMatch = boldRegex.exec(lineText)) !== null) {
          if (boldMatch.index > lastTextIndex) {
            elements.push(lineText.substring(lastTextIndex, boldMatch.index))
          }
          elements.push(
            <strong key={boldMatch.index} className="font-bold text-white bg-white/5 px-1 rounded">
              {boldMatch[1]}
            </strong>
          )
          lastTextIndex = boldRegex.lastIndex
        }
        if (lastTextIndex < lineText.length) {
          elements.push(lineText.substring(lastTextIndex))
        }

        if (isBullet) {
          return (
            <li key={idx} className="ml-4 list-disc pl-1 text-slate-300 my-1">
              {elements}
            </li>
          )
        }
        return (
          <p key={idx} className={line.trim() === '' ? 'h-3' : 'mb-2 text-slate-300 text-sm leading-relaxed'}>
            {elements}
          </p>
        )
      })
    }

    return parts.map((part, index) => {
      if (typeof part === 'string') {
        return <span key={index}>{renderTextWithFormatting(part)}</span>
      }
      return <span key={index} className="mx-1">{part}</span>
    })
  }

  const sendMessage = async (messageText) => {
    const textToSend = messageText || input
    if (!textToSend.trim() || streaming) return

    const userMsg = { role: 'user', content: textToSend }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setStreaming(true)

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: textToSend })
      })
      
      if (!response.body) {
        throw new Error('ReadableStream not supported')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let botContent = ''

      // Insert blank assistant message to stream into
      setMessages(prev => [...prev, { role: 'assistant', content: '' }])

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value)
        const lines = chunk.split('\n').filter(line => line.startsWith('data: '))
        for (const line of lines) {
          const jsonStr = line.replace('data: ', '')
          if (jsonStr === '[DONE]') break
          try {
            const data = JSON.parse(jsonStr)
            if (data.token) {
              botContent += data.token
              setMessages(prev => {
                const list = [...prev]
                const last = list[list.length - 1]
                if (last && last.role === 'assistant') {
                  last.content = botContent
                }
                return list
              })
            }
          } catch(e) {}
        }
      }
    } catch (e) {
      console.error(e)
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${e.message}. Please check backend logs.` }])
    } finally {
      setStreaming(false)
    }
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-950/20 px-6 py-4 flex items-center justify-between">
        <div>
          <h3 className="font-bold text-white text-base">Assistant Copilot</h3>
          <p className="text-xs text-slate-400">Ask questions and analyze hook structure</p>
        </div>
        <div className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${streaming ? 'bg-amber-400 animate-pulse' : 'bg-emerald-400'}`}></span>
          <span className="text-xs text-slate-400">{streaming ? 'Streaming' : 'Ready'}</span>
        </div>
      </div>

      {/* Message Container */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col justify-center items-center text-center px-4 space-y-6">
            <div className="bg-violet-500/10 border border-violet-500/20 w-12 h-12 rounded-xl flex items-center justify-center">
              <svg className="w-6 h-6 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
              </svg>
            </div>
            <div className="space-y-2">
              <h4 className="font-bold text-slate-200">Start Comparing Video Performance</h4>
              <p className="text-xs text-slate-400 max-w-sm">
                Click a suggested question below or write your own prompt to query the vector database and search details.
              </p>
            </div>
            
            <div className="w-full max-w-lg grid grid-cols-1 gap-2.5">
              {suggestions.map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => sendMessage(prompt)}
                  disabled={streaming}
                  className="w-full text-left p-3.5 bg-slate-950/40 hover:bg-slate-800/50 border border-slate-800/60 hover:border-slate-700/80 rounded-xl text-xs text-slate-300 font-medium transition-all hover:translate-x-1"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div 
                className={`max-w-[85%] px-4 py-3 rounded-2xl ${
                  msg.role === 'user' 
                    ? 'bg-violet-600 text-white rounded-br-none shadow-md shadow-violet-900/10' 
                    : 'bg-slate-950/50 border border-slate-800 text-slate-300 rounded-bl-none'
                }`}
              >
                {msg.role === 'user' ? (
                  <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                ) : (
                  <div className="space-y-1">
                    {formatMessageContent(msg.content)}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Input Form */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/20">
        <div className="flex gap-2.5">
          <input
            type="text" 
            value={input} 
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && sendMessage()}
            placeholder="Ask about hook comparisons, engagement rates, and improvement tips..." 
            className="flex-1 p-3 bg-slate-900/80 border border-slate-800 rounded-xl focus:border-violet-500/60 focus:ring-1 focus:ring-violet-500/60 outline-none text-slate-200 text-sm transition-all placeholder:text-slate-500"
            disabled={streaming} 
          />
          <button 
            onClick={() => sendMessage()} 
            disabled={streaming || !input.trim()}
            className="bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white px-5 rounded-xl font-bold text-sm shadow-md transition-all active:scale-95 flex items-center justify-center"
          >
            {streaming ? (
              <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            ) : 'Send'}
          </button>
        </div>
      </div>
    </div>
  )
}
