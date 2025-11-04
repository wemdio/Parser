# Перезапуск Backend

## Шаги:

### 1. Остановите старый backend

В терминале где запущен backend нажмите:
```
Ctrl+C
```

### 2. Запустите backend заново

```powershell
cd C:\Users\wemd1\Desktop\Parser
$env:PYTHONIOENCODING="utf-8"
python run_backend.py
```

### 3. Убедитесь что backend запущен

Вы должны увидеть:
```
======================================================================
>>> BACKEND STARTED <<<
>>> Listening on http://localhost:8000
>>> LOGS WILL APPEAR BELOW
======================================================================
```

### 4. Проверьте что backend отвечает

В консоли браузера (F12) выполните:
```javascript
fetch('http://localhost:8000/').then(r => r.json()).then(console.log)
```

Должны увидеть:
```json
{message: "Telegram Parser API"}
```

## Если backend не запускается

1. Проверьте, что порт 8000 свободен:
```powershell
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
```

2. Если порт занят, найдите и остановите процесс:
```powershell
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process -Force
```

3. Попробуйте запустить снова

