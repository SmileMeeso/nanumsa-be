"""add share_item_id_seq

Revision ID: 2d36887203ab
Revises: 31832085c8c5
Create Date: 2025-02-04 13:18:05.850711

"""
from typing import Sequence, Union

from sqlalchemy.schema import Sequence as Sq, CreateSequence, DropSequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2d36887203ab'
down_revision: Union[str, None] = '31832085c8c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(CreateSequence(Sq('share_item_id_seq')))


def downgrade() -> None:
    op.execute(DropSequence(Sq('share_item_id_seq')))
