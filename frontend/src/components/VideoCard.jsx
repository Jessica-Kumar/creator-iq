export default function VideoCard({ data, label, isYouTube }) {
  if (!data) return null

  const formatDate = (dateStr) => {
    if (!dateStr || dateStr.length !== 8) return dateStr
    return `${dateStr.substring(0, 4)}-${dateStr.substring(4, 6)}-${dateStr.substring(6, 8)}`
  }

  const hashtagsArray = typeof data.hashtags === 'string' 
    ? data.hashtags.split(',').map(tag => tag.trim()).filter(Boolean)
    : Array.isArray(data.hashtags) ? data.hashtags : []

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl hover:border-slate-700/80 transition-all duration-300">
      <div className="flex justify-between items-start mb-5">
        <div>
          <span className={`text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded-md ${
            isYouTube 
              ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' 
              : 'bg-fuchsia-500/10 text-fuchsia-400 border border-fuchsia-500/20'
          }`}>
            {isYouTube ? 'YouTube Video' : 'Instagram Reel'}
          </span>
          <h2 className="text-xl font-bold text-white mt-2">{label}</h2>
        </div>
        <div className="text-right">
          <div className="text-sm text-slate-400">Engagement Rate</div>
          <div className={`text-2xl font-black ${
            data.engagement_rate > 5 ? 'text-emerald-400' : 'text-amber-400'
          }`}>
            {data.engagement_rate}%
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-6">
        <div className="bg-slate-950/40 border border-slate-800/50 rounded-xl p-3.5">
          <div className="text-xs text-slate-500 font-semibold mb-1 uppercase tracking-wide">Creator</div>
          <div className="text-sm font-bold text-slate-200 truncate" title={data.creator}>
            @{data.creator}
          </div>
        </div>
        <div className="bg-slate-950/40 border border-slate-800/50 rounded-xl p-3.5">
          <div className="text-xs text-slate-500 font-semibold mb-1 uppercase tracking-wide">
            {isYouTube ? 'Subscribers' : 'Followers'}
          </div>
          <div className="text-sm font-bold text-slate-200">
            {data.follower_count ? data.follower_count.toLocaleString() : 'N/A'}
          </div>
        </div>
        <div className="bg-slate-950/40 border border-slate-800/50 rounded-xl p-3.5">
          <div className="text-xs text-slate-500 font-semibold mb-1 uppercase tracking-wide">Views</div>
          <div className="text-sm font-bold text-slate-200">
            {data.views ? data.views.toLocaleString() : '0'}
          </div>
        </div>
        <div className="bg-slate-950/40 border border-slate-800/50 rounded-xl p-3.5">
          <div className="text-xs text-slate-500 font-semibold mb-1 uppercase tracking-wide">Likes</div>
          <div className="text-sm font-bold text-slate-200">
            {data.likes ? data.likes.toLocaleString() : '0'}
          </div>
        </div>
        <div className="bg-slate-950/40 border border-slate-800/50 rounded-xl p-3.5">
          <div className="text-xs text-slate-500 font-semibold mb-1 uppercase tracking-wide">Comments</div>
          <div className="text-sm font-bold text-slate-200">
            {data.comments ? data.comments.toLocaleString() : '0'}
          </div>
        </div>
        <div className="bg-slate-950/40 border border-slate-800/50 rounded-xl p-3.5">
          <div className="text-xs text-slate-500 font-semibold mb-1 uppercase tracking-wide">Duration</div>
          <div className="text-sm font-bold text-slate-200">
            {data.duration} seconds
          </div>
        </div>
      </div>

      <div className="flex flex-wrap justify-between items-center text-xs text-slate-500 border-t border-slate-800/60 pt-4 gap-2">
        <div>
          Published: <span className="text-slate-400 font-medium">{formatDate(data.upload_date)}</span>
        </div>
        {hashtagsArray.length > 0 && (
          <div className="flex flex-wrap gap-1.5 max-w-[70%] justify-end">
            {hashtagsArray.slice(0, 3).map((tag, idx) => (
              <span key={idx} className="bg-slate-800 text-slate-300 font-medium px-2 py-0.5 rounded text-[10px]">
                #{tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
