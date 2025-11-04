from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from backend.services.telegram_service import TelegramService
from backend.database.account_storage import AccountStorage

router = APIRouter()
telegram_service = TelegramService()
account_storage = AccountStorage()

class ChatSelectRequest(BaseModel):
    account_id: int
    chat_ids: List[int]

@router.get("/{account_id}")
async def get_chats(account_id: int):
    """Получает список чатов для аккаунта"""
    try:
        account = account_storage.get_account(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        if not account.get("is_connected"):
            raise HTTPException(status_code=400, detail="Account is not connected")
        
        chats = await telegram_service.get_chats(
            account["api_id"],
            account["api_hash"],
            account["phone_number"]
        )
        
        return {"chats": chats}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{account_id}/selected")
async def get_selected_chats(account_id: int):
    """Получает выбранные чаты для аккаунта"""
    try:
        account = account_storage.get_account(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        selected_chats = account_storage.get_selected_chats(account_id)
        return {"chat_ids": selected_chats}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/select")
async def select_chats(request: ChatSelectRequest):
    """Выбирает чаты для парсинга"""
    try:
        account = account_storage.get_account(request.account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        account_storage.set_selected_chats(request.account_id, request.chat_ids)
        return {"status": "success", "message": "Chats selected successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

