"""enterprise hardening

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-11
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('ix_user_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_index('ix_user_sessions_expires_at', 'user_sessions', ['expires_at'])
    op.create_index('ix_user_sessions_revoked_at', 'user_sessions', ['revoked_at'])
    op.create_index('ix_user_sessions_rotation', 'user_sessions', ['rotated_from_session_id'])

    op.create_index('ix_user_sessions_ua_ip', 'user_sessions', ['user_agent_hash', 'ip_hash'])

    op.create_index('ix_messages_external_id', 'messages', ['external_message_id'])
    op.create_index('ix_messages_intent', 'messages', ['intent_label'])

    op.create_index('ix_discovery_jobs_source', 'discovery_jobs', ['source'])
    op.create_index('ix_discovery_jobs_enabled', 'discovery_jobs', ['is_enabled'])
    op.create_index('ix_discovery_jobs_next_run', 'discovery_jobs', ['next_run_at'])

    op.create_index('ix_sales_handoffs_status', 'sales_handoffs', ['status'])
    op.create_index('ix_sales_handoffs_assignee', 'sales_handoffs', ['assigned_to_user_id'])

    op.create_index('ix_campaign_leads_campaign', 'campaign_leads', ['campaign_id'])
    op.create_index('ix_campaign_leads_lead', 'campaign_leads', ['lead_id'])
    op.create_index('ix_campaign_leads_status', 'campaign_leads', ['status'])
    op.create_index('ix_campaign_leads_next_action', 'campaign_leads', ['next_action_at'])

    op.create_index('ix_message_attempts_provider', 'message_attempts', ['provider'])
    op.create_index('ix_message_attempts_outcome', 'message_attempts', ['outcome'])

    op.create_index('ix_outbox_events_topic', 'outbox_events', ['topic'])
    op.create_index('ix_outbox_events_aggregate', 'outbox_events', ['aggregate_id'])
    op.create_index('ix_outbox_events_lease_token', 'outbox_events', ['lease_token'])

    op.create_index('ix_leads_source', 'leads', ['source'])
    op.create_index('ix_leads_source_external', 'leads', ['source_external_id'])

    op.create_index('ix_contact_points_channel', 'contact_points', ['channel'])
    op.create_index('ix_contact_points_normalized', 'contact_points', ['value_normalized'])

    op.create_index('ix_conversations_lead', 'conversations', ['lead_id'])
    op.create_index('ix_conversations_channel', 'conversations', ['channel'])


def downgrade() -> None:
    op.drop_index('ix_conversations_channel', 'conversations')
    op.drop_index('ix_conversations_lead', 'conversations')
    op.drop_index('ix_contact_points_normalized', 'contact_points')
    op.drop_index('ix_contact_points_channel', 'contact_points')
    op.drop_index('ix_leads_source_external', 'leads')
    op.drop_index('ix_leads_source', 'leads')
    op.drop_index('ix_outbox_events_lease_token', 'outbox_events')
    op.drop_index('ix_outbox_events_aggregate', 'outbox_events')
    op.drop_index('ix_outbox_events_topic', 'outbox_events')
    op.drop_index('ix_message_attempts_outcome', 'message_attempts')
    op.drop_index('ix_message_attempts_provider', 'message_attempts')
    op.drop_index('ix_campaign_leads_next_action', 'campaign_leads')
    op.drop_index('ix_campaign_leads_status', 'campaign_leads')
    op.drop_index('ix_campaign_leads_lead', 'campaign_leads')
    op.drop_index('ix_campaign_leads_campaign', 'campaign_leads')
    op.drop_index('ix_sales_handoffs_assignee', 'sales_handoffs')
    op.drop_index('ix_sales_handoffs_status', 'sales_handoffs')
    op.drop_index('ix_discovery_jobs_next_run', 'discovery_jobs')
    op.drop_index('ix_discovery_jobs_enabled', 'discovery_jobs')
    op.drop_index('ix_discovery_jobs_source', 'discovery_jobs')
    op.drop_index('ix_messages_intent', 'messages')
    op.drop_index('ix_messages_external_id', 'messages')
    op.drop_index('ix_user_sessions_ua_ip', 'user_sessions')
    op.drop_index('ix_user_sessions_rotation', 'user_sessions')
    op.drop_index('ix_user_sessions_revoked_at', 'user_sessions')
    op.drop_index('ix_user_sessions_expires_at', 'user_sessions')
    op.drop_index('ix_user_sessions_user_id', 'user_sessions')