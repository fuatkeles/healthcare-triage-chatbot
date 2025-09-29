'use client'

export default function TypingIndicator() {
  return (
    <div className="flex justify-start mb-2">
      <div className="chat-bubble chat-bubble-bot max-w-[100px]">
        <div className="flex items-center space-x-2">
          <div className="flex-shrink-0">
            <div className="w-8 h-8 border-2 border-black bg-white flex items-center justify-center font-mono text-xs">
              AI
            </div>
          </div>
          <div className="typing-indicator">
            <div className="typing-dot animate-typing"></div>
            <div className="typing-dot animate-typing" style={{animationDelay: '200ms'}}></div>
            <div className="typing-dot animate-typing" style={{animationDelay: '400ms'}}></div>
          </div>
        </div>
      </div>
    </div>
  )
}