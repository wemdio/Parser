# Telegram Chat Parser

Парсер сообщений из Telegram чатов с использованием пользовательских аккаунтов.

## Функционал

- Добавление нескольких Telegram аккаунтов через API hash, API ID и номер телефона
- Выбор чатов для парсинга
- Парсинг сообщений за последний час
- Автоматический запуск парсинга каждый час
- Сохранение данных в Supabase

## Установка

### Backend

```bash
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

## Настройка

### 1. Настройка Supabase

1. Создайте проект в [Supabase](https://supabase.com)
2. Выполните SQL скрипт из `database/schema.sql` в SQL Editor Supabase
3. Получите URL и API ключ из настроек проекта

### 2. Настройка окружения

Создайте файл `.env` в корне проекта:
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### 3. Получение Telegram API credentials

1. Перейдите на https://my.telegram.org
2. Войдите с вашим номером телефона
3. Создайте приложение и получите `api_id` и `api_hash`

### 4. Запуск приложения

**Backend:**
```bash
pip install -r requirements.txt
python run_backend.py
```

**Frontend (в новом терминале):**
```bash
cd frontend
npm install
npm start
```

Приложение будет доступно:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

## Структура проекта

- `backend/` - Python FastAPI приложение
- `frontend/` - React приложение
- `sessions/` - Сессии Telegram аккаунтов (автоматически создается)

