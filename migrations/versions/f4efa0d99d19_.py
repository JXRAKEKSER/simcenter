""" Adding `strict_pulling` flag setting.

Revision ID: f4efa0d99d19
Revises: 
Create Date: 2020-02-08 17:45:13.795527

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f4efa0d99d19'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    try:
        op.add_column('settings', sa.Column('strict_pulling', sa.Boolean(), nullable=True))
    except Exception as e:
        pass
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('settings') as batch:
        batch.drop_column('strict_pulling')
    # ### end Alembic commands ###
