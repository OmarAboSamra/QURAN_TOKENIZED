"""initial schema

Revision ID: 8f236b24bbdb
Revises: 
Create Date: 2026-02-20 23:07:28.655587

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8f236b24bbdb'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema – add D7 columns (pattern, related_roots)."""
    with op.batch_alter_table('roots', schema=None) as batch_op:
        batch_op.add_column(sa.Column('related_roots', sa.JSON(), nullable=True,
                                      comment="JSON list of similar/related root strings"))

    with op.batch_alter_table('tokens', schema=None) as batch_op:
        batch_op.add_column(sa.Column('pattern', sa.String(length=50), nullable=True,
                                      comment='Morphological pattern of the word'))
        batch_op.create_index(batch_op.f('ix_tokens_pattern'), ['pattern'], unique=False)


def downgrade() -> None:
    """Downgrade schema – remove D7 columns."""
    with op.batch_alter_table('tokens', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_tokens_pattern'))
        batch_op.drop_column('pattern')

    with op.batch_alter_table('roots', schema=None) as batch_op:
        batch_op.drop_column('related_roots')
