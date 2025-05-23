"""Add firebase_uid to User model

Revision ID: aec11460ac50
Revises: 8556f659ee03
Create Date: 2025-05-04 07:19:12.428920

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'aec11460ac50'
down_revision = '8556f659ee03'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('firebase_uid', sa.String(length=40), nullable=True))
        batch_op.alter_column('mobile',
               existing_type=sa.VARCHAR(length=15),
               nullable=True)
        batch_op.create_unique_constraint(None, ['firebase_uid'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='unique')
        batch_op.alter_column('mobile',
               existing_type=sa.VARCHAR(length=15),
               nullable=False)
        batch_op.drop_column('firebase_uid')

    # ### end Alembic commands ###
