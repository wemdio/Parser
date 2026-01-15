from fastapi import APIRouter, HTTPException, Request
from typing import Optional
from backend.database.supabase_client import SupabaseClient

router = APIRouter()

# Глобальный клиент Supabase (будет инициализирован в main.py)
supabase_client: Optional[SupabaseClient] = None

def set_supabase_client(client: SupabaseClient):
    global supabase_client
    supabase_client = client

@router.get("/parsing-stats")
async def get_parsing_stats(
    limit: int = 100,
    session_id: Optional[str] = None,
    phone_number: Optional[str] = None,
    status: Optional[str] = None
):
    """
    Получает статистику парсинга
    
    Параметры:
    - limit: количество записей (по умолчанию 100)
    - session_id: фильтр по ID сессии
    - phone_number: фильтр по номеру телефона
    - status: фильтр по статусу ('success', 'error', 'skipped')
    """
    if not supabase_client or not supabase_client.client:
        raise HTTPException(status_code=503, detail="Supabase not available")
    
    try:
        # Базовый запрос
        query = supabase_client.client.table('parsing_logs').select("*")
        
        # Применяем фильтры
        if session_id:
            query = query.eq('parsing_session_id', session_id)
        if phone_number:
            query = query.eq('phone_number', phone_number)
        if status:
            query = query.eq('status', status)
        
        # Сортировка по времени (новые сверху)
        query = query.order('started_at', desc=True).limit(limit)
        
        result = query.execute()
        
        return {
            "success": True,
            "count": len(result.data),
            "logs": result.data
        }
    except Exception as e:
        print(f"Error getting parsing stats: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/parsing-sessions")
async def get_parsing_sessions(limit: int = 50):
    """
    Получает список уникальных сессий парсинга с агрегированной статистикой
    """
    if not supabase_client or not supabase_client.client:
        raise HTTPException(status_code=503, detail="Supabase not available")
    
    try:
        # Получаем все логи
        result = supabase_client.client.table('parsing_logs')\
            .select("*")\
            .order('started_at', desc=True)\
            .limit(limit * 10)\
            .execute()
        
        # Группируем по session_id
        sessions_dict = {}
        for log in result.data:
            session_id = log['parsing_session_id']
            if session_id not in sessions_dict:
                sessions_dict[session_id] = {
                    'session_id': session_id,
                    'started_at': log['started_at'],
                    'total_chats': 0,
                    'total_messages': 0,
                    'success_count': 0,
                    'error_count': 0,
                    'skipped_count': 0,
                    'accounts': set(),
                    'errors': []
                }
            
            session = sessions_dict[session_id]
            session['total_chats'] += 1
            session['total_messages'] += log.get('messages_saved', 0)
            session['accounts'].add(log['phone_number'])
            
            if log['status'] == 'success':
                session['success_count'] += 1
            elif log['status'] == 'error':
                session['error_count'] += 1
                session['errors'].append({
                    'chat_name': log['chat_name'],
                    'error_type': log.get('error_type'),
                    'error_message': log.get('error_message')
                })
            elif log['status'] == 'skipped':
                session['skipped_count'] += 1
        
        # Преобразуем set в list для JSON сериализации
        sessions = []
        for session in sessions_dict.values():
            session['accounts'] = list(session['accounts'])
            sessions.append(session)
        
        # Сортируем по времени
        sessions.sort(key=lambda x: x['started_at'], reverse=True)
        
        return {
            "success": True,
            "count": len(sessions[:limit]),
            "sessions": sessions[:limit]
        }
    except Exception as e:
        print(f"Error getting parsing sessions: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/parsing-stats/errors")
async def get_parsing_errors(limit: int = 100):
    """
    Получает только записи с ошибками
    """
    if not supabase_client or not supabase_client.client:
        raise HTTPException(status_code=503, detail="Supabase not available")
    
    try:
        result = supabase_client.client.table('parsing_logs')\
            .select("*")\
            .in_('status', ['error', 'skipped'])\
            .order('started_at', desc=True)\
            .limit(limit)\
            .execute()
        
        return {
            "success": True,
            "count": len(result.data),
            "errors": result.data
        }
    except Exception as e:
        print(f"Error getting parsing errors: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))
