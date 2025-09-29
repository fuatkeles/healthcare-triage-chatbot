'use client'

interface Button {
  title: string
  payload: string
}

interface QuickRepliesProps {
  replies: Button[]
  onReplyClick: (payload: string, title: string) => void
}

export default function QuickReplies({ replies, onReplyClick }: QuickRepliesProps) {
  return (
    <div className="grid grid-cols-2 gap-2 mt-2 max-w-md">
      {replies.map((button, index) => (
        <button
          key={index}
          onClick={() => onReplyClick(button.payload, button.title)}
          className="quick-reply-btn font-mono text-xs px-3 py-2 text-center"
        >
          {button.title}
        </button>
      ))}
    </div>
  )
}