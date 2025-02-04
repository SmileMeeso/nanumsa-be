"""Change kakao_user_id to bigint

Revision ID: 31832085c8c5
Revises: 47dfaf207af4
Create Date: 2025-02-04 12:44:23.214153

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '31832085c8c5'
down_revision: Union[str, None] = '47dfaf207af4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
    ALTER TABLE users
    ALTER COLUMN kakao_user_id TYPE bigint
    USING kakao_user_id::bigint;
    """)

def downgrade() -> None:
    op.execute("""
    ALTER TABLE users
    ALTER COLUMN kakao_user_id TYPE varchar
    USING kakao_user_id::varchar;
    """)