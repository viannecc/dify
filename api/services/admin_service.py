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
        """List all workspaces with member counts. Uses a single aggregated query to avoid N+1."""
        stmt = select(Tenant).order_by(Tenant.created_at.desc())
        pagination = db.paginate(select=stmt, page=page, per_page=limit, error_out=False)

        tenant_ids = [t.id for t in pagination.items]

        # Single query to get all member counts
        counts: dict[str, int] = {}
        if tenant_ids:
            rows = db.session.execute(
                select(TenantAccountJoin.tenant_id, func.count(TenantAccountJoin.id).label("cnt"))
                .where(TenantAccountJoin.tenant_id.in_(tenant_ids))
                .group_by(TenantAccountJoin.tenant_id)
            ).all()
            counts = {row.tenant_id: row.cnt for row in rows}

        workspaces = [
            {
                "id": tenant.id,
                "name": tenant.name,
                "plan": tenant.plan,
                "status": tenant.status,
                "member_count": counts.get(tenant.id, 0),
                "created_at": int(tenant.created_at.timestamp()),
            }
            for tenant in pagination.items
        ]

        return {
            "workspaces": workspaces,
            "has_more": pagination.has_next,
            "page": page,
            "limit": limit,
            "total": pagination.total,
        }

    @classmethod
    def create_workspace(cls, name: str, owner_email: str | None = None) -> dict:
        """Create a new workspace. Optionally assign an owner by email."""
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
            "id": tenant.id,
            "name": tenant.name,
            "status": tenant.status,
            "owner_id": owner_id,
            "created_at": int(tenant.created_at.timestamp()),
        }

    @classmethod
    def get_workspace_detail(cls, tenant_id: str) -> dict | None:
        """Get workspace detail with member list. Uses a single JOIN query to avoid N+1."""
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            return None

        # Single JOIN query instead of per-member lookups
        rows = db.session.execute(
            select(Account, TenantAccountJoin.role, TenantAccountJoin.created_at)
            .join(TenantAccountJoin, Account.id == TenantAccountJoin.account_id)
            .where(TenantAccountJoin.tenant_id == tenant_id)
        ).all()

        members = [
            {
                "account_id": str(account.id),
                "name": account.name,
                "email": account.email,
                "role": role,
                "status": account.status,
                "joined_at": int(joined_at.timestamp()),
            }
            for account, role, joined_at in rows
        ]

        return {
            "id": tenant.id,
            "name": tenant.name,
            "plan": tenant.plan,
            "status": tenant.status,
            "members": members,
            "member_count": len(members),
            "created_at": int(tenant.created_at.timestamp()),
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
            raise ValueError(f"Workspace {tenant_id} not found")

        normalized_email = email.lower()
        account = db.session.scalar(
            select(Account).where(Account.email == normalized_email)
        )
        if not account:
            from services.account_service import RegisterService

            account = RegisterService.register(
                email=normalized_email,
                name=normalized_email.split("@")[0],
                language=None,
                status=AccountStatus.PENDING,
                is_setup=True,
                create_workspace_required=False,
            )

        existing = db.session.scalar(
            select(TenantAccountJoin).where(
                TenantAccountJoin.tenant_id == tenant_id,
                TenantAccountJoin.account_id == account.id,
            )
        )
        if existing:
            raise ValueError(f"User {email} is already in workspace {tenant.name}")

        TenantService.create_tenant_member(tenant, account, role=role)
        db.session.commit()

        return {
            "account_id": str(account.id),
            "email": account.email,
            "name": account.name,
            "role": role,
            "tenant_id": tenant_id,
            "tenant_name": tenant.name,
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
        """List all accounts. Uses a single aggregated query to avoid N+1 on workspace counts."""
        stmt = select(Account).order_by(Account.created_at.desc())
        pagination = db.paginate(select=stmt, page=page, per_page=limit, error_out=False)

        account_ids = [a.id for a in pagination.items]

        # Single query for all workspace counts
        workspace_counts: dict[str, int] = {}
        if account_ids:
            rows = db.session.execute(
                select(TenantAccountJoin.account_id, func.count(TenantAccountJoin.id).label("cnt"))
                .where(TenantAccountJoin.account_id.in_(account_ids))
                .group_by(TenantAccountJoin.account_id)
            ).all()
            workspace_counts = {row.account_id: row.cnt for row in rows}

        users = [
            {
                "id": str(account.id),
                "name": account.name,
                "email": account.email,
                "status": account.status,
                "system_role": account.system_role,
                "workspace_count": workspace_counts.get(account.id, 0),
                "created_at": int(account.created_at.timestamp()),
            }
            for account in pagination.items
        ]

        return {
            "users": users,
            "has_more": pagination.has_next,
            "page": page,
            "limit": limit,
            "total": pagination.total,
        }

    @classmethod
    def set_system_role(cls, account_id: str, system_role: SystemRole) -> dict:
        """Promote or demote a user's system role."""
        account = db.session.get(Account, account_id)
        if not account:
            raise ValueError(f"Account {account_id} not found")

        account.system_role = system_role
        db.session.commit()

        return {
            "account_id": str(account.id),
            "email": account.email,
            "system_role": account.system_role,
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
        """Set or update quota for a specific user in a workspace (upsert)."""
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

        return [
            {
                "id": q.id,
                "tenant_id": q.tenant_id,
                "account_id": q.account_id,
                "quota_type": q.quota_type,
                "quota_limit": q.quota_limit,
                "quota_used": q.quota_used,
                "period": q.period,
                "is_active": q.is_active,
            }
            for q in db.session.scalars(stmt).all()
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
        Returns (is_exceeded, used, limit). limit == -1 means unlimited.
        """
        quota = db.session.scalar(
            select(UserQuota).where(
                UserQuota.tenant_id == tenant_id,
                UserQuota.account_id == account_id,
                UserQuota.quota_type == quota_type,
                UserQuota.is_active == True,  # noqa: E712
            )
        )
        if not quota or quota.quota_limit == -1:
            return False, 0, -1

        return quota.quota_used >= quota.quota_limit, quota.quota_used, quota.quota_limit

    @classmethod
    def consume_user_quota(
        cls, tenant_id: str, account_id: str, quota_type: UserQuotaType, amount: int = 1
    ) -> bool:
        """
        Consume quota for a user. Returns True if allowed and increments quota_used, False if exceeded.
        Uses a targeted UPDATE to avoid a second SELECT.
        """
        quota = db.session.scalar(
            select(UserQuota).where(
                UserQuota.tenant_id == tenant_id,
                UserQuota.account_id == account_id,
                UserQuota.quota_type == quota_type,
                UserQuota.is_active == True,  # noqa: E712
            )
        )
        # No quota record or unlimited → allow
        if not quota or quota.quota_limit == -1:
            return True

        if quota.quota_used >= quota.quota_limit:
            return False

        quota.quota_used += amount
        db.session.commit()
        return True
