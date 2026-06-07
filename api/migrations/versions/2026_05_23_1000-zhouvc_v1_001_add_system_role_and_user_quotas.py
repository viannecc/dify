"""add system_role to accounts and create user_quotas table

Revision ID: zhouvc_v1_001
Revises: 8574b23a38fd
Create Date: 2026-05-23 10:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

import models.types


# revision identifiers, used by Alembic.
revision = 'zhouvc_v1_001'
down_revision = '8574b23a38fd'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add system_role column to accounts table
    with op.batch_alter_table('accounts', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'system_role',
                sa.String(length=16),
                server_default=sa.text("'user'"),
                nullable=False,
            )
        )

    # 2. Create user_quotas table
    op.create_table(
        'user_quotas',
        sa.Column(
            'id',
            models.types.StringUUID(),
            nullable=False,
        ),
        sa.Column('tenant_id', models.types.StringUUID(), nullable=False),
        sa.Column('account_id', models.types.StringUUID(), nullable=False),
        sa.Column('quota_type', sa.String(length=16), nullable=False),
        sa.Column('quota_limit', sa.BigInteger(), nullable=False),
        sa.Column('quota_used', sa.BigInteger(), nullable=False),
        sa.Column('period', sa.String(length=16), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id', name='user_quota_pkey'),
    )

    # 3. Create indexes for user_quotas
    with op.batch_alter_table('user_quotas', schema=None) as batch_op:
        batch_op.create_index(
            'user_quota_tenant_user_idx',
            ['tenant_id', 'account_id'],
        )
        batch_op.create_unique_constraint(
            'unique_user_quota',
            ['tenant_id', 'account_id', 'quota_type'],
        )


def downgrade():
    # 1. Drop user_quotas table
    op.drop_table('user_quotas')

    # 2. Remove system_role column from accounts
    with op.batch_alter_table('accounts', schema=None) as batch_op:
        batch_op.drop_column('system_role')
