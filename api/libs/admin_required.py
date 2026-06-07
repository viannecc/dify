import functools

from flask import Response
from flask_login import current_user


def admin_required(func):
    """
    Decorator that ensures the current user is a super admin.
    Must be applied after @login_required in the decorator stack.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        user = current_user._get_current_object()
        if not user or not getattr(user, "is_super_admin", False):
            return Response(
                '{"code": "forbidden", "message": "Super admin privileges required"}',
                status=403,
                content_type="application/json",
            )
        return func(*args, **kwargs)

    return wrapper
