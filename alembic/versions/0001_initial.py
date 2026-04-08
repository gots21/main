"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "persons",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("birth_year", sa.Integer, nullable=True),
        sa.Column("residence", sa.String(255), nullable=True),
        sa.Column("career_history", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("education", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("interests", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("mbti_raw", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("mbti_type", sa.String(10), nullable=True),
        sa.Column("speech_patterns", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("feedback_deltas", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("custom_directions", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("system_prompt_cache", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("person_id", sa.Integer, sa.ForeignKey("persons.id"), nullable=False),
        sa.Column("system_prompt_snapshot", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("session_id", sa.Integer, sa.ForeignKey("chat_sessions.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("timestamp", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "feedback_surveys",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("session_id", sa.Integer, sa.ForeignKey("chat_sessions.id"), nullable=False),
        sa.Column("realism_score", sa.Integer, nullable=False),
        sa.Column("personality_accuracy", sa.Integer, nullable=False),
        sa.Column("communication_style_accuracy", sa.Integer, nullable=False),
        sa.Column("humor_accuracy", sa.Integer, nullable=False),
        sa.Column("knowledge_accuracy", sa.Integer, nullable=False),
        sa.Column("corrections", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("missing_traits", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("extra_traits", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("general_feedback", sa.Text, nullable=True),
        sa.Column("submitted_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("feedback_surveys")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("persons")
