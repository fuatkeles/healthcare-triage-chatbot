'use client'

import { useState, useEffect } from 'react'

const FIREBASE_URL = 'https://chat-bot-a8ae4-default-rtdb.europe-west1.firebasedatabase.app'

type TableName = 'appointments' | 'patients' | 'doctors' | 'departments'

export default function DatabaseAdmin() {
  const [activeTab, setActiveTab] = useState<TableName>('appointments')
  const [data, setData] = useState<any>({})
  const [loading, setLoading] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editData, setEditData] = useState<any>({})
  const [searchQuery, setSearchQuery] = useState('')
  const [showAddForm, setShowAddForm] = useState(false)
  const [newRecord, setNewRecord] = useState<any>({})

  useEffect(() => {
    loadData()
  }, [activeTab])

  const loadData = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${FIREBASE_URL}/${activeTab}.json`)
      const result = await response.json()
      setData(result || {})
    } catch (error) {
      console.error('Failed to load data:', error)
    }
    setLoading(false)
  }

  const handleEdit = (id: string, item: any) => {
    setEditingId(id)
    setEditData({ ...item })
  }

  const handleSave = async (id: string) => {
    try {
      await fetch(`${FIREBASE_URL}/${activeTab}/${id}.json`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editData)
      })
      setEditingId(null)
      loadData()
    } catch (error) {
      console.error('Failed to update:', error)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this item?')) return
    try {
      await fetch(`${FIREBASE_URL}/${activeTab}/${id}.json`, {
        method: 'DELETE'
      })
      loadData()
    } catch (error) {
      console.error('Failed to delete:', error)
    }
  }

  const handleCancel = () => {
    setEditingId(null)
    setEditData({})
  }

  const handleAdd = async () => {
    try {
      const newId = `${activeTab.slice(0, 2).toUpperCase()}${Date.now()}`
      await fetch(`${FIREBASE_URL}/${activeTab}/${newId}.json`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newRecord)
      })
      setShowAddForm(false)
      setNewRecord({})
      loadData()
    } catch (error) {
      console.error('Failed to add:', error)
    }
  }

  const filterData = () => {
    if (!searchQuery.trim()) return data

    const filtered: any = {}
    Object.entries(data).forEach(([id, item]: [string, any]) => {
      const searchStr = JSON.stringify(item).toLowerCase()
      if (searchStr.includes(searchQuery.toLowerCase()) || id.toLowerCase().includes(searchQuery.toLowerCase())) {
        filtered[id] = item
      }
    })
    return filtered
  }

  const renderValue = (key: string, value: any, isEditing: boolean) => {
    if (isEditing) {
      if (typeof value === 'object' && value !== null) {
        return (
          <textarea
            className="w-full border border-black p-1 font-mono text-xs"
            rows={3}
            value={JSON.stringify(value, null, 2)}
            onChange={(e) => {
              try {
                setEditData({ ...editData, [key]: JSON.parse(e.target.value) })
              } catch {}
            }}
          />
        )
      }
      return (
        <input
          type="text"
          className="w-full border border-black p-1 font-mono text-xs"
          value={editData[key] || ''}
          onChange={(e) => setEditData({ ...editData, [key]: e.target.value })}
        />
      )
    }

    if (typeof value === 'object' && value !== null) {
      return <pre className="text-xs">{JSON.stringify(value, null, 2)}</pre>
    }
    return <span className="text-xs">{String(value)}</span>
  }

  const renderTable = () => {
    const filteredData = filterData()
    const entries = Object.entries(filteredData)

    if (entries.length === 0) {
      return <p className="text-center text-gray-500 py-8">No data found</p>
    }

    return (
      <div className="overflow-auto max-h-[calc(100vh-500px)] pb-4">
        <table className="w-full border-collapse">
          <thead className="sticky top-0 bg-black text-white">
            <tr>
              <th className="border border-black p-2 text-left text-xs font-mono">ID</th>
              {Object.keys(entries[0][1] as Record<string, any>).map((key) => (
                <th key={key} className="border border-black p-2 text-left text-xs font-mono">{key}</th>
              ))}
              <th className="border border-black p-2 text-left text-xs font-mono">ACTIONS</th>
            </tr>
          </thead>
          <tbody>
            {entries.map(([id, item]: [string, any]) => {
              const isEditing = editingId === id
              return (
                <tr key={id} className={isEditing ? 'bg-yellow-50' : 'hover:bg-gray-50'}>
                  <td className="border border-black p-2 font-mono text-xs font-bold">{id}</td>
                  {Object.entries(item).map(([key, value]) => (
                    <td key={key} className="border border-black p-2">
                      {renderValue(key, value, isEditing)}
                    </td>
                  ))}
                  <td className="border border-black p-2">
                    {isEditing ? (
                      <div className="flex gap-1">
                        <button
                          onClick={() => handleSave(id)}
                          className="px-2 py-1 text-xs border border-black bg-green-100 hover:bg-green-200"
                        >
                          Save
                        </button>
                        <button
                          onClick={handleCancel}
                          className="px-2 py-1 text-xs border border-black hover:bg-gray-200"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <div className="flex gap-1">
                        <button
                          onClick={() => handleEdit(id, item)}
                          className="px-2 py-1 text-xs border border-black hover:bg-blue-100"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(id)}
                          className="px-2 py-1 text-xs border border-black bg-red-100 hover:bg-red-200"
                        >
                          Delete
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col border-2 border-black">
      {/* Header */}
      <div className="border-b-2 border-black p-4 bg-black text-white">
        <h2 className="text-xl font-bold font-mono">DATABASE ADMIN</h2>
        <p className="text-xs font-mono mt-1">Firebase Realtime Database</p>
      </div>

      {/* Tabs */}
      <div className="flex border-b-2 border-black">
        {(['appointments', 'patients', 'doctors', 'departments'] as TableName[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 py-3 font-mono text-sm border-r border-black ${
              activeTab === tab
                ? 'bg-black text-white'
                : 'bg-white hover:bg-gray-100'
            }`}
          >
            {tab.toUpperCase()}
          </button>
        ))}
      </div>

      {/* Search and Add Bar */}
      <div className="border-b-2 border-black p-4 flex gap-2">
        <input
          type="text"
          placeholder="Search..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="flex-1 border border-black p-2 font-mono text-sm"
        />
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="px-4 py-2 border border-black font-mono text-sm bg-green-100 hover:bg-green-200"
        >
          {showAddForm ? 'CANCEL' : 'ADD NEW'}
        </button>
      </div>

      {/* Add Form */}
      {showAddForm && (
        <div className="border-b-2 border-black p-4 bg-yellow-50">
          <h3 className="font-mono font-bold mb-2">Add New {activeTab.slice(0, -1).toUpperCase()}</h3>
          <div className="grid grid-cols-2 gap-2 mb-2">
            {data && Object.keys(Object.values(data)[0] || {}).map((key) => (
              <div key={key}>
                <label className="text-xs font-mono">{key}:</label>
                <input
                  type="text"
                  className="w-full border border-black p-1 text-xs font-mono"
                  onChange={(e) => setNewRecord({ ...newRecord, [key]: e.target.value })}
                />
              </div>
            ))}
          </div>
          <button
            onClick={handleAdd}
            className="w-full py-2 border border-black font-mono text-sm bg-green-200 hover:bg-green-300"
          >
            SAVE NEW RECORD
          </button>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 p-4 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <p className="font-mono">Loading...</p>
          </div>
        ) : (
          renderTable()
        )}
      </div>

      {/* Refresh Button */}
      <div className="border-t-2 border-black p-4">
        <button
          onClick={loadData}
          className="w-full py-2 border border-black font-mono text-sm hover:bg-black hover:text-white transition-colors"
        >
          REFRESH DATA
        </button>
      </div>
    </div>
  )
}