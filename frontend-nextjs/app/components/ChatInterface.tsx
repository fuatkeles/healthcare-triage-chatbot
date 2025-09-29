'use client'

import { useState, useRef, useEffect } from 'react'
import MessageBubble from './MessageBubble'
import QuickReplies from './QuickReplies'
import TypingIndicator from './TypingIndicator'
import AppointmentCalendar from './AppointmentCalendar'

interface Message {
  id: string
  text: string
  sender: 'user' | 'bot'
  timestamp: Date
  quickReplies?: Array<{
    title: string
    payload: string
  }>
}

interface RasaResponse {
  recipient_id: string
  text?: string
  buttons?: Array<{
    title: string
    payload: string
  }>
  custom?: any
}

interface Appointment {
  id: string
  date: string
  time: string
  doctor: string
  department?: string
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      text: 'HEALTHCARE TRIAGE SYSTEM\n\nConnecting to medical assistant...',
      sender: 'bot',
      timestamp: new Date()
    }
  ])
  const [inputMessage, setInputMessage] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'connecting'>('connecting')
  const [sessionId] = useState(`session_${Date.now()}`)
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [showAppointments, setShowAppointments] = useState(false)
  const [showCalendar, setShowCalendar] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    // Initialize conversation with Rasa
    initializeConversation()
  }, [])

  const initializeConversation = async () => {
    try {
      // Send initial message to Rasa
      const response = await fetch('http://localhost:5005/webhooks/rest/webhook', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sender: sessionId,
          message: '/greet'
        }),
      })

      if (response.ok) {
        const data: RasaResponse[] = await response.json()
        setConnectionStatus('connected')

        if (data && data.length > 0) {
          const botMessages = data.map((msg, index) => ({
            id: `init_${index}`,
            text: msg.text || 'Welcome! How can I help you today?',
            sender: 'bot' as const,
            timestamp: new Date(),
            quickReplies: msg.buttons
          }))

          setMessages(botMessages)
        }
      } else {
        // If Rasa is not running, show offline mode
        setConnectionStatus('disconnected')
        setMessages([{
          id: '1',
          text: 'HEALTHCARE TRIAGE SYSTEM\n\n⚠️ Backend not connected. Please ensure Rasa server is running.\n\nTo start Rasa:\n1. cd rasa-backend\n2. py -3.10 rasa_server.py',
          sender: 'bot',
          timestamp: new Date()
        }])
      }
    } catch (error) {
      console.error('Failed to connect to Rasa:', error)
      setConnectionStatus('disconnected')
      setMessages([{
        id: '1',
        text: 'HEALTHCARE TRIAGE SYSTEM\n\n⚠️ Cannot connect to backend.\n\nPlease start the Rasa server:\n1. cd rasa-backend\n2. py -3.10 rasa_server.py',
        sender: 'bot',
        timestamp: new Date()
      }])
    }
  }


  const handleSendMessage = async (text?: string) => {
    const messageText = text || inputMessage
    if (!messageText.trim()) return

    // Check for view appointments command and open panel instead
    if (messageText.toLowerCase().includes('view') && messageText.toLowerCase().includes('appointment')) {
      setShowAppointments(true)
      return
    }

    // Add user message to chat
    const userMessage: Message = {
      id: Date.now().toString(),
      text: messageText,
      sender: 'user',
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setIsTyping(true)

    try {
      // Send message to Rasa
      const response = await fetch('http://localhost:5005/webhooks/rest/webhook', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sender: sessionId,
          message: messageText
        }),
      })

      if (response.ok) {
        const data: RasaResponse[] = await response.json()

        // Process Rasa responses
        data.forEach((msg) => {
          // Check if appointment confirmed in the message
          if (msg.text?.includes('APPOINTMENT CONFIRMED')) {
            const confirmMatch = msg.text.match(/Confirmation: (HC\d+)/)
            const dateMatch = msg.text.match(/Date: (.+?)\n/)
            const doctorMatch = msg.text.match(/Doctor: (.+?)\n/)
            const departmentMatch = msg.text.match(/Department: (.+?)\n/)

            if (confirmMatch) {
              const [, time] = dateMatch?.[1]?.split(' at ') || ['', '']
              const date = dateMatch?.[1]?.split(' at ')[0] || ''

              const newAppointment: Appointment = {
                id: confirmMatch[1],
                date: date,
                time: time || '',
                doctor: doctorMatch?.[1] || 'Dr. Smith',
                department: departmentMatch?.[1] || ''
              }
              // Add new appointment to the list
              setAppointments(prev => [...prev, newAppointment])
            }
          }

          // Check if appointment rescheduled
          if (msg.text?.includes('APPOINTMENT RESCHEDULED')) {
            const confirmMatch = msg.text.match(/Confirmation: (HC\d+)/)
            const newTimeMatch = msg.text.match(/New time: (.+?)\n/)
            const doctorMatch = msg.text.match(/Doctor: (.+?)\n/)

            if (confirmMatch && newTimeMatch) {
              const [date, time] = newTimeMatch[1].split(' at ')
              const appointmentId = confirmMatch[1]

              // Update existing appointment
              setAppointments(prev => prev.map(apt =>
                apt.id === appointmentId
                  ? { ...apt, date, time: time || '', doctor: doctorMatch?.[1] || apt.doctor }
                  : apt
              ))
            }
          }

          // Check if appointment cancelled
          if (msg.text?.includes('APPOINTMENT CANCELLED')) {
            const idMatch = msg.text.match(/Confirmation: (HC\d+)/)
            if (idMatch) {
              setAppointments(prev => prev.filter(apt => apt.id !== idMatch[1]))
            }
          }
        })

        // Store button payloads for handling
        const buttonPayloadMap = new Map<string, string>()
        data.forEach((msg) => {
          if (msg.buttons) {
            msg.buttons.forEach(btn => {
              buttonPayloadMap.set(btn.title, btn.payload)
            })
          }
        })

        // Create button mapping for display vs payload
        const buttonData = data.flatMap(msg => msg.buttons || [])

        const botMessages = data.map((msg, index) => ({
          id: `${Date.now()}_${index}`,
          text: msg.text || '',
          sender: 'bot' as const,
          timestamp: new Date(),
          quickReplies: msg.buttons ? msg.buttons : undefined
        }))

        // Add bot messages to chat
        setMessages(prev => [...prev, ...botMessages])
        setConnectionStatus('connected')
      } else {
        // Error handling
        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          text: '⚠️ Failed to get response. Please check if Rasa server is running.',
          sender: 'bot',
          timestamp: new Date()
        }])
        setConnectionStatus('disconnected')
      }
    } catch (error) {
      console.error('Error sending message:', error)
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        text: '⚠️ Connection error. Please ensure Rasa server is running on port 5005.',
        sender: 'bot',
        timestamp: new Date()
      }])
      setConnectionStatus('disconnected')
    } finally {
      setIsTyping(false)
    }
  }

  const handleQuickReply = (replyPayload: string, replyTitle: string) => {
    // Check if it's the calendar button
    if (replyPayload === '/open_calendar') {
      setShowCalendar(true)
      return
    }

    // Check if it's view appointments button
    if (replyPayload === '/view_appointments') {
      setShowAppointments(true)
      return
    }

    // Display the title in chat, but send the payload to backend
    const userMessage: Message = {
      id: Date.now().toString(),
      text: replyTitle, // Show the button title, not the payload
      sender: 'user',
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setIsTyping(true)

    // Send the payload to backend
    fetch('http://localhost:5005/webhooks/rest/webhook', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        sender: sessionId,
        message: replyPayload // Send the payload
      }),
    })
    .then(response => response.json())
    .then((data: RasaResponse[]) => {
      // Process responses
      data.forEach((msg) => {
        if (msg.text?.includes('APPOINTMENT CONFIRMED')) {
          const confirmMatch = msg.text.match(/Confirmation: (HC\d+)/)
          const dateMatch = msg.text.match(/Date: (.+?)\n/)
          const doctorMatch = msg.text.match(/Doctor: (.+?)\n/)

          if (confirmMatch) {
            const [, time] = dateMatch?.[1]?.split(' at ') || ['', '']
            const date = dateMatch?.[1]?.split(' at ')[0] || ''

            const newAppointment: Appointment = {
              id: confirmMatch[1],
              date: date,
              time: time || '',
              doctor: doctorMatch?.[1] || 'Dr. Smith'
            }
            setAppointments(prev => [...prev, newAppointment])
          }
        }

        if (msg.text?.includes('APPOINTMENT RESCHEDULED')) {
          const confirmMatch = msg.text.match(/Confirmation: (HC\d+)/)
          const newTimeMatch = msg.text.match(/New time: (.+?)\n/)
          const doctorMatch = msg.text.match(/Doctor: (.+?)\n/)

          if (confirmMatch && newTimeMatch) {
            const [date, time] = newTimeMatch[1].split(' at ')
            const appointmentId = confirmMatch[1]

            setAppointments(prev => prev.map(apt =>
              apt.id === appointmentId
                ? { ...apt, date, time: time || '', doctor: doctorMatch?.[1] || apt.doctor }
                : apt
            ))
          }
        }

        if (msg.text?.includes('APPOINTMENT CANCELLED')) {
          const idMatch = msg.text.match(/Confirmation: (HC\d+)/)
          if (idMatch) {
            setAppointments(prev => prev.filter(apt => apt.id !== idMatch[1]))
          }
        }
      })

      const botMessages = data.map((msg, index) => ({
        id: `${Date.now()}_${index}`,
        text: msg.text || '',
        sender: 'bot' as const,
        timestamp: new Date(),
        quickReplies: msg.buttons
      }))

      setMessages(prev => [...prev, ...botMessages])
      setIsTyping(false)
      setConnectionStatus('connected')
    })
    .catch(error => {
      console.error('Error:', error)
      setIsTyping(false)
      setConnectionStatus('disconnected')
    })
  }

  const cancelAppointment = (aptId: string) => {
    setAppointments(prev => prev.filter(apt => apt.id !== aptId))
    handleSendMessage(`/cancel_apt_${aptId}`)
    setShowAppointments(false)
  }

  const handleCalendarSelect = (date: string, time: string) => {
    setShowCalendar(false)
    const appointmentMessage = `Book appointment for ${date} at ${time}`
    handleSendMessage(appointmentMessage)
  }

  return (
    <div className="flex gap-4">
      <div className="flex-1 flex flex-col h-[calc(100vh-200px)] max-w-5xl border-2 border-black bg-white">
        {/* Header */}
        <div className="flex justify-between items-center px-4 py-2 border-b-2 border-black bg-gray-50">
          <span className="text-sm font-mono font-bold">MEDICAL TRIAGE SYSTEM</span>
          <div className="flex items-center space-x-4">
            <button
              onClick={() => setShowAppointments(!showAppointments)}
              className="text-sm font-mono hover:underline"
            >
              MY APPOINTMENTS ({appointments.length})
            </button>
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${
                connectionStatus === 'connected' ? 'bg-green-600' :
                connectionStatus === 'connecting' ? 'bg-yellow-600 animate-pulse' :
                'bg-red-600'
              }`}></div>
              <span className="text-xs font-mono uppercase">
                {connectionStatus === 'connected' ? 'RASA CONNECTED' :
                 connectionStatus === 'connecting' ? 'CONNECTING...' :
                 'RASA OFFLINE'}
              </span>
            </div>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map(message => (
            <div key={message.id} className={message.sender === 'bot' ? 'flex flex-col items-start' : 'flex justify-end'}>
              <MessageBubble message={message} />
              {message.quickReplies && message.sender === 'bot' &&
               message.id === messages[messages.length - 1]?.id && (
                <QuickReplies
                  replies={message.quickReplies}
                  onReplyClick={handleQuickReply}
                />
              )}
            </div>
          ))}
          {isTyping && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t-2 border-black p-4 bg-gray-50">
          <form onSubmit={(e) => { e.preventDefault(); handleSendMessage(); }} className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder={connectionStatus === 'connected' ?
                "Describe your symptoms or type 'help'..." :
                "Waiting for Rasa connection..."}
              disabled={connectionStatus !== 'connected'}
              className="flex-1 px-4 py-3 border-2 border-black bg-white focus:outline-none focus:ring-2 focus:ring-black focus:ring-offset-2 font-mono disabled:bg-gray-100 disabled:text-gray-500"
            />
            <button
              type="submit"
              className={`px-6 py-3 border-2 border-black font-mono font-bold transition-colors ${
                connectionStatus === 'connected' && inputMessage.trim()
                  ? 'bg-black text-white hover:bg-gray-800'
                  : 'bg-gray-200 text-gray-500 cursor-not-allowed'
              }`}
              disabled={connectionStatus !== 'connected' || !inputMessage.trim()}
            >
              SEND
            </button>
          </form>
          <div className="mt-2 flex justify-between">
            <p className="text-xs text-gray-600 font-mono">
              {connectionStatus === 'connected'
                ? 'End-to-end encrypted | HIPAA compliant | Powered by Rasa'
                : 'Waiting for Rasa server on port 5005...'}
            </p>
            <div className="flex gap-2">
              <button
                className="text-xs font-mono hover:underline"
                onClick={() => setShowCalendar(true)}
                disabled={connectionStatus !== 'connected'}
              >
                📅 CALENDAR
              </button>
              <button
                className="text-xs font-mono hover:underline"
                onClick={() => handleSendMessage('view my appointments')}
                disabled={connectionStatus !== 'connected'}
              >
                MY APPOINTMENTS
              </button>
              <button
                className="text-xs font-mono hover:underline"
                onClick={() => handleQuickReply('/nurse', 'Speak to nurse')}
              >
                SPEAK TO NURSE →
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Appointments Panel */}
      {showAppointments && (
        <div className="w-80 h-[calc(100vh-200px)] border-2 border-black bg-white flex flex-col">
          <div className="border-b-2 border-black p-4 bg-gray-50">
            <div className="flex justify-between items-center">
              <h3 className="font-mono font-bold">MY APPOINTMENTS</h3>
              <button
                onClick={() => setShowAppointments(false)}
                className="text-lg hover:bg-gray-200 px-2"
              >
                ×
              </button>
            </div>
          </div>
          <div className="p-4 overflow-y-auto flex-1">
            {appointments.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-gray-600 font-mono text-sm">No appointments scheduled</p>
                <button
                  onClick={() => {
                    setShowAppointments(false)
                    handleSendMessage('schedule appointment')
                  }}
                  className="mt-4 px-4 py-2 border border-black hover:bg-black hover:text-white transition-colors"
                >
                  Schedule Now
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {appointments.map((apt) => (
                  <div key={apt.id} className="border border-black p-3">
                    <div className="flex justify-between items-start mb-2">
                      <span className="font-mono text-xs">#{apt.id}</span>
                      <span className="text-xs bg-green-100 px-2 py-1 border border-green-600">CONFIRMED</span>
                    </div>
                    <p className="font-mono text-sm font-bold">{apt.date}</p>
                    <p className="font-mono text-sm">Time: {apt.time}</p>
                    {apt.department && <p className="font-mono text-sm">Department: {apt.department}</p>}
                    <p className="font-mono text-sm">Doctor: {apt.doctor}</p>
                    <div className="mt-2 flex gap-2">
                      <button
                        onClick={() => cancelAppointment(apt.id)}
                        className="text-xs border border-black px-2 py-1 hover:bg-black hover:text-white"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => {
                          // Store appointment ID to reschedule and open scheduling
                          handleSendMessage(`/reschedule_apt_${apt.id}`)
                          setShowAppointments(false)
                        }}
                        className="text-xs border border-black px-2 py-1 hover:bg-black hover:text-white"
                      >
                        Reschedule
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Appointment Calendar Modal */}
      {showCalendar && (
        <AppointmentCalendar
          onSelectDateTime={handleCalendarSelect}
          onClose={() => setShowCalendar(false)}
        />
      )}
    </div>
  )
}