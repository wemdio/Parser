-- Создание таблицы messages в Supabase
-- Выполните этот SQL в Supabase SQL Editor

CREATE TABLE IF NOT EXISTS messages (
    id BIGSERIAL PRIMARY KEY,
    message_time TIMESTAMP WITH TIME ZONE NOT NULL,
    chat_name TEXT NOT NULL,
    user_id BIGINT,
    first_name TEXT,
    last_name TEXT,
    username TEXT,
    bio TEXT,
    profile_link TEXT,
    message TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Создание индексов для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_message_time ON messages(message_time);
CREATE INDEX IF NOT EXISTS idx_chat_name ON messages(chat_name);
CREATE INDEX IF NOT EXISTS idx_username ON messages(username);
CREATE INDEX IF NOT EXISTS idx_user_id ON messages(user_id);

-- Включение Row Level Security
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Политики доступа
DROP POLICY IF EXISTS "Allow all read operations" ON messages;
CREATE POLICY "Allow all read operations" ON messages FOR SELECT USING (true);

DROP POLICY IF EXISTS "Allow all insert operations" ON messages;
CREATE POLICY "Allow all insert operations" ON messages FOR INSERT WITH CHECK (true);

