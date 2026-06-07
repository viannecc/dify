'use client'

import type { ReactNode } from 'react'
import { useEffect } from 'react'
import Loading from '@/app/components/base/loading'
import { useAppContext } from '@/context/app-context'
import { usePathname, useRouter } from '@/next/navigation'

const adminRoutes = ['/admin'] as const

const isPathUnderRoute = (pathname: string, route: string) =>
  pathname === route || pathname.startsWith(`${route}/`)

export default function AdminRouteGuard({ children }: { children: ReactNode }) {
  const { isSuperAdmin, isLoadingCurrentWorkspace } = useAppContext()
  const pathname = usePathname()
  const router = useRouter()

  const isAdminRoute = adminRoutes.some(route => isPathUnderRoute(pathname, route))
  const shouldRedirect = isAdminRoute && !isLoadingCurrentWorkspace && !isSuperAdmin

  useEffect(() => {
    if (shouldRedirect)
      router.replace('/apps')
  }, [shouldRedirect, router])

  if (isAdminRoute && isLoadingCurrentWorkspace)
    return <Loading type="app" />

  if (shouldRedirect)
    return null

  return <>{children}</>
}
