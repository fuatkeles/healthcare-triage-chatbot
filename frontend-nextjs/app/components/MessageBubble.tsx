'use client'

interface Message {
  id: string
  text: string
  sender: 'user' | 'bot'
  timestamp: Date
}

export default function MessageBubble({ message }: { message: Message }) {
  const isUser = message.sender === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-2`}>
      <div
        className={`w-full ${
          isUser
            ? 'chat-bubble chat-bubble-user'
            : 'chat-bubble chat-bubble-bot'
        }`}
      >
        <div className="flex items-start space-x-2">
          {!isUser && (
            <div className="flex-shrink-0 mt-1">
              <div className="w-8 h-8 border-2 border-black bg-white flex items-center justify-center font-mono text-xs">
                AI
              </div>
            </div>
          )}
          <div className="flex-1">
            <p className="whitespace-pre-wrap font-mono text-sm">{message.text}</p>
            <p className={`text-xs mt-2 ${isUser ? 'text-gray-300' : 'text-gray-500'} font-mono`}>
              {message.timestamp.toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit'
              })}
            </p>
          </div>
          {isUser && (
            <div className="flex-shrink-0 mt-1">
              <div className="w-8 h-8 border-2 border-white bg-black flex items-center justify-center font-mono text-xs text-white">
                U
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}