'use client'

import { useState } from 'react'
import { initializeDatabase } from '@/lib/db-setup'

export default function AdminPage() {
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [firebaseConfig, setFirebaseConfig] = useState({
    apiKey: '',
    authDomain: '',
    projectId: '',
    storageBucket: '',
    messagingSenderId: '',
    appId: ''
  })

  const handleInitDatabase = async () => {
    setIsLoading(true)
    setMessage('Initializing database...')

    try {
      const result = await initializeDatabase()
      if (result.success) {
        setMessage('✅ Database initialized successfully with mockup data!')
      } else {
        setMessage('❌ Error initializing database')
      }
    } catch (error) {
      setMessage(`❌ Error: ${error}`)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Healthcare Database Admin</h1>

        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Firebase Configuration</h2>
          <div className="bg-yellow-50 border border-yellow-200 rounded p-4 mb-4">
            <p className="text-sm text-yellow-800">
              ⚠️ To use Firebase, you need to:
            </p>
            <ol className="list-decimal list-inside text-sm text-yellow-800 mt-2 space-y-1">
              <li>Go to <a href="https://console.firebase.google.com" target="_blank" className="underline">Firebase Console</a></li>
              <li>Create a new project (it's free)</li>
              <li>Enable Firestore Database</li>
              <li>Go to Project Settings → General → Your apps → Add app → Web</li>
              <li>Copy the configuration and update <code>lib/firebase.ts</code></li>
            </ol>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">Database Setup</h2>

          <div className="space-y-4">
            <div>
              <h3 className="font-medium mb-2">Collections to be created:</h3>
              <ul className="list-disc list-inside text-sm space-y-1 text-gray-600">
                <li><strong>Doctors:</strong> 6 doctors with specializations</li>
                <li><strong>Patients:</strong> 3 patient records with medical history</li>
                <li><strong>Appointments:</strong> 3 scheduled appointments</li>
                <li><strong>Departments:</strong> 6 hospital departments</li>
              </ul>
            </div>

            <button
              onClick={handleInitDatabase}
              disabled={isLoading}
              className={`px-6 py-3 rounded-lg font-medium ${
                isLoading
                  ? 'bg-gray-300 cursor-not-allowed'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              }`}
            >
              {isLoading ? 'Initializing...' : 'Initialize Database with Mockup Data'}
            </button>

            {message && (
              <div className={`p-4 rounded ${
                message.includes('✅')
                  ? 'bg-green-50 text-green-800'
                  : message.includes('❌')
                  ? 'bg-red-50 text-red-800'
                  : 'bg-blue-50 text-blue-800'
              }`}>
                {message}
              </div>
            )}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6 mt-6">
          <h2 className="text-xl font-semibold mb-4">Database Structure</h2>

          <div className="space-y-4">
            <div>
              <h3 className="font-medium text-gray-700">👨‍⚕️ Doctors Collection</h3>
              <pre className="bg-gray-100 p-2 rounded text-xs mt-1">
{`{
  name: string
  email: string
  phone: string
  specialization: string
  department: string
  availability: { days: [], hours: string }
  experience: number
  rating: number
}`}
              </pre>
            </div>

            <div>
              <h3 className="font-medium text-gray-700">👤 Patients Collection</h3>
              <pre className="bg-gray-100 p-2 rounded text-xs mt-1">
{`{
  name: string
  email: string
  phone: string
  dateOfBirth: Date
  gender: string
  bloodType: string
  allergies: string[]
  medicalHistory: string[]
  emergencyContact: {...}
}`}
              </pre>
            </div>

            <div>
              <h3 className="font-medium text-gray-700">📅 Appointments Collection</h3>
              <pre className="bg-gray-100 p-2 rounded text-xs mt-1">
{`{
  patientId: string
  patientName: string
  doctorId: string
  doctorName: string
  department: string
  date: Date
  time: string
  status: string
  reason: string
}`}
              </pre>
            </div>

            <div>
              <h3 className="font-medium text-gray-700">🏥 Departments Collection</h3>
              <pre className="bg-gray-100 p-2 rounded text-xs mt-1">
{`{
  name: string
  description: string
  head: string
  phone: string
  location: string
  services: string[]
}`}
              </pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}