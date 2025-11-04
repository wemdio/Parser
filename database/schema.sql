-- Создание таблицы messages в Supabase
-- Выполните этот SQL в Supabase SQL Editor

CREATE TABLE IF NOT EXISTS messages (
    id BIGSERIAL PRIMARY KEY,
    message_time TIMESTAMP WITH TIME ZONE NOT NULL,
    chat_name TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    username TEXT,
    bio TEXT,
    message TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Создание индексов для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_message_time ON messages(message_time);
CREATE INDEX IF NOT EXISTS idx_chat_name ON messages(chat_name);
CREATE INDEX IF NOT EXISTS idx_username ON messages(username);

-- Включение Row Level Security (опционально)
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Создание политики для чтения (если нужно ограничить доступ)
-- CREATE POLICY "Allow all operations" ON messages FOR ALL USING (true);

