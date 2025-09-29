'use client'

import { useState, useEffect } from 'react'

interface AppointmentCalendarProps {
  onSelectDateTime: (date: string, time: string) => void
  onClose: () => void
}

export default function AppointmentCalendar({ onSelectDateTime, onClose }: AppointmentCalendarProps) {
  const [selectedDate, setSelectedDate] = useState<Date | null>(null)
  const [selectedTime, setSelectedTime] = useState<string>('')
  const [currentMonth, setCurrentMonth] = useState(new Date())

  const timeSlots = [
    '09:00', '09:30', '10:00', '10:30', '11:00', '11:30',
    '14:00', '14:30', '15:00', '15:30', '16:00', '16:30'
  ]

  const getDaysInMonth = (date: Date) => {
    const year = date.getFullYear()
    const month = date.getMonth()
    const firstDay = new Date(year, month, 1)
    const lastDay = new Date(year, month + 1, 0)
    const daysInMonth = lastDay.getDate()
    const startingDayOfWeek = firstDay.getDay()

    const days = []

    // Add empty cells for days before month starts
    for (let i = 0; i < startingDayOfWeek; i++) {
      days.push(null)
    }

    // Add all days of the month
    for (let i = 1; i <= daysInMonth; i++) {
      days.push(new Date(year, month, i))
    }

    return days
  }

  const isWeekend = (date: Date) => {
    const day = date.getDay()
    return day === 0 || day === 6 // Sunday or Saturday
  }

  const isPastDate = (date: Date) => {
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    return date < today
  }

  const isToday = (date: Date) => {
    const today = new Date()
    return date.toDateString() === today.toDateString()
  }

  const formatDate = (date: Date) => {
    const options: Intl.DateTimeFormatOptions = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }
    return date.toLocaleDateString('en-US', options)
  }

  const handleDateClick = (date: Date) => {
    if (!isWeekend(date) && !isPastDate(date)) {
      setSelectedDate(date)
    }
  }

  const handleConfirm = () => {
    if (selectedDate && selectedTime) {
      const dateStr = formatDate(selectedDate)
      onSelectDateTime(dateStr, selectedTime)
    }
  }

  const nextMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1))
  }

  const prevMonth = () => {
    const prevDate = new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1)
    const today = new Date()
    if (prevDate.getMonth() >= today.getMonth() && prevDate.getFullYear() >= today.getFullYear()) {
      setCurrentMonth(prevDate)
    }
  }

  const monthYear = currentMonth.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
  const days = getDaysInMonth(currentMonth)

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white border-2 border-black p-6 max-w-2xl w-full mx-4">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-mono font-bold">SCHEDULE APPOINTMENT</h2>
          <button
            onClick={onClose}
            className="text-2xl hover:bg-gray-200 px-2"
          >
            ×
          </button>
        </div>

        {/* Calendar */}
        <div className="mb-6">
          <div className="flex justify-between items-center mb-4">
            <button
              onClick={prevMonth}
              className="px-3 py-1 border border-black hover:bg-black hover:text-white"
            >
              ←
            </button>
            <h3 className="font-mono font-bold">{monthYear}</h3>
            <button
              onClick={nextMonth}
              className="px-3 py-1 border border-black hover:bg-black hover:text-white"
            >
              →
            </button>
          </div>

          <div className="grid grid-cols-7 gap-1 mb-2">
            {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
              <div key={day} className="text-center font-mono text-xs font-bold p-2">
                {day}
              </div>
            ))}
          </div>

          <div className="grid grid-cols-7 gap-1">
            {days.map((date, index) => (
              <div
                key={index}
                className={`
                  border border-gray-300 p-2 h-10 flex items-center justify-center
                  ${!date ? 'bg-gray-50' : ''}
                  ${date && isWeekend(date) ? 'bg-gray-200 text-gray-400 cursor-not-allowed' : ''}
                  ${date && isPastDate(date) ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : ''}
                  ${date && isToday(date) ? 'bg-yellow-100' : ''}
                  ${date && selectedDate?.toDateString() === date.toDateString() ? 'bg-black text-white' : ''}
                  ${date && !isWeekend(date) && !isPastDate(date) ? 'hover:bg-gray-100 cursor-pointer' : ''}
                `}
                onClick={() => date && handleDateClick(date)}
              >
                {date && (
                  <span className="text-sm font-mono">
                    {date.getDate()}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Time Slots */}
        {selectedDate && (
          <div className="mb-6">
            <h3 className="font-mono font-bold mb-3">
              Available Times for {selectedDate.toLocaleDateString()}
            </h3>
            <div className="grid grid-cols-4 gap-2">
              {timeSlots.map(time => (
                <button
                  key={time}
                  onClick={() => setSelectedTime(time)}
                  className={`
                    px-3 py-2 border font-mono text-sm
                    ${selectedTime === time
                      ? 'border-black bg-black text-white'
                      : 'border-gray-300 hover:border-black'
                    }
                  `}
                >
                  {time}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Confirm Button */}
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-black hover:bg-gray-100"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={!selectedDate || !selectedTime}
            className={`
              px-4 py-2 border border-black
              ${selectedDate && selectedTime
                ? 'bg-black text-white hover:bg-gray-800'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
              }
            `}
          >
            Confirm Appointment
          </button>
        </div>
      </div>
    </div>
  )
}