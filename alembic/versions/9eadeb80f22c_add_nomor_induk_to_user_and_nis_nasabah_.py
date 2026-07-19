"""add nomor_induk to user and nis_nasabah to account

Revision ID: 9eadeb80f22c
Revises: 9930297b9ddb
Create Date: 2026-07-19 10:52:54.249435

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9eadeb80f22c'
down_revision: Union[str, Sequence[str], None] = '9930297b9ddb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('account', schema=None) as batch_op:
        batch_op.add_column(sa.Column('nis_nasabah', sa.String(length=30), nullable=True))
        batch_op.create_index(batch_op.f('ix_account_nis_nasabah'), ['nis_nasabah'], unique=False)

    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('nomor_induk', sa.String(length=30), nullable=True))
        batch_op.create_unique_constraint('uq_user_nomor_induk', ['nomor_induk'])


def downgrade() -> None:
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_constraint('uq_user_nomor_induk', type_='unique')
        batch_op.drop_column('nomor_induk')

    with op.batch_alter_table('account', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_account_nis_nasabah'))
        batch_op.drop_column('nis_nasabah')
