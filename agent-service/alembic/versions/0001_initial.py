"""Initial schema: sessions, documents, repositories, session_repositories, embeddings.

Revision ID: 0001
Revises:
Create Date: 2026-10-11

"""
from __future__ import annotations

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

EMBEDDING_DIM = 1024  # Qwen3-Embedding-0.6B native output size


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("last_active_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("document_count", sa.Integer(), server_default="0"),
        sa.Column("repo_count", sa.Integer(), server_default="0"),
        sa.Column("total_bytes", sa.Integer(), server_default="0"),
        sa.Column("message_count", sa.Integer(), server_default="0"),
    )

    op.create_table(
        "repositories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("commit_sha", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default="processing"),
        sa.Column("indexed_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_unique_constraint("uq_repositories_full_name_commit_sha", "repositories", ["full_name", "commit_sha"])

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("file_type", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default="processing"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "session_repositories",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id"), primary_key=True),
        sa.Column(
            "repository_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repositories.id"), primary_key=True
        ),
        sa.Column("last_used_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(EMBEDDING_DIM), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repositories.id"), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_embeddings_hnsw",
        "embeddings",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index(
        "ix_embeddings_repo_doc_source", "embeddings", ["repository_id", "document_id", "source_type"]
    )


def downgrade() -> None:
    op.drop_table("embeddings")
    op.drop_table("session_repositories")
    op.drop_table("documents")
    op.drop_table("repositories")
    op.drop_table("sessions")
