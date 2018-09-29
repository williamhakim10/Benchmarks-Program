"""add relationship between lists and users

Revision ID: a921df1ce5a3
Revises: 0122cf52d3a6
Create Date: 2018-09-29 11:37:52.385864

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a921df1ce5a3'
down_revision = '0122cf52d3a6'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('list_users',
    sa.Column('list_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['list_id'], ['list_stats.list_id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], ),
    sa.PrimaryKeyConstraint('list_id', 'user_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('list_users')
    # ### end Alembic commands ###
