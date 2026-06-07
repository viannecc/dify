import logging

from flask import request
from flask_restx import Resource, fields

from controllers.console import console_ns
from controllers.console.wraps import account_initialization_required, setup_required
from libs.admin_required import admin_required
from libs.login import login_required
from models.account import UserQuotaPeriod, UserQuotaType
from services.admin_service import AdminService

logger = logging.getLogger(__name__)

# -- Schema fields ----------------------------------------------------------

quota_fields = {
    'id': fields.String,
    'tenant_id': fields.String,
    'account_id': fields.String,
    'quota_type': fields.String,
    'quota_limit': fields.Integer,
    'quota_used': fields.Integer,
    'period': fields.String,
    'is_active': fields.Boolean,
}


# -- API Resources ----------------------------------------------------------

@console_ns.route('/admin/workspaces/<string:tenant_id>/quotas')
class AdminWorkspaceQuotaListApi(Resource):

    @setup_required
    @login_required
    @admin_required
    @account_initialization_required
    def get(self, tenant_id):
        account_id = request.args.get('account_id')
        result = AdminService.get_user_quotas(tenant_id, account_id=account_id)
        return {'quotas': result}, 200


@console_ns.route('/admin/workspaces/<string:tenant_id>/quotas/create')
class AdminUserQuotaApi(Resource):

    @setup_required
    @login_required
    @admin_required
    @account_initialization_required
    def post(self, tenant_id):
        data = request.get_json() or {}
        account_id = data.get('account_id', '').strip()
        quota_type_str = data.get('quota_type', '').strip()
        quota_limit = data.get('quota_limit', 0)
        period_str = data.get('period', 'monthly').strip()

        if not account_id:
            return {'code': 'invalid_account', 'message': 'account_id is required'}, 400

        if quota_type_str not in ('token', 'api_call', 'app_count'):
            return {'code': 'invalid_quota_type', 'message': 'quota_type must be token/api_call/app_count'}, 400

        if period_str not in ('daily', 'monthly', 'total'):
            return {'code': 'invalid_period', 'message': 'period must be daily/monthly/total'}, 400

        quota = AdminService.set_user_quota(
            tenant_id=tenant_id,
            account_id=account_id,
            quota_type=UserQuotaType(quota_type_str),
            quota_limit=quota_limit,
            period=UserQuotaPeriod(period_str),
            is_active=data.get('is_active', True),
        )

        return {
            'id': quota.id,
            'tenant_id': quota.tenant_id,
            'account_id': quota.account_id,
            'quota_type': quota.quota_type,
            'quota_limit': quota.quota_limit,
            'quota_used': quota.quota_used,
            'period': quota.period,
            'is_active': quota.is_active,
        }, 201


@console_ns.route('/admin/quotas/<string:quota_id>')
class AdminQuotaDeleteApi(Resource):

    @setup_required
    @login_required
    @admin_required
    @account_initialization_required
    def delete(self, quota_id):
        success = AdminService.delete_user_quota(quota_id)
        if not success:
            return {'code': 'not_found', 'message': 'Quota not found'}, 404
        return {'result': 'success'}, 200
