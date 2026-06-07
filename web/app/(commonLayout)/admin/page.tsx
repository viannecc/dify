'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { fetchAdminWorkspaces, createAdminWorkspace, deleteAdminWorkspace, type AdminWorkspace } from '@/service/admin'

export default function AdminPage() {
  const router = useRouter()
  const [workspaces, setWorkspaces] = useState<AdminWorkspace[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newOwnerEmail, setNewOwnerEmail] = useState('')
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    loadWorkspaces()
  }, [])

  const loadWorkspaces = async () => {
    try {
      const data = await fetchAdminWorkspaces({ page: 1, limit: 50 })
      setWorkspaces(data.workspaces)
    } catch (e: any) {
      if (e?.code === 'unauthorized' || e?.status === 401) {
        setError('Access denied. Please sign in as a super admin.')
      } else {
        setError('Failed to load workspaces: ' + (e?.message || 'Unknown error'))
      }
    }
    setLoading(false)
  }

  const handleCreate = async () => {
    if (!newName.trim()) return
    try {
      await createAdminWorkspace({ name: newName.trim(), owner_email: newOwnerEmail.trim() || undefined })
      setNewName('')
      setNewOwnerEmail('')
      setShowCreate(false)
      await loadWorkspaces()
    } catch (e: any) {
      alert('Failed to create workspace: ' + (e?.message || 'Unknown error'))
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this workspace?')) return
    try {
      await deleteAdminWorkspace(id)
      await loadWorkspaces()
    } catch (e: any) {
      alert('Failed to delete: ' + (e?.message || 'Unknown error'))
    }
  }

  if (!mounted || loading) {
    return (
      <div style={{ padding: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 600, marginBottom: 16 }}>Admin Panel</h1>
        <p>Loading...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 600, marginBottom: 16 }}>Admin Panel</h1>
        <div style={{ padding: 16, background: '#fff2f0', border: '1px solid #ffccc7', borderRadius: 8, color: '#cf1322' }}>
          {error}
        </div>
      </div>
    )
  }

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 600 }}>Admin Panel - Workspace Management</h1>
        <button
          onClick={() => setShowCreate(!showCreate)}
          style={{
            padding: '8px 16px',
            background: '#1677ff',
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            cursor: 'pointer',
            fontSize: 14,
          }}
        >
          + Create Workspace
        </button>
      </div>

      {showCreate && (
        <div style={{ marginBottom: 24, padding: 16, background: '#f5f5f5', borderRadius: 8 }}>
          <h3 style={{ marginBottom: 12 }}>Create New Workspace</h3>
          <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
            <input
              type="text"
              placeholder="Workspace name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              style={{ padding: '6px 12px', borderRadius: 4, border: '1px solid #d9d9d9', flex: 1 }}
            />
            <input
              type="email"
              placeholder="Owner email (optional)"
              value={newOwnerEmail}
              onChange={(e) => setNewOwnerEmail(e.target.value)}
              style={{ padding: '6px 12px', borderRadius: 4, border: '1px solid #d9d9d9', flex: 1 }}
            />
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={handleCreate} style={{ padding: '6px 16px', background: '#52c41a', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}>
              Create
            </button>
            <button onClick={() => setShowCreate(false)} style={{ padding: '6px 16px', background: '#fff', color: '#666', border: '1px solid #d9d9d9', borderRadius: 4, cursor: 'pointer' }}>
              Cancel
            </button>
          </div>
        </div>
      )}

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #e8e8e8', textAlign: 'left' }}>
            <th style={{ padding: '8px 12px' }}>Name</th>
            <th style={{ padding: '8px 12px' }}>Plan</th>
            <th style={{ padding: '8px 12px' }}>Status</th>
            <th style={{ padding: '8px 12px' }}>Members</th>
            <th style={{ padding: '8px 12px' }}>Created</th>
            <th style={{ padding: '8px 12px' }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {workspaces.map((ws) => (
            <tr key={ws.id} style={{ borderBottom: '1px solid #f0f0f0' }}>
              <td style={{ padding: '8px 12px' }}>
                <a onClick={() => router.push(`/admin/workspaces/${ws.id}`)} style={{ color: '#1677ff', cursor: 'pointer', textDecoration: 'underline' }}>
                  {ws.name}
                </a>
              </td>
              <td style={{ padding: '8px 12px' }}>{ws.plan}</td>
              <td style={{ padding: '8px 12px' }}>{ws.status}</td>
              <td style={{ padding: '8px 12px' }}>{ws.member_count}</td>
              <td style={{ padding: '8px 12px' }}>{new Date(ws.created_at * 1000).toLocaleDateString()}</td>
              <td style={{ padding: '8px 12px' }}>
                <button onClick={() => handleDelete(ws.id)} style={{ padding: '4px 12px', background: '#ff4d4f', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}>
                  Delete
                </button>
              </td>
            </tr>
          ))}
          {workspaces.length === 0 && (
            <tr><td colSpan={6} style={{ padding: 24, textAlign: 'center', color: '#999' }}>No workspaces found</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
