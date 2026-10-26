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

## Protected Chat Onboarding

The `/api/chat-onboarding` routes are disabled unless a dedicated random
`PARSER_CHAT_ADMIN_TOKEN` (at least 32 characters) is configured. They require
`Authorization: Bearer <token>` on every request. This protection applies only
to the new routes; it does not change authentication on legacy API routes.

Set `PARSER_JOIN_ALLOWED_USERNAMES` to a comma-separated list of public group
usernames. An empty list denies all joins. For the approved rollout:

```text
ozon_fbs,mpbestchat,pdn152fz,kii187fz,camunda_bpm,ctorecordschat,refuelchat,gilforum
```

Deploy only to parser app **242317**, with app-local variables, not global
variables. Do not change backend 223617, schedules, client qualification settings,
or existing chat selections. Snapshot `/api/chats/{account_id}/selected` before
deployment and compare after it. Never export Telegram session files to another
running process or machine.

- `GET /api/chat-onboarding/status` returns account IDs, active chat filters,
  cooldown and per-chat messages received since process start. It does not
  return phone numbers, Telegram API credentials or sessions. Received counters
  are not proof of successful database insertion; check saved messages separately.
- `POST /api/chat-onboarding/join` accepts
  `{"account_id":4,"username":"ozon_fbs"}`. Only a connected realtime owner can
  perform the operation. No extra Telegram connection is created.
- Membership is checked before and after joining. Confirmed membership adds
  the chat to the saved selection and live filter without restarting clients.
  Other selections are preserved; a chat selected on another account is reported
  without joining it again.
- Only consider a chat ready when `selected`, `listening` and `persisted` are
  all true. `persisted:false` means the local addition worked but its database
  backup failed; retry the same account and username before any redeploy.
- `pending_approval` is not connected. Wait for administrator approval, then
  repeat the same request. Do not use another account to circumvent moderation.
- Calls are serialized and have a minimum 10-second spacing. On HTTP 429 honor
  `Retry-After`; do not rotate accounts. On HTTP 504 the remote result may be
  unknown: retry the same account and username to reconcile membership.
- Emptying the allowlist disables future joins without removing existing chats.
  Removing the administrator token disables both onboarding routes after restart.

Tests use fake Telegram clients and temporary account storage, not live sessions:

```bash
pip install -r requirements.txt -r requirements-test.txt
python -m unittest discover -s tests -v
```

