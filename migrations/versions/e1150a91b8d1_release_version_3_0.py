"""release version 3.0

Revision ID: e1150a91b8d1
Revises: 
Create Date: 2019-01-09 15:14:30.861585

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1150a91b8d1'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('app_user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('signup_timestamp', sa.DateTime(), nullable=True),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.Column('email', sa.String(length=64), nullable=True),
    sa.Column('email_hash', sa.String(length=64), nullable=True),
    sa.Column('approved', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('app_user', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_app_user_email'), ['email'], unique=True)
        batch_op.create_index(batch_op.f('ix_app_user_email_hash'), ['email_hash'], unique=True)

    op.create_table('organization',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=True),
    sa.Column('financial_classification', sa.String(length=32), nullable=True),
    sa.Column('coverage_scope', sa.String(length=32), nullable=True),
    sa.Column('coverage_focus', sa.String(length=64), nullable=True),
    sa.Column('platform', sa.String(length=64), nullable=True),
    sa.Column('employee_range', sa.String(length=32), nullable=True),
    sa.Column('budget', sa.String(length=64), nullable=True),
    sa.Column('affiliations', sa.String(length=512), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('organization', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_organization_name'), ['name'], unique=True)

    op.create_table('email_list',
    sa.Column('list_id', sa.String(length=64), nullable=False),
    sa.Column('list_name', sa.String(length=128), nullable=True),
    sa.Column('api_key', sa.String(length=64), nullable=True),
    sa.Column('data_center', sa.String(length=64), nullable=True),
    sa.Column('store_aggregates', sa.Boolean(), nullable=True),
    sa.Column('monthly_updates', sa.Boolean(), nullable=True),
    sa.Column('org_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['org_id'], ['organization.id'], name='fk_org_id'),
    sa.PrimaryKeyConstraint('list_id')
    )
    op.create_table('users',
    sa.Column('org_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['org_id'], ['organization.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], ),
    sa.PrimaryKeyConstraint('org_id', 'user_id')
    )
    op.create_table('list_stats',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('analysis_timestamp', sa.DateTime(), nullable=True),
    sa.Column('frequency', sa.Float(), nullable=True),
    sa.Column('subscribers', sa.Integer(), nullable=True),
    sa.Column('open_rate', sa.Float(), nullable=True),
    sa.Column('hist_bin_counts', sa.String(length=512), nullable=True),
    sa.Column('subscribed_pct', sa.Float(), nullable=True),
    sa.Column('unsubscribed_pct', sa.Float(), nullable=True),
    sa.Column('cleaned_pct', sa.Float(), nullable=True),
    sa.Column('pending_pct', sa.Float(), nullable=True),
    sa.Column('high_open_rt_pct', sa.Float(), nullable=True),
    sa.Column('cur_yr_inactive_pct', sa.Float(), nullable=True),
    sa.Column('list_id', sa.String(length=64), nullable=True),
    sa.ForeignKeyConstraint(['list_id'], ['email_list.list_id'], name='fk_list_id'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('list_users',
    sa.Column('list_id', sa.String(length=64), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['list_id'], ['email_list.list_id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], ),
    sa.PrimaryKeyConstraint('list_id', 'user_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('list_users')
    op.drop_table('list_stats')
    op.drop_table('users')
    op.drop_table('email_list')
    with op.batch_alter_table('organization', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_organization_name'))

    op.drop_table('organization')
    with op.batch_alter_table('app_user', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_app_user_email_hash'))
        batch_op.drop_index(batch_op.f('ix_app_user_email'))

    op.drop_table('app_user')
    # ### end Alembic commands ###