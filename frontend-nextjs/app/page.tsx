'use client'

import { useState, useEffect, useRef } from 'react'
import ChatInterface from './components/ChatInterface'
import DatabaseAdmin from './components/DatabaseAdmin'

export default function Home() {
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    setTimeout(() => setIsLoading(false), 1000)
  }, [])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <div className="text-center">
          <div className="inline-flex items-center space-x-1 mb-4">
            <div className="w-3 h-3 bg-black rounded-full animate-bounce" style={{animationDelay: '0ms'}}></div>
            <div className="w-3 h-3 bg-black rounded-full animate-bounce" style={{animationDelay: '150ms'}}></div>
            <div className="w-3 h-3 bg-black rounded-full animate-bounce" style={{animationDelay: '300ms'}}></div>
          </div>
          <p className="text-black font-mono">Initializing HealthTriage System...</p>
        </div>
      </div>
    )
  }

  return (
    <main className="min-h-screen bg-white">
      <div className="max-w-full mx-auto p-4">
        {/* Header */}
        <header className="border-b-2 border-black pb-4 mb-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold tracking-tight font-mono">HealthTriage Assistant</h1>
              <p className="text-gray-600 mt-1 font-mono text-sm">AI-Powered Medical Triage System v1.0</p>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-right">
                <p className="text-sm font-mono text-gray-600">STATUS</p>
                <p className="text-sm font-bold">ONLINE</p>
              </div>
              <div className="w-3 h-3 bg-black rounded-full animate-pulse"></div>
            </div>
          </div>
        </header>

        {/* Split Layout */}
        <div className="grid grid-cols-2 gap-6 h-[calc(100vh-200px)]">
          {/* Left: Chat Interface */}
          <div className="overflow-hidden">
            <ChatInterface />
          </div>

          {/* Right: Database Admin */}
          <div className="overflow-hidden">
            <DatabaseAdmin />
          </div>
        </div>

        {/* Footer */}
        <footer className="mt-8 pt-4 border-t border-gray-300 text-center">
          <p className="text-xs text-gray-600 font-mono">
            HIPAA Compliant | Secure Connection | Emergency: Call 911
          </p>
        </footer>
      </div>
    </main>
  )
}