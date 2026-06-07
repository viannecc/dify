'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import {
  fetchAdminWorkspaceDetail,
  assignUserToWorkspace,
  removeUserFromWorkspace,
  fetchWorkspaceQuotas,
  createUserQuota,
  deleteUserQuota,
  type AdminWorkspaceDetail,
  type AdminQuota,
} from '@/service/admin'

const ROLES = ['owner', 'admin', 'editor', 'normal', 'dataset_operator']
const QUOTA_TYPES = ['token', 'api_call', 'app_count']
const PERIODS = ['daily', 'monthly', 'total']

export default function WorkspaceDetailPage() {
  const params = useParams()
  const router = useRouter()
  const tenantId = params?.tenantId as string

  const [workspace, setWorkspace] = useState<AdminWorkspaceDetail | null>(null)
  const [quotas, setQuotas] = useState<AdminQuota[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [mounted, setMounted] = useState(false)

  const [email, setEmail] = useState('')
  const [role, setRole] = useState('normal')

  const [quotaAccountId, setQuotaAccountId] = useState('')
  const [quotaType, setQuotaType] = useState('token')
  const [quotaLimit, setQuotaLimit] = useState(1000)
  const [quotaPeriod, setQuotaPeriod] = useState('monthly')
  const [showQuotaForm, setShowQuotaForm] = useState(false)

  useEffect(() => {
    setMounted(true)
    if (tenantId) loadData()
  }, [tenantId])

  const loadData = async () => {
    try {
      const [ws, qs] = await Promise.all([
        fetchAdminWorkspaceDetail(tenantId),
        fetchWorkspaceQuotas(tenantId),
      ])
      setWorkspace(ws)
      setQuotas(qs.quotas)
    } catch (e: any) {
      setError('Failed to load: ' + (e?.message || 'Unknown error'))
    }
    setLoading(false)
  }

  const handleAddMember = async () => {
    if (!email.trim()) return
    try {
      await assignUserToWorkspace(tenantId, { email: email.trim(), role })
      setEmail('')
      await loadData()
    } catch (e: any) {
      alert('Failed to add member: ' + (e?.message || 'Unknown error'))
    }
  }

  const handleRemoveMember = async (accountId: string) => {
    if (!confirm('Remove this member?')) return
    try {
      await removeUserFromWorkspace(tenantId, accountId)
      await loadData()
    } catch (e: any) {
      alert('Failed to remove: ' + (e?.message || 'Unknown error'))
    }
  }

  const handleSetQuota = async () => {
    if (!quotaAccountId.trim()) return
    try {
      await createUserQuota(tenantId, {
        account_id: quotaAccountId.trim(),
        quota_type: quotaType,
        quota_limit: quotaLimit,
        period: quotaPeriod,
        is_active: true,
      })
      setShowQuotaForm(false)
      await loadData()
    } catch (e: any) {
      alert('Failed to set quota: ' + (e?.message || 'Unknown error'))
    }
  }

  const handleDeleteQuota = async (quotaId: string) => {
    if (!confirm('Delete this quota?')) return
    try {
      await deleteUserQuota(quotaId)
      await loadData()
    } catch (e: any) {
      alert('Failed to delete: ' + (e?.message || 'Unknown error'))
    }
  }

  const getMemberQuota = (accountId: string, type: string) => {
    return quotas.find((q) => q.account_id === accountId && q.quota_type === type)
  }

  if (!mounted || loading) {
    return <div style={{ padding: 24 }}><h1 style={{ fontSize: 24, fontWeight: 600 }}>Workspace Detail</h1><p>Loading...</p></div>
  }

  if (error) {
    return <div style={{ padding: 24 }}><h1 style={{ fontSize: 24, fontWeight: 600 }}>Workspace Detail</h1><div style={{ padding: 16, background: '#fff2f0', border: '1px solid #ffccc7', borderRadius: 8, color: '#cf1322' }}>{error}</div></div>
  }

  if (!workspace) {
    return <div style={{ padding: 24 }}><h1 style={{ fontSize: 24, fontWeight: 600 }}>Workspace not found</h1></div>
  }

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 16 }}>
        <a onClick={() => router.push('/admin')} style={{ color: '#1677ff', cursor: 'pointer', fontSize: 14 }}>
          &larr; Back to Workspaces
        </a>
      </div>

      <h1 style={{ fontSize: 24, fontWeight: 600, marginBottom: 24 }}>
        {workspace.name}
        <span style={{ fontSize: 14, color: '#999', marginLeft: 12 }}>
          {workspace.member_count} members | Plan: {workspace.plan}
        </span>
      </h1>

      {/* Add Member */}
      <div style={{ marginBottom: 32, padding: 16, background: '#fafafa', borderRadius: 8 }}>
        <h3 style={{ marginBottom: 12 }}>Add Member</h3>
        <div style={{ display: 'flex', gap: 8 }}>
          <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)}
            style={{ padding: '6px 12px', borderRadius: 4, border: '1px solid #d9d9d9', flex: 1 }} />
          <select value={role} onChange={(e) => setRole(e.target.value)}
            style={{ padding: '6px 12px', borderRadius: 4, border: '1px solid #d9d9d9' }}>
            {ROLES.map((r) => (<option key={r} value={r}>{r}</option>))}
          </select>
          <button onClick={handleAddMember}
            style={{ padding: '6px 16px', background: '#1677ff', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}>
            Add
          </button>
        </div>
      </div>

      {/* Members Table */}
      <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 12 }}>Members</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 32 }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #e8e8e8', textAlign: 'left' }}>
            <th style={{ padding: '8px 12px' }}>Name</th>
            <th style={{ padding: '8px 12px' }}>Email</th>
            <th style={{ padding: '8px 12px' }}>Role</th>
            <th style={{ padding: '8px 12px' }}>Token Quota</th>
            <th style={{ padding: '8px 12px' }}>API Quota</th>
            <th style={{ padding: '8px 12px' }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {workspace.members.map((m) => {
            const tokenQuota = getMemberQuota(m.account_id, 'token')
            const apiQuota = getMemberQuota(m.account_id, 'api_call')
            return (
              <tr key={m.account_id} style={{ borderBottom: '1px solid #f0f0f0' }}>
                <td style={{ padding: '8px 12px' }}>{m.name}</td>
                <td style={{ padding: '8px 12px' }}>{m.email}</td>
                <td style={{ padding: '8px 12px' }}>{m.role}</td>
                <td style={{ padding: '8px 12px' }}>
                  {tokenQuota ? `${tokenQuota.quota_used}/${tokenQuota.quota_limit}` : 'No limit'}
                </td>
                <td style={{ padding: '8px 12px' }}>
                  {apiQuota ? `${apiQuota.quota_used}/${apiQuota.quota_limit}` : 'No limit'}
                </td>
                <td style={{ padding: '8px 12px' }}>
                  <button onClick={() => { setQuotaAccountId(m.account_id); setShowQuotaForm(!showQuotaForm) }}
                    style={{ padding: '4px 8px', background: '#faad14', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 12, marginRight: 8 }}>
                    Set Quota
                  </button>
                  <button onClick={() => handleRemoveMember(m.account_id)}
                    style={{ padding: '4px 8px', background: '#ff4d4f', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}>
                    Remove
                  </button>
                </td>
              </tr>
            )
          })}
          {workspace.members.length === 0 && (
            <tr><td colSpan={6} style={{ padding: 24, textAlign: 'center', color: '#999' }}>No members</td></tr>
          )}
        </tbody>
      </table>

      {/* Quota Form */}
      {showQuotaForm && (
        <div style={{ marginBottom: 32, padding: 16, background: '#fff7e6', borderRadius: 8 }}>
          <h3 style={{ marginBottom: 12 }}>Set Quota for {workspace.members.find((m) => m.account_id === quotaAccountId)?.email || quotaAccountId}</h3>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <select value={quotaType} onChange={(e) => setQuotaType(e.target.value)}
              style={{ padding: '6px 12px', borderRadius: 4, border: '1px solid #d9d9d9' }}>
              {QUOTA_TYPES.map((t) => (<option key={t} value={t}>{t}</option>))}
            </select>
            <input type="number" value={quotaLimit} onChange={(e) => setQuotaLimit(Number(e.target.value))}
              placeholder="Limit (-1=unlimited)" style={{ padding: '6px 12px', borderRadius: 4, border: '1px solid #d9d9d9', width: 180 }} />
            <select value={quotaPeriod} onChange={(e) => setQuotaPeriod(e.target.value)}
              style={{ padding: '6px 12px', borderRadius: 4, border: '1px solid #d9d9d9' }}>
              {PERIODS.map((p) => (<option key={p} value={p}>{p}</option>))}
            </select>
            <button onClick={handleSetQuota}
              style={{ padding: '6px 16px', background: '#52c41a', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}>
              Save
            </button>
            <button onClick={() => setShowQuotaForm(false)}
              style={{ padding: '6px 16px', background: '#fff', color: '#666', border: '1px solid #d9d9d9', borderRadius: 4, cursor: 'pointer' }}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Quotas List */}
      <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 12 }}>All Quotas in Workspace</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #e8e8e8', textAlign: 'left' }}>
            <th style={{ padding: '8px 12px' }}>User</th>
            <th style={{ padding: '8px 12px' }}>Type</th>
            <th style={{ padding: '8px 12px' }}>Used/Limit</th>
            <th style={{ padding: '8px 12px' }}>Period</th>
            <th style={{ padding: '8px 12px' }}>Active</th>
            <th style={{ padding: '8px 12px' }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {quotas.map((q) => {
            const member = workspace.members.find((m) => m.account_id === q.account_id)
            return (
              <tr key={q.id} style={{ borderBottom: '1px solid #f0f0f0' }}>
                <td style={{ padding: '8px 12px' }}>{member?.email || q.account_id}</td>
                <td style={{ padding: '8px 12px' }}>{q.quota_type}</td>
                <td style={{ padding: '8px 12px' }}>{q.quota_used}/{q.quota_limit}</td>
                <td style={{ padding: '8px 12px' }}>{q.period}</td>
                <td style={{ padding: '8px 12px' }}>{q.is_active ? 'Yes' : 'No'}</td>
                <td style={{ padding: '8px 12px' }}>
                  <button onClick={() => handleDeleteQuota(q.id)}
                    style={{ padding: '4px 8px', background: '#ff4d4f', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}>
                    Delete
                  </button>
                </td>
              </tr>
            )
          })}
          {quotas.length === 0 && (
            <tr><td colSpan={6} style={{ padding: 24, textAlign: 'center', color: '#999' }}>No quotas set</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
