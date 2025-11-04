# Инструкция по деплою на timeweb.cloud

## Подготовка

1. Создайте проект в Supabase и выполните SQL скрипт из `database/schema.sql`

2. Получите SUPABASE_URL и SUPABASE_KEY из настроек проекта Supabase

3. Создайте `.env` файл с переменными окружения:
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

## Локальный запуск

### Backend:
```bash
pip install -r requirements.txt
python run_backend.py
```

### Frontend:
```bash
cd frontend
npm install
npm start
```

## Деплой через Docker

1. Соберите образы:
```bash
docker-compose build
```

2. Запустите контейнеры:
```bash
docker-compose up -d
```

## Деплой на timeweb.cloud

### Вариант 1: Через Docker

1. Загрузите проект на сервер (через git или FTP)

2. Настройте переменные окружения на сервере:
   - В панели timeweb.cloud создайте переменные SUPABASE_URL и SUPABASE_KEY

3. Запустите через docker-compose:
```bash
docker-compose up -d
```

### Вариант 2: Прямой запуск

1. Установите зависимости:
```bash
pip install -r requirements.txt
cd frontend && npm install && npm run build
```

2. Настройте веб-сервер (nginx/apache) для раздачи frontend/build

3. Запустите backend:
```bash
python run_backend.py
```

## Важные замечания

- Сессии Telegram хранятся в директории `sessions/` - убедитесь, что она доступна для записи
- Файл `accounts.json` содержит данные аккаунтов - храните его в безопасности
- Настройте автоматический запуск backend при перезагрузке сервера (через systemd или supervisor)

## Настройка systemd для автозапуска

Создайте файл `/etc/systemd/system/telegram-parser.service`:

```ini
[Unit]
Description=Telegram Parser Backend
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/Parser
Environment="PATH=/usr/bin:/usr/local/bin"
EnvironmentFile=/path/to/.env
ExecStart=/usr/bin/python3 /path/to/run_backend.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Затем:
```bash
sudo systemctl enable telegram-parser
sudo systemctl start telegram-parser
```

