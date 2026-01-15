-- Таблица для хранения статистики парсинга
-- Выполните этот SQL в Supabase SQL Editor

CREATE TABLE IF NOT EXISTS parsing_logs (
    id BIGSERIAL PRIMARY KEY,
    
    -- Информация о сессии парсинга
    parsing_session_id UUID NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    
    -- Информация об аккаунте и чате
    phone_number TEXT NOT NULL,
    chat_id BIGINT NOT NULL,
    chat_name TEXT NOT NULL,
    
    -- Статистика
    messages_found INTEGER DEFAULT 0,
    messages_saved INTEGER DEFAULT 0,
    messages_skipped INTEGER DEFAULT 0,
    
    -- Статус и ошибки
    status TEXT NOT NULL DEFAULT 'success', -- 'success', 'error', 'skipped'
    error_type TEXT, -- 'FLOOD_WAIT', 'PeerIdInvalid', 'Other'
    error_message TEXT,
    
    -- Дополнительная информация
    hours_back INTEGER DEFAULT 1,
    execution_time_seconds FLOAT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_parsing_logs_session ON parsing_logs(parsing_session_id);
CREATE INDEX IF NOT EXISTS idx_parsing_logs_started_at ON parsing_logs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_parsing_logs_phone ON parsing_logs(phone_number);
CREATE INDEX IF NOT EXISTS idx_parsing_logs_chat ON parsing_logs(chat_id);
CREATE INDEX IF NOT EXISTS idx_parsing_logs_status ON parsing_logs(status);

-- Включение Row Level Security (опционально)
ALTER TABLE parsing_logs ENABLE ROW LEVEL SECURITY;

-- Удаляем политики если существуют (чтобы избежать ошибок)
DROP POLICY IF EXISTS "Allow all read operations" ON parsing_logs;
DROP POLICY IF EXISTS "Allow all insert operations" ON parsing_logs;

-- Политика для чтения всех записей (если используете анонимный ключ)
CREATE POLICY "Allow all read operations" ON parsing_logs FOR SELECT USING (true);

-- Политика для записи всех записей (если используете анонимный ключ)
CREATE POLICY "Allow all insert operations" ON parsing_logs FOR INSERT WITH CHECK (true);
