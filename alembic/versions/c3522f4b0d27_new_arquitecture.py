"""new arquitecture

Revision ID: c3522f4b0d27
Revises: e095ef913958
Create Date: 2025-06-18 02:00:25.700411

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c3522f4b0d27'
down_revision: Union[str, None] = 'e095ef913958'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('working_groups',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('creator_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('description', sa.String(length=255), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_working_groups_id'), 'working_groups', ['id'], unique=False)
    op.create_index(op.f('ix_working_groups_name'), 'working_groups', ['name'], unique=True)
    op.create_table('devices',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('working_group_id', sa.Integer(), nullable=False),
    sa.Column('device_uid', sa.String(length=255), nullable=False),
    sa.Column('alias', sa.String(length=50), nullable=True),
    sa.Column('description', sa.String(length=255), nullable=True),
    sa.Column('last_seen', sa.DateTime(), nullable=True),
    sa.Column('last_ip_address', sa.String(length=45), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['working_group_id'], ['working_groups.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_devices_device_uid'), 'devices', ['device_uid'], unique=True)
    op.create_index(op.f('ix_devices_id'), 'devices', ['id'], unique=False)
    op.create_table('group_schedules',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('working_group_id', sa.Integer(), nullable=False),
    sa.Column('start_time', sa.DateTime(), nullable=False),
    sa.Column('end_time', sa.DateTime(), nullable=False),
    sa.Column('all_day', sa.Boolean(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['working_group_id'], ['working_groups.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_group_schedules_id'), 'group_schedules', ['id'], unique=False)
    op.create_table('notifications',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('working_group_id', sa.Integer(), nullable=False),
    sa.Column('raw_notification', sa.String(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('amount', sa.Float(), nullable=False),
    sa.Column('security_code', sa.String(length=255), nullable=False),
    sa.Column('status', sa.Enum('RECEIVED', 'SENT', name='notificationstatus'), nullable=False),
    sa.Column('notification_timestamp', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['working_group_id'], ['working_groups.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)
    op.create_table('device_users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('device_id', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_device_users_id'), 'device_users', ['id'], unique=False)
    op.create_table('device_users_notifications',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('notification_id', sa.Integer(), nullable=False),
    sa.Column('device_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('sent_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
    sa.ForeignKeyConstraint(['notification_id'], ['notifications.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('notification_id', 'device_id', 'user_id', name='_notification_device_user_uc')
    )
    op.create_index(op.f('ix_device_users_notifications_id'), 'device_users_notifications', ['id'], unique=False)
    op.create_table('individual_schedules',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('device_user_id', sa.Integer(), nullable=True),
    sa.Column('device_id', sa.Integer(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('start_time', sa.DateTime(), nullable=False),
    sa.Column('end_time', sa.DateTime(), nullable=False),
    sa.Column('all_day', sa.Boolean(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
    sa.ForeignKeyConstraint(['device_user_id'], ['device_users.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_individual_schedules_id'), 'individual_schedules', ['id'], unique=False)
    op.drop_index(op.f('ix_businesses_id'), table_name='businesses')
    op.drop_index(op.f('ix_businesses_name'), table_name='businesses')
    op.drop_table('businesses')
    op.drop_index(op.f('ix_yape_transactions_id'), table_name='yape_transactions')
    op.drop_table('yape_transactions')
    op.add_column('users', sa.Column('dni', sa.String(length=15), nullable=True))
    op.add_column('users', sa.Column('name', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('maternal_surname', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('paternal_surname', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), nullable=False))
    op.add_column('users', sa.Column('avatar', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('email', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('phone', sa.String(length=15), nullable=True))
    op.add_column('users', sa.Column('country_code', sa.String(length=5), nullable=True))
    op.add_column('users', sa.Column('last_login', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=False))
    op.create_unique_constraint(None, 'users', ['dni'])
    op.drop_constraint(op.f('users_business_id_fkey'), 'users', type_='foreignkey')
    op.drop_column('users', 'business_id')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('business_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key(op.f('users_business_id_fkey'), 'users', 'businesses', ['business_id'], ['id'])
    op.drop_constraint(None, 'users', type_='unique')
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'last_login')
    op.drop_column('users', 'country_code')
    op.drop_column('users', 'phone')
    op.drop_column('users', 'email')
    op.drop_column('users', 'avatar')
    op.drop_column('users', 'is_verified')
    op.drop_column('users', 'paternal_surname')
    op.drop_column('users', 'maternal_surname')
    op.drop_column('users', 'name')
    op.drop_column('users', 'dni')
    op.create_table('yape_transactions',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('amount', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False),
    sa.Column('sender_name', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('security_code', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('timestamp', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('business_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], name=op.f('yape_transactions_business_id_fkey')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('yape_transactions_user_id_fkey')),
    sa.PrimaryKeyConstraint('id', name=op.f('yape_transactions_pkey'))
    )
    op.create_index(op.f('ix_yape_transactions_id'), 'yape_transactions', ['id'], unique=False)
    op.create_table('businesses',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('owner_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name=op.f('businesses_owner_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('businesses_pkey')),
    sa.UniqueConstraint('owner_id', name=op.f('businesses_owner_id_key'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.create_index(op.f('ix_businesses_name'), 'businesses', ['name'], unique=True)
    op.create_index(op.f('ix_businesses_id'), 'businesses', ['id'], unique=False)
    op.drop_index(op.f('ix_individual_schedules_id'), table_name='individual_schedules')
    op.drop_table('individual_schedules')
    op.drop_index(op.f('ix_device_users_notifications_id'), table_name='device_users_notifications')
    op.drop_table('device_users_notifications')
    op.drop_index(op.f('ix_device_users_id'), table_name='device_users')
    op.drop_table('device_users')
    op.drop_index(op.f('ix_notifications_id'), table_name='notifications')
    op.drop_table('notifications')
    op.drop_index(op.f('ix_group_schedules_id'), table_name='group_schedules')
    op.drop_table('group_schedules')
    op.drop_index(op.f('ix_devices_id'), table_name='devices')
    op.drop_index(op.f('ix_devices_device_uid'), table_name='devices')
    op.drop_table('devices')
    op.drop_index(op.f('ix_working_groups_name'), table_name='working_groups')
    op.drop_index(op.f('ix_working_groups_id'), table_name='working_groups')
    op.drop_table('working_groups')
    # ### end Alembic commands ###
