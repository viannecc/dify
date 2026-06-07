import logging

from sqlalchemy import func, select

from extensions.ext_database import db
from models.account import (
    Account,
    AccountStatus,
    SystemRole,
    Tenant,
    TenantAccountJoin,
    TenantAccountRole,
    TenantStatus,
    UserQuota,
    UserQuotaPeriod,
    UserQuotaType,
)
from services.account_service import TenantService

logger = logging.getLogger(__name__)


class AdminService:
    """Service for super admin operations: workspace management, user assignment, quota control."""

    # ── Workspace management ──────────────────────────────────────────────

    @classmethod
    def list_all_workspaces(cls, page: int = 1, limit: int = 20) -> dict:
        """List all workspaces with member/user counts."""
        stmt = select(Tenant).order_by(Tenant.created_at.desc())
        pagination = db.paginate(select=stmt, page=page, per_page=limit, error_out=False)

        workspaces = []
        for tenant in pagination.items:
            member_count = db.session.scalar(
                select(func.count(TenantAccountJoin.id)).where(
                    TenantAccountJoin.tenant_id == tenant.id
                )
            ) or 0
            workspaces.append({
                'id': tenant.id,
                'name': tenant.name,
                'plan': tenant.plan,
                'status': tenant.status,
                'member_count': member_count,
                'created_at': int(tenant.created_at.timestamp()),
            })

        return {
            'workspaces': workspaces,
            'has_more': pagination.has_next,
            'page': page,
            'limit': limit,
            'total': pagination.total,
        }

    @classmethod
    def create_workspace(cls, name: str, owner_email: str | None = None) -> dict:
        """Create a new workspace. Optionally assign an owner."""
        tenant = TenantService.create_tenant(name)
        db.session.flush()

        owner_id = None
        if owner_email:
            account = db.session.scalar(
                select(Account).where(Account.email == owner_email.lower())
            )
            if account:
                TenantService.create_tenant_member(tenant, account, role=TenantAccountRole.OWNER)
                owner_id = str(account.id)

        db.session.commit()

        return {
            'id': tenant.id,
            'name': tenant.name,
            'status': tenant.status,
            'owner_id': owner_id,
            'created_at': int(tenant.created_at.timestamp()),
        }

    @classmethod
    def get_workspace_detail(cls, tenant_id: str) -> dict | None:
        """Get workspace detail with member list."""
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            return None

        members = []
        joins = db.session.scalars(
            select(TenantAccountJoin).where(TenantAccountJoin.tenant_id == tenant_id)
        ).all()

        for join in joins:
            account = db.session.get(Account, join.account_id)
            if account:
                members.append({
                    'account_id': str(account.id),
                    'name': account.name,
                    'email': account.email,
                    'role': join.role,
                    'status': account.status,
                    'joined_at': int(join.created_at.timestamp()),
                })

        return {
            'id': tenant.id,
            'name': tenant.name,
            'plan': tenant.plan,
            'status': tenant.status,
            'members': members,
            'member_count': len(members),
            'created_at': int(tenant.created_at.timestamp()),
        }

    @classmethod
    def delete_workspace(cls, tenant_id: str) -> bool:
        """Archive (soft-delete) a workspace."""
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            return False
        tenant.status = TenantStatus.ARCHIVE
        db.session.commit()
        return True

    # ── User management ───────────────────────────────────────────────────

    @classmethod
    def assign_user_to_workspace(
        cls, tenant_id: str, email: str, role: str = TenantAccountRole.NORMAL
    ) -> dict:
        """Assign an existing user (by email) to a workspace with a given role."""
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError(f'Workspace {tenant_id} not found')

        normalized_email = email.lower()
        account = db.session.scalar(
            select(Account).where(Account.email == normalized_email)
        )
        if not account:
            # Create pending account for new user
            from services.account_service import RegisterService
            account = RegisterService.register(
                email=normalized_email,
                name=normalized_email.split('@')[0],
                language=None,
                status=AccountStatus.PENDING,
                is_setup=True,
                create_workspace_required=False,
            )

        # Check if already in tenant
        existing = db.session.scalar(
            select(TenantAccountJoin).where(
                TenantAccountJoin.tenant_id == tenant_id,
                TenantAccountJoin.account_id == account.id,
            )
        )
        if existing:
            raise ValueError(f'User {email} is already in workspace {tenant.name}')

        TenantService.create_tenant_member(tenant, account, role=role)
        db.session.commit()

        return {
            'account_id': str(account.id),
            'email': account.email,
            'name': account.name,
            'role': role,
            'tenant_id': tenant_id,
            'tenant_name': tenant.name,
        }

    @classmethod
    def remove_user_from_workspace(cls, tenant_id: str, account_id: str) -> bool:
        """Remove a user from a workspace."""
        join_record = db.session.scalar(
            select(TenantAccountJoin).where(
                TenantAccountJoin.tenant_id == tenant_id,
                TenantAccountJoin.account_id == account_id,
            )
        )
        if not join_record:
            return False
        db.session.delete(join_record)
        db.session.commit()
        return True

    @classmethod
    def list_all_users(cls, page: int = 1, limit: int = 50) -> dict:
        """List all accounts in the system."""
        stmt = select(Account).order_by(Account.created_at.desc())
        pagination = db.paginate(select=stmt, page=page, per_page=limit, error_out=False)

        users = []
        for account in pagination.items:
            # Get workspaces for each user
            joins = db.session.scalars(
                select(TenantAccountJoin).where(TenantAccountJoin.account_id == account.id)
            ).all()
            workspace_count = len(joins)

            users.append({
                'id': str(account.id),
                'name': account.name,
                'email': account.email,
                'status': account.status,
                'system_role': account.system_role,
                'workspace_count': workspace_count,
                'created_at': int(account.created_at.timestamp()),
            })

        return {
            'users': users,
            'has_more': pagination.has_next,
            'page': page,
            'limit': limit,
            'total': pagination.total,
        }

    @classmethod
    def set_system_role(cls, account_id: str, system_role: SystemRole) -> dict:
        """Promote or demote a user's system role."""
        account = db.session.get(Account, account_id)
        if not account:
            raise ValueError(f'Account {account_id} not found')

        account.system_role = system_role
        db.session.commit()

        return {
            'account_id': str(account.id),
            'email': account.email,
            'system_role': account.system_role,
        }

    # ── Quota management ──────────────────────────────────────────────────

    @classmethod
    def set_user_quota(
        cls,
        tenant_id: str,
        account_id: str,
        quota_type: UserQuotaType,
        quota_limit: int,
        period: UserQuotaPeriod = UserQuotaPeriod.MONTHLY,
        is_active: bool = True,
    ) -> UserQuota:
        """Set or update quota for a specific user in a workspace."""
        # Upsert
        existing = db.session.scalar(
            select(UserQuota).where(
                UserQuota.tenant_id == tenant_id,
                UserQuota.account_id == account_id,
                UserQuota.quota_type == quota_type,
            )
        )

        if existing:
            existing.quota_limit = quota_limit
            existing.period = period
            existing.is_active = is_active
            quota = existing
        else:
            quota = UserQuota(
                tenant_id=tenant_id,
                account_id=account_id,
                quota_type=quota_type,
                quota_limit=quota_limit,
                period=period,
                is_active=is_active,
            )
            db.session.add(quota)

        db.session.commit()
        return quota

    @classmethod
    def get_user_quotas(cls, tenant_id: str, account_id: str | None = None) -> list[dict]:
        """Get all quotas for a workspace, optionally filtered by user."""
        stmt = select(UserQuota).where(UserQuota.tenant_id == tenant_id)
        if account_id:
            stmt = stmt.where(UserQuota.account_id == account_id)
        stmt = stmt.order_by(UserQuota.account_id, UserQuota.quota_type)

        quotas = db.session.scalars(stmt).all()
        return [
            {
                'id': q.id,
                'tenant_id': q.tenant_id,
                'account_id': q.account_id,
                'quota_type': q.quota_type,
                'quota_limit': q.quota_limit,
                'quota_used': q.quota_used,
                'period': q.period,
                'is_active': q.is_active,
            }
            for q in quotas
        ]

    @classmethod
    def delete_user_quota(cls, quota_id: str) -> bool:
        """Delete a quota record."""
        quota = db.session.get(UserQuota, quota_id)
        if not quota:
            return False
        db.session.delete(quota)
        db.session.commit()
        return True

    @classmethod
    def check_user_quota_exceeded(
        cls, tenant_id: str, account_id: str, quota_type: UserQuotaType
    ) -> tuple[bool, int, int]:
        """
        Check if a user has exceeded their quota.
        Returns (is_exceeded, used, limit).
        -1 limit means unlimited; returns (False, used, -1).
        """
        quota = db.session.scalar(
            select(UserQuota).where(
                UserQuota.tenant_id == tenant_id,
                UserQuota.account_id == account_id,
                UserQuota.quota_type == quota_type,
                UserQuota.is_active == True,
            )
        )
        if not quota or quota.quota_limit == -1:
            return False, 0, -1

        return quota.quota_used >= quota.quota_limit, quota.quota_used, quota.quota_limit

    @classmethod
    def consume_user_quota(cls, tenant_id: str, account_id: str, quota_type: UserQuotaType, amount: int = 1) -> bool:
        """
        Try to consume quota for a user. Returns True if allowed, False if exceeded.
        Increments quota_used on success.
        """
        is_exceeded, used, limit = cls.check_user_quota_exceeded(tenant_id, account_id, quota_type)
        if is_exceeded:
            return False

        quota = db.session.scalar(
            select(UserQuota).where(
                UserQuota.tenant_id == tenant_id,
                UserQuota.account_id == account_id,
                UserQuota.quota_type == quota_type,
                UserQuota.is_active == True,
            )
        )
        if quota:
            quota.quota_used += amount
            db.session.commit()

        return True
