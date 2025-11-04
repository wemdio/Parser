from fastapi import APIRouter, HTTPException
from backend.services.parser_service import ParserService
from backend.database.supabase_client import SupabaseClient

router = APIRouter()
supabase_client = SupabaseClient()
parser_service = ParserService(supabase_client)

@router.post("/start")
async def start_parsing():
    """Запускает парсинг для всех подключенных аккаунтов"""
    try:
        import sys
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
    return {"status": "running", "message": "Parser is running"}

