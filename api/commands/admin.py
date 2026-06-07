import click
from sqlalchemy.orm import Session

from extensions.ext_database import db
from models.account import Account, SystemRole
from services.account_service import AccountService


@click.command('promote-super-admin', help='Promote a user to super admin.')
@click.option('--email', prompt=True, help='Account email to promote')
def promote_super_admin(email):
    """Promote an existing user to super admin."""
    normalized_email = email.strip().lower()
    account = AccountService.get_account_by_email_with_case_fallback(normalized_email)

    if not account:
        click.echo(click.style(f'Account not found for email: {email}', fg='red'))
        return

    if account.system_role == SystemRole.SUPER_ADMIN:
        click.echo(click.style(f'Account {account.email} is already a super admin.', fg='yellow'))
        return

    with Session(db.engine) as session:
        account = session.merge(account)
        account.system_role = SystemRole.SUPER_ADMIN
        session.commit()

    click.echo(click.style(f'Account {account.email} promoted to super admin successfully.', fg='green'))


@click.command('demote-super-admin', help='Demote a super admin to regular user.')
@click.option('--email', prompt=True, help='Account email to demote')
def demote_super_admin(email):
    """Demote a super admin to regular user."""
    normalized_email = email.strip().lower()
    account = AccountService.get_account_by_email_with_case_fallback(normalized_email)

    if not account:
        click.echo(click.style(f'Account not found for email: {email}', fg='red'))
        return

    if account.system_role != SystemRole.SUPER_ADMIN:
        click.echo(click.style(f'Account {account.email} is not a super admin.', fg='yellow'))
        return

    with Session(db.engine) as session:
        account = session.merge(account)
        account.system_role = SystemRole.USER
        session.commit()

    click.echo(click.style(f'Account {account.email} demoted to regular user successfully.', fg='green'))


@click.command('list-super-admins', help='List all super admin accounts.')
def list_super_admins():
    """List all super admin accounts."""
    from sqlalchemy import select

    with Session(db.engine) as session:
        admins = session.scalars(
            select(Account).where(Account.system_role == SystemRole.SUPER_ADMIN)
        ).all()

        if not admins:
            click.echo(click.style('No super admins found.', fg='yellow'))
            return

        click.echo(click.style(f'Found {len(admins)} super admin(s):', fg='green'))
        for admin in admins:
            click.echo(f'  - {admin.email} ({admin.name})')


@click.command('init-super-admin', help='Initialize the super admin (promote owner of first workspace).')
def init_super_admin():
    """Initialize super admin: promote the oldest account with owner role."""
    from sqlalchemy import select

    from models.account import TenantAccountJoin, TenantAccountRole

    with Session(db.engine) as session:
        # Find the earliest tenant owner
        join = session.scalars(
            select(TenantAccountJoin)
            .where(TenantAccountJoin.role == TenantAccountRole.OWNER)
            .order_by(TenantAccountJoin.created_at.asc())
            .limit(1)
        ).first()

        if not join:
            click.echo(click.style('No workspace owner found in the system.', fg='red'))
            return

        account = session.get(Account, join.account_id)
        if not account:
            click.echo(click.style('Owner account not found.', fg='red'))
            return

        if account.system_role == SystemRole.SUPER_ADMIN:
            click.echo(click.style(f'Account {account.email} is already a super admin.', fg='yellow'))
            return

        account.system_role = SystemRole.SUPER_ADMIN
        session.commit()

    click.echo(click.style(f'Account {account.email} initialized as super admin successfully.', fg='green'))


def register_admin_commands(cli_group):
    cli_group.add_command(promote_super_admin)
    cli_group.add_command(demote_super_admin)
    cli_group.add_command(list_super_admins)
    cli_group.add_command(init_super_admin)
