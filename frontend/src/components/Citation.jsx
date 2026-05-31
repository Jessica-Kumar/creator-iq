export default function Citation({ video, chunk, text }) {
  const isVideoA = video.toLowerCase().includes('a') || video.includes('0')
  return (
    <span 
      className={`inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full cursor-help transition-all ${
        isVideoA 
          ? 'bg-rose-500/10 text-rose-300 border border-rose-500/20 hover:bg-rose-500/25' 
          : 'bg-fuchsia-500/10 text-fuchsia-300 border border-fuchsia-500/20 hover:bg-fuchsia-500/25'
      }`}
      title={text}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${isVideoA ? 'bg-rose-400' : 'bg-fuchsia-400'}`}></span>
      {isVideoA ? 'Video A' : 'Video B'} · Ch{chunk}
    </span>
  )
}
