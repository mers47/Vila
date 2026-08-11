"""initial

Revision ID: 0001
Revises:
Create Date: 2026-08-11
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('email', sa.String(320), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(32), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_email', 'users', ['email'])

    op.create_table('leads',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('business_name', sa.String(255), nullable=False),
        sa.Column('industry', sa.String(120), nullable=True),
        sa.Column('province', sa.String(120), nullable=True),
        sa.Column('city', sa.String(120), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('website', sa.String(500), nullable=True),
        sa.Column('source', sa.String(80), nullable=False),
        sa.Column('source_external_id', sa.String(255), nullable=True),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('temperature', sa.String(20), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('assigned_to_user_id', sa.Uuid(), nullable=True),
        sa.Column('next_follow_up_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_contact_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source', 'source_external_id', name='uq_lead_source_external_id'),
    )
    op.create_index('ix_leads_business_name', 'leads', ['business_name'])
    op.create_index('ix_leads_status_score', 'leads', ['status', 'score'])
    op.create_index('ix_leads_city_industry', 'leads', ['city', 'industry'])

    op.create_table('contact_points',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('lead_id', sa.Uuid(), nullable=False),
        sa.Column('channel', sa.String(40), nullable=False),
        sa.Column('value', sa.String(500), nullable=False),
        sa.Column('value_normalized', sa.String(500), nullable=False),
        sa.Column('consent_status', sa.String(30), nullable=False),
        sa.Column('consent_source', sa.String(120), nullable=True),
        sa.Column('consent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('interaction_started', sa.Boolean(), nullable=False),
        sa.Column('last_inbound_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_valid', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('channel', 'value_normalized', name='uq_contact_channel_value'),
    )

    op.create_table('campaigns',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('min_score', sa.Integer(), nullable=False),
        sa.Column('channels', sa.JSON(), nullable=False),
        sa.Column('message_template', sa.Text(), nullable=False),
        sa.Column('provider_templates', sa.JSON(), nullable=False),
        sa.Column('follow_up_rules', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    op.create_table('conversations',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('lead_id', sa.Uuid(), nullable=False),
        sa.Column('channel', sa.String(40), nullable=False),
        sa.Column('external_thread_id', sa.String(255), nullable=True),
        sa.Column('human_takeover', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lead_id', 'channel', name='uq_conversation_lead_channel'),
    )

    op.create_table('messages',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('conversation_id', sa.Uuid(), nullable=False),
        sa.Column('campaign_id', sa.Uuid(), nullable=True),
        sa.Column('direction', sa.String(20), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('external_message_id', sa.String(255), nullable=True),
        sa.Column('idempotency_key', sa.String(255), nullable=True),
        sa.Column('error_code', sa.String(120), nullable=True),
        sa.Column('error_detail', sa.Text(), nullable=True),
        sa.Column('intent_label', sa.String(40), nullable=True),
        sa.Column('intent_confidence', sa.Integer(), nullable=True),
        sa.Column('classification_engine', sa.String(40), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key'),
    )

    op.create_table('suppressions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('channel', sa.String(40), nullable=False),
        sa.Column('value_normalized', sa.String(500), nullable=False),
        sa.Column('reason', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('channel', 'value_normalized', name='uq_suppression_channel_value'),
    )

    op.create_table('audit_logs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('actor_user_id', sa.Uuid(), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(80), nullable=False),
        sa.Column('entity_id', sa.String(255), nullable=True),
        sa.Column('detail', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])

    op.create_table('scoring_profiles',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(120), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('weights', sa.JSON(), nullable=False),
        sa.Column('target_industries', sa.JSON(), nullable=False),
        sa.Column('target_cities', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    op.create_table('user_sessions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('refresh_jti', sa.String(64), nullable=False),
        sa.Column('refresh_token_hash', sa.String(64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rotated_from_session_id', sa.Uuid(), nullable=True),
        sa.Column('user_agent_hash', sa.String(64), nullable=True),
        sa.Column('ip_hash', sa.String(64), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('refresh_jti'),
    )

    op.create_table('sales_handoffs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('lead_id', sa.Uuid(), nullable=False),
        sa.Column('assigned_to_user_id', sa.Uuid(), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('reason', sa.String(255), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('campaign_leads',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('campaign_id', sa.Uuid(), nullable=False),
        sa.Column('lead_id', sa.Uuid(), nullable=False),
        sa.Column('contact_id', sa.Uuid(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('step', sa.Integer(), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('next_action_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_message_id', sa.Uuid(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['contact_id'], ['contact_points.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('campaign_id', 'lead_id', name='uq_campaign_lead'),
    )

    op.create_table('discovery_jobs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('source', sa.String(40), nullable=False),
        sa.Column('query', sa.String(255), nullable=False),
        sa.Column('city', sa.String(120), nullable=True),
        sa.Column('max_results', sa.Integer(), nullable=False),
        sa.Column('interval_minutes', sa.Integer(), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_result_count', sa.Integer(), nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('message_attempts',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('message_id', sa.Uuid(), nullable=False),
        sa.Column('attempt_no', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(40), nullable=False),
        sa.Column('outcome', sa.String(30), nullable=False),
        sa.Column('http_status', sa.Integer(), nullable=True),
        sa.Column('error_code', sa.String(120), nullable=True),
        sa.Column('error_detail', sa.Text(), nullable=True),
        sa.Column('retry_after_seconds', sa.Integer(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('outbox_events',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('topic', sa.String(80), nullable=False),
        sa.Column('aggregate_id', sa.String(64), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('available_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('lease_token', sa.String(64), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('topic', 'aggregate_id', name='uq_outbox_topic_aggregate'),
    )
    op.create_index('ix_outbox_due', 'outbox_events', ['status', 'available_at'])
    op.create_index('ix_outbox_lease', 'outbox_events', ['status', 'locked_until'])


def downgrade() -> None:
    op.drop_table('outbox_events')
    op.drop_table('message_attempts')
    op.drop_table('discovery_jobs')
    op.drop_table('campaign_leads')
    op.drop_table('sales_handoffs')
    op.drop_table('user_sessions')
    op.drop_table('scoring_profiles')
    op.drop_index('ix_audit_logs_action', 'audit_logs')
    op.drop_table('audit_logs')
    op.drop_table('suppressions')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('campaigns')
    op.drop_table('contact_points')
    op.drop_table('leads')
    op.drop_table('users')