import logging

from flask import request
from flask_restx import Resource, fields

from controllers.console import console_ns
from controllers.console.wraps import account_initialization_required, setup_required
from libs.admin_required import admin_required
from libs.login import login_required
from models.account import SystemRole
from services.admin_service import AdminService

logger = logging.getLogger(__name__)

# ── Schema fields ──────────────────────────────────────────────────────────

user_fields = {
    "id": fields.String,
    "name": fields.String,
    "email": fields.String,
    "status": fields.String,
    "system_role": fields.String,
    "workspace_count": fields.Integer,
    "created_at": fields.Integer,
}


# ── API Resources ──────────────────────────────────────────────────────────

@console_ns.route("/admin/users")
class AdminUserListApi(Resource):
    """Super admin: list all users."""

    @setup_required
    @login_required
    @admin_required
    @account_initialization_required
    def get(self):
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 50, type=int)
        result = AdminService.list_all_users(page=page, limit=limit)
        return result, 200


@console_ns.route("/admin/users/<string:account_id>/role")
class AdminUserRoleApi(Resource):
    """Super admin: set a user's system role (promote/demote super admin)."""

    @setup_required
    @login_required
    @admin_required
    @account_initialization_required
    def put(self, account_id):
        data = request.get_json() or {}
        role_str = data.get("system_role", "").strip()

        if role_str not in (SystemRole.SUPER_ADMIN, SystemRole.USER):
            return {
                "code": "invalid_role",
                "message": "system_role must be super_admin or user",
            }, 400

        try:
            result = AdminService.set_system_role(account_id, SystemRole(role_str))
            return result, 200
        except ValueError as e:
            return {"code": "not_found", "message": str(e)}, 404
