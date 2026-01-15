# 🔧 CORS Fix для Production

## Проблема

В консоли браузера (F12) появлялись ошибки:
```
Access to XMLHttpRequest at 'https://wemdio-parser-ddaf.twc1.net/api/accounts/' 
from origin 'https://wemdio-parser-ddaf.twc1.net' has been blocked by CORS policy: 
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

**Причина**: Backend был настроен только для `localhost:3000`, а приложение развернуто на Timeweb с доменом `.twc1.net`.

---

## ✅ Что исправлено

### 1. Backend CORS настройки (`backend/main.py`)

**Было:**
```python
allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"]
```

**Стало:**
```python
allow_origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://wemdio-parser-828c.twc1.net",  # Frontend production
    "https://wemdio-parser-ddaf.twc1.net",  # Alternative frontend URL
    "https://wemdio-parser-0daf.twc1.net",  # Backend URL (for same-origin)
]
```

### 2. Frontend API конфигурация (`frontend/src/config.js`)

**Было:**
```javascript
const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';
```

**Стало:**
```javascript
const API_BASE = process.env.REACT_APP_API_URL || 
                window.location.origin.includes('twc1.net') 
                  ? 'https://wemdio-parser-0daf.twc1.net' 
                  : 'http://localhost:8000';
```

Теперь фронтенд автоматически определяет production окружение и использует правильный backend URL.

---

## 🚀 Как задеплоить на Timeweb

### Вариант 1: Автоматический редеплой (если настроен)

Если в Timeweb включен автоматический деплой из GitHub:
1. Изменения уже запушены в `main` ветку
2. Timeweb автоматически начнет редеплой (2-5 минут)
3. Проверьте статус в Timeweb Dashboard

### Вариант 2: Ручной редеплой через Timeweb Dashboard

#### Backend:
1. Откройте [Timeweb Dashboard](https://timeweb.cloud/my/apps)
2. Найдите приложение **Backend** (`wemdio-parser-0daf`)
3. Нажмите на него
4. Нажмите кнопку **"Redeploy"** или **"Restart"**
5. Дождитесь завершения деплоя (2-5 минут)

#### Frontend:
1. Откройте [Timeweb Dashboard](https://timeweb.cloud/my/apps)
2. Найдите приложение **Frontend** (`wemdio-parser-828c` или `wemdio-parser-ddaf`)
3. Нажмите на него
4. Нажмите кнопку **"Redeploy"**
5. Дождитесь завершения деплоя (2-5 минут)

### Вариант 3: Через терминал (если у вас установлен Timeweb CLI)

```bash
# Не применимо - используйте Dashboard
```

---

## 🧪 Как проверить, что исправление работает

### 1. Откройте фронтенд в браузере
```
https://wemdio-parser-828c.twc1.net
```
или
```
https://wemdio-parser-ddaf.twc1.net
```

### 2. Откройте DevTools (F12)
Нажмите `F12` → вкладка `Console`

### 3. Проверьте, что ошибок CORS нет
**Раньше было:**
```
❌ Access to XMLHttpRequest has been blocked by CORS policy
❌ net::ERR_FAILED 200 (OK)
```

**Теперь должно быть:**
```
✅ Аккаунты загружаются успешно
✅ Никаких ошибок CORS
✅ API запросы работают (статус 200 OK)
```

### 4. Проверьте Network tab
1. F12 → вкладка `Network`
2. Обновите страницу (`Ctrl+R`)
3. Найдите запрос к `/api/accounts/`
4. Проверьте:
   - **Status**: `200 OK` ✅
   - **Response Headers** должны содержать:
     ```
     Access-Control-Allow-Origin: https://wemdio-parser-ddaf.twc1.net
     Access-Control-Allow-Credentials: true
     ```

---

## 🐛 Troubleshooting

### Ошибка все еще появляется

**1. Очистите кэш браузера:**
- `Ctrl+Shift+Delete`
- Выберите "Кэш изображений и файлов"
- Нажмите "Удалить"

**2. Жесткое обновление:**
- `Ctrl+Shift+R` (Chrome/Edge)
- `Ctrl+F5` (Firefox)

**3. Проверьте, что backend перезапущен:**
```bash
curl https://wemdio-parser-0daf.twc1.net/health
```

Ответ должен быть:
```json
{
  "status": "ok",
  "version": "2.0-with-logging",
  "logging": "enabled"
}
```

**4. Проверьте логи backend в Timeweb Dashboard:**
1. Откройте Backend приложение
2. Перейдите в "Logs"
3. Найдите строку:
   ```
   >>> BACKEND STARTED <<<
   ```

Если нет - значит backend не запустился. Проверьте ошибки в логах.

### Frontend не обновляется

**Причина**: React приложение закешировано в браузере.

**Решение**:
1. Откройте DevTools (F12)
2. Правый клик на кнопку обновления в браузере
3. Выберите "Empty Cache and Hard Reload"

### Другие URL на Timeweb

Если у вас другие URL (не те, что в коде):

1. **Откройте Timeweb Dashboard**
2. **Найдите свои приложения** и их URL
3. **Обновите** `backend/main.py`:
   ```python
   allow_origins=[
       # ... localhost urls ...
       "https://ваш-frontend-url.twc1.net",
       "https://ваш-backend-url.twc1.net",
   ]
   ```
4. **Обновите** `frontend/src/config.js`:
   ```javascript
   const API_BASE = 'https://ваш-backend-url.twc1.net';
   ```
5. **Закоммитьте и запушьте**:
   ```bash
   git add .
   git commit -m "Update Timeweb URLs"
   git push origin main
   ```
6. **Редеплойте** оба приложения

---

## 📊 Статус

- ✅ Изменения закоммичены: `0360c52`
- ✅ Изменения запушены в GitHub: `main` branch
- ⏳ Ожидается редеплой на Timeweb (вручную или автоматически)

---

## 📝 Коммит

**Hash**: `0360c52`  
**Message**: "Fix CORS settings for Timeweb production deployment"  
**Дата**: 4 ноября 2025  
**Измененные файлы**:
- `backend/main.py` (+7 строк)
- `frontend/src/config.js` (+6 строк)

---

## 🎯 Следующий шаг

**Перезапустите Backend и Frontend на Timeweb через Dashboard**, затем проверьте, что ошибки CORS исчезли!





