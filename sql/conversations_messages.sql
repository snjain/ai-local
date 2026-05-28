-- Conversations and messages tables for chat history
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS requests CASCADE;
DROP TABLE IF EXISTS conversations CASCADE;

CREATE TABLE conversations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID,
    session_id TEXT UNIQUE NOT NULL,
    title TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    last_message_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE messages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id TEXT REFERENCES conversations(session_id) ON DELETE CASCADE,
    computed_session_user_id TEXT,
    message JSONB NOT NULL,
    message_data TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

CREATE TABLE requests (
    id TEXT PRIMARY KEY,
    user_id UUID,
    user_query TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

CREATE INDEX idx_messages_session ON messages(session_id);
CREATE INDEX idx_messages_created ON messages(created_at);
CREATE INDEX idx_conversations_user ON conversations(user_id);
CREATE INDEX idx_conversations_session ON conversations(session_id);
CREATE INDEX idx_requests_user ON requests(user_id);
CREATE INDEX idx_requests_timestamp ON requests(timestamp);
