import type { CommonResponse } from '@/models/common'
import { del, get, post, put } from './base'

// -- Types -------------------------------------------------------------------

export type AdminWorkspace = {
  id: string
  name: string
  plan: string
  status: string
  member_count: number
  created_at: number
}

export type AdminWorkspaceDetail = {
  id: string
  name: string
  plan: string
  status: string
  members: AdminMember[]
  member_count: number
  created_at: number
}

export type AdminMember = {
  account_id: string
  name: string
  email: string
  role: string
  status: string
  joined_at: number
}

export type AdminUser = {
  id: string
  name: string
  email: string
  status: string
  system_role: string
  workspace_count: number
  created_at: number
}

export type AdminQuota = {
  id: string
  tenant_id: string
  account_id: string
  quota_type: 'token' | 'api_call' | 'app_count'
  quota_limit: number
  quota_used: number
  period: 'daily' | 'monthly' | 'total'
  is_active: boolean
}

export type AdminWorkspaceListResponse = {
  workspaces: AdminWorkspace[]
  has_more: boolean
  page: number
  limit: number
  total: number
}

export type AdminUserListResponse = {
  users: AdminUser[]
  has_more: boolean
  page: number
  limit: number
  total: number
}

export type AdminQuotaListResponse = {
  quotas: AdminQuota[]
}

// -- Workspace APIs ----------------------------------------------------------

export const fetchAdminWorkspaces = (params?: Record<string, any>): Promise<AdminWorkspaceListResponse> => {
  return get<AdminWorkspaceListResponse>('/admin/workspaces', { params })
}

export const createAdminWorkspace = (body: { name: string; owner_email?: string }): Promise<AdminWorkspace> => {
  return post<AdminWorkspace>('/admin/workspaces', { body })
}

export const fetchAdminWorkspaceDetail = (tenantId: string): Promise<AdminWorkspaceDetail> => {
  return get<AdminWorkspaceDetail>(`/admin/workspaces/${tenantId}`)
}

export const deleteAdminWorkspace = (tenantId: string): Promise<CommonResponse> => {
  return del<CommonResponse>(`/admin/workspaces/${tenantId}`)
}

// -- Member APIs -------------------------------------------------------------

export const assignUserToWorkspace = (tenantId: string, body: { email: string; role: string }): Promise<AdminMember> => {
  return post<AdminMember>(`/admin/workspaces/${tenantId}/members`, { body })
}

export const removeUserFromWorkspace = (tenantId: string, accountId: string): Promise<CommonResponse> => {
  return del<CommonResponse>(`/admin/workspaces/${tenantId}/members?account_id=${accountId}`)
}

// -- User APIs ---------------------------------------------------------------

export const fetchAdminUsers = (params?: Record<string, any>): Promise<AdminUserListResponse> => {
  return get<AdminUserListResponse>('/admin/users', { params })
}

export const setAdminUserRole = (accountId: string, body: { system_role: 'super_admin' | 'user' }): Promise<AdminUser> => {
  return put<AdminUser>(`/admin/users/${accountId}/role`, { body })
}

// -- Quota APIs --------------------------------------------------------------

export const fetchWorkspaceQuotas = (tenantId: string, accountId?: string): Promise<AdminQuotaListResponse> => {
  const params = accountId ? { account_id: accountId } : undefined
  return get<AdminQuotaListResponse>(`/admin/workspaces/${tenantId}/quotas`, { params })
}

export const createUserQuota = (tenantId: string, body: {
  account_id: string
  quota_type: string
  quota_limit: number
  period: string
  is_active: boolean
}): Promise<AdminQuota> => {
  return post<AdminQuota>(`/admin/workspaces/${tenantId}/quotas/create`, { body })
}

export const deleteUserQuota = (quotaId: string): Promise<CommonResponse> => {
  return del<CommonResponse>(`/admin/quotas/${quotaId}`)
}
