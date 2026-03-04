from fastapi import APIRouter, HTTPException, Request
from backend.services.parser_service import ParserService
from backend.database.supabase_client import SupabaseClient
import sys

router = APIRouter()
supabase_client = SupabaseClient()
parser_service = ParserService(supabase_client)


# ── Realtime endpoints ──────────────────────────────────────────────

@router.get("/realtime/status")
async def realtime_status(request: Request):
    rt = getattr(request.app.state, 'realtime_service', None)
    if not rt:
        return {"running": False, "accounts": 0, "messages_received": 0}
    return rt.status()


@router.post("/realtime/start")
async def realtime_start(request: Request):
    rt = getattr(request.app.state, 'realtime_service', None)
    if not rt:
        raise HTTPException(status_code=500, detail="Realtime service not initialized")
    if rt.is_running():
        return {"status": "info", "message": "Realtime already running"}
    try:
        await rt.start()
        return {"status": "success", "message": "Realtime started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/realtime/stop")
async def realtime_stop(request: Request):
    rt = getattr(request.app.state, 'realtime_service', None)
    if not rt:
        raise HTTPException(status_code=500, detail="Realtime service not initialized")
    if not rt.is_running():
        return {"status": "info", "message": "Realtime is not running"}
    await rt.stop()
    return {"status": "success", "message": "Realtime stopped"}


@router.post("/realtime/restart")
async def realtime_restart(request: Request):
    rt = getattr(request.app.state, 'realtime_service', None)
    if not rt:
        raise HTTPException(status_code=500, detail="Realtime service not initialized")
    await rt.restart()
    return {"status": "success", "message": "Realtime restarted"}

@router.post("/start")
async def start_parsing():
    """Запускает парсинг для всех подключенных аккаунтов"""
    try:
        print("\n" + "="*60, file=sys.stderr, flush=True)
        print("PARSER START REQUEST RECEIVED", file=sys.stderr, flush=True)
        print("="*60 + "\n", file=sys.stderr, flush=True)
        
        await parser_service.parse_all_accounts()
        
        print("\n" + "="*60, file=sys.stderr, flush=True)
        print("PARSER COMPLETED SUCCESSFULLY", file=sys.stderr, flush=True)
        print("="*60 + "\n", file=sys.stderr, flush=True)
        
        return {"status": "success", "message": "Parsing completed"}
    except Exception as e:
        print(f"\nPARSER ERROR: {str(e)}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_status():
    """Получает статус парсера"""
    is_running = parser_service.is_running()
    return {
        "is_running": is_running,
        "status": "running" if is_running else "idle",
        "message": "Parser is running" if is_running else "Parser is idle"
    }

@router.post("/stop")
async def stop_parsing():
    """Останавливает текущий процесс парсинга"""
    try:
        print("\n" + "="*60, file=sys.stderr, flush=True)
        print("PARSER STOP REQUEST RECEIVED", file=sys.stderr, flush=True)
        print("="*60 + "\n", file=sys.stderr, flush=True)
        
        stopped = parser_service.stop_parsing()
        
        if stopped:
            return {"status": "success", "message": "Parser stop signal sent"}
        else:
            return {"status": "info", "message": "Parser is not running"}
    except Exception as e:
        print(f"\nPARSER STOP ERROR: {str(e)}", file=sys.stderr, flush=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/schedule/status")
async def get_schedule_status(request: Request):
    """Получает статус автоматического парсинга и realtime"""
    try:
        auto_parsing_enabled = getattr(request.app.state, 'auto_parsing_enabled', True)
        scheduler = getattr(request.app.state, 'scheduler', None)
        
        if scheduler and scheduler.get_job('hourly_parse'):
            job = scheduler.get_job('hourly_parse')
            next_run = job.next_run_time.isoformat() if job.next_run_time else None
        else:
            next_run = None
        
        rt = getattr(request.app.state, 'realtime_service', None)
        rt_status = rt.status() if rt else {"running": False}
        
        return {
            "auto_parsing_enabled": auto_parsing_enabled,
            "next_run": next_run,
            "realtime": rt_status,
            "message": "Auto-parsing is enabled" if auto_parsing_enabled else "Auto-parsing is disabled"
        }
    except Exception as e:
        print(f"\nSCHEDULE STATUS ERROR: {str(e)}", file=sys.stderr, flush=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/schedule/pause")
async def pause_schedule(request: Request):
    """Приостанавливает автоматический парсинг (отключает scheduler)"""
    try:
        print("\n" + "="*60, file=sys.stderr, flush=True)
        print("AUTO-PARSING PAUSE REQUEST RECEIVED", file=sys.stderr, flush=True)
        print("="*60 + "\n", file=sys.stderr, flush=True)
        
        scheduler = getattr(request.app.state, 'scheduler', None)
        if not scheduler:
            raise HTTPException(status_code=500, detail="Scheduler not initialized")
        
        # Паузим задачу
        job = scheduler.get_job('hourly_parse')
        if job:
            scheduler.pause_job('hourly_parse')
            request.app.state.auto_parsing_enabled = False
            print("✅ Auto-parsing PAUSED", file=sys.stderr, flush=True)
            return {
                "status": "success",
                "message": "Auto-parsing paused. Scheduled parsing will not run.",
                "auto_parsing_enabled": False
            }
        else:
            return {
                "status": "info",
                "message": "No scheduled job found",
                "auto_parsing_enabled": False
            }
    except Exception as e:
        print(f"\nSCHEDULE PAUSE ERROR: {str(e)}", file=sys.stderr, flush=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/schedule/resume")
async def resume_schedule(request: Request):
    """Возобновляет автоматический парсинг (включает scheduler)"""
    try:
        print("\n" + "="*60, file=sys.stderr, flush=True)
        print("AUTO-PARSING RESUME REQUEST RECEIVED", file=sys.stderr, flush=True)
        print("="*60 + "\n", file=sys.stderr, flush=True)
        
        scheduler = getattr(request.app.state, 'scheduler', None)
        if not scheduler:
            raise HTTPException(status_code=500, detail="Scheduler not initialized")
        
        # Возобновляем задачу
        job = scheduler.get_job('hourly_parse')
        if job:
            scheduler.resume_job('hourly_parse')
            request.app.state.auto_parsing_enabled = True
            next_run = job.next_run_time.isoformat() if job.next_run_time else "calculating..."
            print(f"✅ Auto-parsing RESUMED. Next run: {next_run}", file=sys.stderr, flush=True)
            return {
                "status": "success",
                "message": f"Auto-parsing resumed. Next run at: {next_run}",
                "auto_parsing_enabled": True,
                "next_run": next_run
            }
        else:
            return {
                "status": "info",
                "message": "No scheduled job found",
                "auto_parsing_enabled": False
            }
    except Exception as e:
        print(f"\nSCHEDULE RESUME ERROR: {str(e)}", file=sys.stderr, flush=True)
        raise HTTPException(status_code=500, detail=str(e))
