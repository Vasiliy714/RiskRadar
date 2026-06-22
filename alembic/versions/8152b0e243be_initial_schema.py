"""Начальная схема

Revision ID: 8152b0e243be
Revises:
Create Date: 2026-06-02 03:36:46.894747

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# Идентификаторы ревизии, используемые Alembic.
revision: str = '8152b0e243be'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JSONB = postgresql.JSONB(astext_type=sa.Text())
_EMPTY_OBJECT = sa.text("'{}'::jsonb")
_EMPTY_ARRAY = sa.text("'[]'::jsonb")
_NOW = sa.text('now()')
_UUID_DEFAULT = sa.text('gen_random_uuid()')

_DOCUMENT_TYPE = sa.Enum(
    'annual_report',
    'quarterly_report',
    'news',
    'legal_case',
    'rating_report',
    'press_release',
    name='document_type',
    native_enum=False,
)
_RISK_REPORT_STATUS = sa.Enum(
    'running',
    'completed',
    'requires_review',
    'failed',
    name='risk_report_status',
    native_enum=False,
)
_RISK_LEVEL = sa.Enum(
    'low',
    'medium',
    'high',
    'critical',
    name='risk_level',
    native_enum=False,
)
_AGENT_NAME = sa.Enum(
    'report_agent',
    'news_agent',
    'market_agent',
    'legal_agent',
    'rating_agent',
    'supervisor',
    name='agent_name',
    native_enum=False,
)
_INGESTION_JOB_STATUS = sa.Enum(
    'queued',
    'running',
    'succeeded',
    'failed',
    name='ingestion_job_status',
    native_enum=False,
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=_NOW,
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=_NOW,
            nullable=False,
        ),
    ]


def _uuid_pk() -> sa.Column:
    return sa.Column('id', sa.UUID(), server_default=_UUID_DEFAULT, nullable=False)


def upgrade() -> None:
    """Обновляет схему."""
    # ### команды автоматически сгенерированы Alembic; при необходимости поправьте ###
    op.create_table(
        'issuers',
        sa.Column('code', sa.String(length=32), nullable=False),
        sa.Column('name', sa.String(length=512), nullable=False),
        sa.Column('inn', sa.String(length=12), nullable=True),
        sa.Column(
            'is_public',
            sa.Boolean(),
            server_default=sa.text('true'),
            nullable=False,
        ),
        sa.Column('country_code', sa.String(length=2), nullable=True),
        sa.Column('sector', sa.String(length=128), nullable=True),
        _uuid_pk(),
        *_timestamps(),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_issuers')),
        sa.UniqueConstraint('code', name=op.f('uq_issuers_code')),
    )
    op.create_index(op.f('ix_issuers_inn'), 'issuers', ['inn'], unique=False)
    op.create_table(
        'documents',
        sa.Column('issuer_id', sa.UUID(), nullable=True),
        sa.Column('doc_type', _DOCUMENT_TYPE, nullable=False),
        sa.Column('title', sa.String(length=512), nullable=False),
        sa.Column('source_url', sa.String(length=2048), nullable=True),
        sa.Column('external_id', sa.String(length=128), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', _JSONB, server_default=_EMPTY_OBJECT, nullable=False),
        sa.Column(
            'is_current',
            sa.Boolean(),
            server_default=sa.text('true'),
            nullable=False,
        ),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        _uuid_pk(),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ['issuer_id'],
            ['issuers.id'],
            name=op.f('fk_documents_issuer_id_issuers'),
            ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_documents')),
        sa.UniqueConstraint('content_hash', name='uq_documents_content_hash'),
    )
    op.create_index(
        'ix_documents_issuer_published',
        'documents',
        ['issuer_id', 'published_at'],
        unique=False,
    )
    op.create_index(
        'ix_documents_issuer_type_current',
        'documents',
        ['issuer_id', 'doc_type', 'is_current'],
        unique=False,
    )
    op.create_table(
        'risk_reports',
        sa.Column('issuer_id', sa.UUID(), nullable=False),
        sa.Column('status', _RISK_REPORT_STATUS, nullable=False),
        sa.Column('metadata', _JSONB, server_default=_EMPTY_OBJECT, nullable=False),
        sa.Column('risk_level', _RISK_LEVEL, nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=True),
        sa.Column('coverage_penalty', sa.Float(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            'coverage_penalty IS NULL OR '
            '(coverage_penalty >= 0 AND coverage_penalty <= 1)',
            name=op.f('ck_risk_reports_coverage_penalty_range'),
        ),
        sa.CheckConstraint(
            'risk_score IS NULL OR (risk_score >= 0 AND risk_score <= 100)',
            name=op.f('ck_risk_reports_risk_score_range'),
        ),
        sa.ForeignKeyConstraint(
            ['issuer_id'],
            ['issuers.id'],
            name=op.f('fk_risk_reports_issuer_id_issuers'),
            ondelete='RESTRICT',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_risk_reports')),
    )
    op.create_index(
        op.f('ix_risk_reports_issuer_id'),
        'risk_reports',
        ['issuer_id'],
        unique=False,
    )
    op.create_table(
        'agent_traces',
        sa.Column('risk_report_id', sa.UUID(), nullable=False),
        sa.Column('agent_name', _AGENT_NAME, nullable=False),
        sa.Column('input', _JSONB, server_default=_EMPTY_OBJECT, nullable=False),
        sa.Column('output', _JSONB, nullable=True),
        sa.Column(
            'retrieved_chunk_ids',
            _JSONB,
            server_default=_EMPTY_ARRAY,
            nullable=False,
        ),
        _uuid_pk(),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ['risk_report_id'],
            ['risk_reports.id'],
            name=op.f('fk_agent_traces_risk_report_id_risk_reports'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_agent_traces')),
    )
    op.create_index(
        op.f('ix_agent_traces_risk_report_id'),
        'agent_traces',
        ['risk_report_id'],
        unique=False,
    )
    op.create_table(
        'ingestion_jobs',
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('status', _INGESTION_JOB_STATUS, nullable=False),
        sa.Column('payload', _JSONB, server_default=_EMPTY_OBJECT, nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        _uuid_pk(),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ['document_id'],
            ['documents.id'],
            name=op.f('fk_ingestion_jobs_document_id_documents'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_ingestion_jobs')),
    )
    op.create_index(
        op.f('ix_ingestion_jobs_document_id'),
        'ingestion_jobs',
        ['document_id'],
        unique=False,
    )
    # ### конец команд Alembic ###


def downgrade() -> None:
    """Откатывает схему."""
    # ### команды автоматически сгенерированы Alembic; при необходимости поправьте ###
    op.drop_index(op.f('ix_ingestion_jobs_document_id'), table_name='ingestion_jobs')
    op.drop_table('ingestion_jobs')
    op.drop_index(op.f('ix_agent_traces_risk_report_id'), table_name='agent_traces')
    op.drop_table('agent_traces')
    op.drop_index(op.f('ix_risk_reports_issuer_id'), table_name='risk_reports')
    op.drop_table('risk_reports')
    op.drop_index('ix_documents_issuer_type_current', table_name='documents')
    op.drop_index('ix_documents_issuer_published', table_name='documents')
    op.drop_table('documents')
    op.drop_index(op.f('ix_issuers_inn'), table_name='issuers')
    op.drop_table('issuers')
    # ### конец команд Alembic ###
