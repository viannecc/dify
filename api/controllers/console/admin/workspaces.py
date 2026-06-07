import logging

from flask import request
from flask_restx import Resource, fields

from controllers.console import console_ns
from controllers.console.wraps import account_initialization_required, setup_required
from libs.admin_required import admin_required
from libs.login import login_required
from models.account import TenantAccountRole
from services.admin_service import AdminService

logger = logging.getLogger(__name__)


# ── Schema models ─────────────────────────────────────────────────────────

workspace_fields = {
    "id": fields.String,
    "name": fields.String,
    "plan": fields.String,
    "status": fields.String,
    "member_count": fields.Integer,
    "created_at": fields.Integer,
}

workspace_detail_fields = {
    "id": fields.String,
    "name": fields.String,
    "plan": fields.String,
    "status": fields.String,
    "members": fields.List(fields.Raw),
    "member_count": fields.Integer,
    "created_at": fields.Integer,
}

member_fields = {
    "account_id": fields.String,
    "name": fields.String,
    "email": fields.String,
    "role": fields.String,
    "status": fields.String,
    "joined_at": fields.Integer,
}

# ── API Resources ──────────────────────────────────────────────────────────


@console_ns.route("/admin/workspaces")
class AdminWorkspaceListApi(Resource):
    """Super admin: list all workspaces and create new ones."""

    @setup_required
    @login_required
    @admin_required
    @account_initialization_required
    def get(self):
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 20, type=int)
        result = AdminService.list_all_workspaces(page=page, limit=limit)
        return result, 200

    @setup_required
    @login_required
    @admin_required
    @account_initialization_required
    def post(self):
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        if not name:
            return {"code": "invalid_name", "message": "Workspace name is required"}, 400

        owner_email = data.get("owner_email", "").strip() or None
        result = AdminService.create_workspace(name=name, owner_email=owner_email)
        return result, 201


@console_ns.route("/admin/workspaces/<string:tenant_id>")
class AdminWorkspaceDetailApi(Resource):
    """Super admin: get/delete a specific workspace."""

    @setup_required
    @login_required
    @admin_required
    @account_initialization_required
    def get(self, tenant_id):
        result = AdminService.get_workspace_detail(tenant_id)
        if not result:
            return {"code": "not_found", "message": "Workspace not found"}, 404
        return result, 200

    @setup_required
    @login_required
    @admin_required
    @account_initialization_required
    def delete(self, tenant_id):
        success = AdminService.delete_workspace(tenant_id)
        if not success:
            return {"code": "not_found", "message": "Workspace not found"}, 404
        return {"result": "success"}, 200


@console_ns.route("/admin/workspaces/<string:tenant_id>/members")
class AdminWorkspaceMemberApi(Resource):
    """Super admin: assign/remove users to/from a workspace."""

    @setup_required
    @login_required
    @admin_required
    @account_initialization_required
    def post(self, tenant_id):
        data = request.get_json() or {}
        email = (data.get("email") or "").strip()
        role = data.get("role", TenantAccountRole.NORMAL)

        if not email:
            return {"code": "invalid_email", "message": "Email is required"}, 400

        if not TenantAccountRole.is_valid_role(role):
            return {"code": "invalid_role", "message": "Invalid role"}, 400

        try:
            result = AdminService.assign_user_to_workspace(tenant_id, email, role)
            return result, 200
        except ValueError as e:
            return {"code": "error", "message": str(e)}, 400

    @setup_required
    @login_required
    @admin_required
    @account_initialization_required
    def delete(self, tenant_id):
        account_id = request.args.get("account_id", "")
        if not account_id:
            return {"code": "invalid_account", "message": "account_id is required"}, 400

        success = AdminService.remove_user_from_workspace(tenant_id, account_id)
        if not success:
            return {"code": "not_found", "message": "Membership not found"}, 404
        return {"result": "success"}, 200
