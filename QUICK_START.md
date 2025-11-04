# Быстрый старт

## Проблема: ничего не отображается на localhost:3000

### Решение:

1. **Установите зависимости frontend** (если еще не установлены):
```bash
cd frontend
npm install
```

2. **Запустите backend** (в первом терминале):
```bash
# Из корня проекта
python run_backend.py
```

Вы должны увидеть:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

3. **Запустите frontend** (во втором терминале):
```bash
cd frontend
npm start
```

4. **Откройте браузер:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

### Если backend не запускается:

1. Проверьте установку зависимостей:
```bash
pip install -r requirements.txt
```

2. Создайте файл `.env` в корне проекта (можно пока без реальных данных):
```
SUPABASE_URL=https://placeholder.supabase.co
SUPABASE_KEY=placeholder_key
```

Приложение будет работать, но сообщения не будут сохраняться в базу до настройки Supabase.

### Если frontend показывает ошибку подключения к API:

- Убедитесь, что backend запущен на порту 8000
- Проверьте консоль браузера (F12) на наличие ошибок CORS
- Убедитесь, что в `frontend/src/App.js` правильный URL: `http://localhost:8000/api`

