# ПРОВЕРКА SUPABASE

## 1. Откройте Supabase Dashboard

Перейдите: https://supabase.com/dashboard/project/liavhyhyzqadilfmicba

## 2. Проверьте таблицу messages

1. В левом меню → **Table Editor**
2. Найдите таблицу **messages**

### Если таблицы НЕТ:

1. В левом меню → **SQL Editor**
2. Нажмите **New query**
3. Вставьте код:

```sql
CREATE TABLE IF NOT EXISTS messages (
    id BIGSERIAL PRIMARY KEY,
    message_time TIMESTAMPTZ NOT NULL,
    chat_name TEXT,
    first_name TEXT,
    last_name TEXT,
    username TEXT,
    bio TEXT,
    message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Индекс для быстрого поиска по времени
CREATE INDEX IF NOT EXISTS idx_messages_time ON messages(message_time DESC);

-- Индекс для поиска по чату
CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(chat_name);
```

4. Нажмите **Run** (или F5)
5. Должно появиться: **Success. No rows returned**

## 3. Проверьте что таблица создана

1. Вернитесь в **Table Editor**
2. Должна появиться таблица **messages**

## 4. Перезапустите backend

```
Ctrl+C (в терминале backend)
python run_backend.py
```

Должны увидеть:
```
Initializing Supabase client...
URL: https://liavhyhyzqadilfmicba.supabase.co
Supabase client initialized successfully!
Table 'messages' exists
```

## 5. Запустите парсинг снова

В браузере → **Запустить парсинг**

Должны увидеть в backend:
```
>>> Time limit for messages: 2024-XX-XX XX:XX:XX UTC
>>> Will parse messages from last 1 hour(s)
>>> Chat 'название': found X messages in last hour, skipped Y old messages
Inserting X messages to Supabase...
Successfully inserted X messages!
```

## 6. Проверьте данные

1. **Table Editor** → **messages**
2. Должны появиться записи с сообщениями за последний час

