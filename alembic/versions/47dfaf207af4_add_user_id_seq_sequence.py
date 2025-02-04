"""Add user_id_seq sequence

Revision ID: 47dfaf207af4
Revises: 9a237e861a09
Create Date: 2025-02-03 21:16:30.921389

"""
from typing import Sequence, Union

from sqlalchemy.schema import Sequence as Sq, CreateSequence, DropSequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '47dfaf207af4'
down_revision: Union[str, None] = '9a237e861a09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(CreateSequence(Sq('user_id_seq')))


def downgrade() -> None:
    op.execute(DropSequence(Sq('user_id_seq')))
