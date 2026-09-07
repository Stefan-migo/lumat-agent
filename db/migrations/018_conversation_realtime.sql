-- 018_conversation_realtime.sql — active conversation summary read model.

CREATE INDEX idx_conversations_active_recency
    ON conversations (last_message_at DESC, id DESC)
    WHERE state IN ('bot', 'human') AND last_message_at IS NOT NULL;
