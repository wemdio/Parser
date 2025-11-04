from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.services.telegram_service import TelegramService
from backend.database.account_storage import AccountStorage
import os

router = APIRouter()
telegram_service = TelegramService()
account_storage = AccountStorage()

class AccountCreateRequest(BaseModel):
    api_id: str
    api_hash: str
    phone_number: str
    name: str = None

class VerifyCodeRequest(BaseModel):
    account_id: int
    phone_code: str
    phone_code_hash: str
    password: str = None

@router.post("/add")
async def add_account(account_data: AccountCreateRequest):
    """Добавляет новый аккаунт и запрашивает код подтверждения"""
    try:
        import sys
        print(f"\n{'#'*60}", file=sys.stderr, flush=True)
        print(f"### ADD ACCOUNT REQUEST RECEIVED ###", file=sys.stderr, flush=True)
        print(f"### Phone: {account_data.phone_number}", file=sys.stderr, flush=True)
        print(f"{'#'*60}\n", file=sys.stderr, flush=True)
        
        print(f"Received account data: api_id={account_data.api_id}, phone={account_data.phone_number}")
        
        # Валидация входных данных
        api_id_str = (account_data.api_id or "").strip()
        api_hash_str = (account_data.api_hash or "").strip()
        phone_str = (account_data.phone_number or "").strip()
        
        if not api_id_str:
            raise HTTPException(status_code=400, detail="API ID is required")
        if not api_hash_str:
            raise HTTPException(status_code=400, detail="API Hash is required")
        if not phone_str:
            raise HTTPException(status_code=400, detail="Phone number is required")
        
        # Проверяем, что API ID - это число
        try:
            api_id_int = int(api_id_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="API ID must be a number")
        
        # Проверяем формат номера телефона
        phone = phone_str.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        
        # Номер должен начинаться с + или быть валидным
        if not phone.startswith("+"):
            if phone.startswith("8") and len(phone) == 11:
                # Российский номер без +, преобразуем
                phone = "+7" + phone[1:]
            elif phone.isdigit() and len(phone) >= 10:
                raise HTTPException(
                    status_code=400, 
                    detail="Phone number must start with '+' and country code (e.g., +79991234567)"
                )
            else:
                raise HTTPException(
                    status_code=400, 
                    detail="Phone number must start with '+' and country code (e.g., +79991234567)"
                )
        
        name = (account_data.name or "").strip() if account_data.name else None
        
        # Проверяем, существует ли аккаунт с таким номером
        existing_account = None
        all_accounts = account_storage.get_all_accounts()
        for acc in all_accounts:
            if acc.get("phone_number") == phone:
                existing_account = acc
                break
        
        if existing_account:
            # Если аккаунт существует и не подключен, пытаемся запросить новый код
            if not existing_account.get("is_connected", False):
                # Попытаемся запросить новый код для существующего аккаунта
                try:
                    result = await telegram_service.connect_account(
                        existing_account["api_id"],
                        existing_account["api_hash"],
                        phone
                    )
                    
                    if result.get("status") == "already_connected":
                        account_storage.update_account_connection(existing_account["id"], True)
                        return {
                            "account_id": existing_account["id"],
                            "status": "already_connected",
                            "message": "Account already connected"
                        }
                    elif result.get("phone_code_hash"):
                        return {
                            "account_id": existing_account["id"],
                            "phone_code_hash": result["phone_code_hash"],
                            "needs_password": result.get("needs_password", False),
                            "message": "New code sent for existing account"
                        }
                except Exception as e:
                    print(f"Error requesting new code for existing account: {e}")
            
            # Если не удалось запросить код, возвращаем информацию о существующем аккаунте
            return {
                "account_id": existing_account["id"],
                "status": "already_exists",
                "is_connected": existing_account.get("is_connected", False),
                "message": f"Аккаунт с номером {phone} уже существует",
                "existing_account": {
                    "id": existing_account["id"],
                    "name": existing_account.get("name"),
                    "phone_number": existing_account.get("phone_number"),
                    "is_connected": existing_account.get("is_connected", False)
                }
            }
        
        # Удаляем старую сессию перед добавлением нового аккаунта
        from backend.services.telegram_service import TelegramService
        temp_service = TelegramService()
        session_path = temp_service.get_session_path(phone)
        session_file = session_path + ".session"
        
        for path in [session_path, session_file, session_path + ".session"]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                    print(f"Removed old session file: {path}")
                except Exception as e:
                    print(f"Could not remove session file {path}: {e}")
        
        account_id = account_storage.add_account({
            "api_id": api_id_str,
            "api_hash": api_hash_str,
            "phone_number": phone,
            "name": name
        })
        
        result = await telegram_service.connect_account(
            api_id_str,
            api_hash_str,
            phone
        )
        
        if result.get("status") == "already_connected":
            account_storage.update_account_connection(account_id, True)
            return {
                "account_id": account_id,
                "status": "already_connected",
                "message": "Account already connected"
            }
        
        return {
            "account_id": account_id,
            "phone_code_hash": result["phone_code_hash"],
            "needs_password": result.get("needs_password", False)
        }
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        print(f"Error adding account: {error_msg}")
        print(f"Error type: {error_type}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/verify")
async def verify_code(request: VerifyCodeRequest):
    """Проверяет код подтверждения"""
    try:
        import sys
        print(f"\n{'#'*60}", file=sys.stderr, flush=True)
        print(f"### VERIFY REQUEST RECEIVED ###", file=sys.stderr, flush=True)
        print(f"### Account ID: {request.account_id}", file=sys.stderr, flush=True)
        print(f"### Phone code: {request.phone_code}", file=sys.stderr, flush=True)
        print(f"### Code hash: {request.phone_code_hash[:20]}...", file=sys.stderr, flush=True)
        print(f"{'#'*60}\n", file=sys.stderr, flush=True)
        
        account = account_storage.get_account(request.account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        print(f"Account found: {account.get('phone_number')}", file=sys.stderr, flush=True)
        
        success = await telegram_service.verify_code(
            account["api_id"],
            account["api_hash"],
            account["phone_number"],
            request.phone_code,
            request.phone_code_hash,
            request.password
        )
        
        if success:
            account_storage.update_account_connection(request.account_id, True)
            return {"status": "success", "message": "Account connected successfully"}
        else:
            raise HTTPException(status_code=400, detail="Verification failed")
    
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        # Проверяем тип ошибки для правильного статуса
        if "PHONE_CODE_EXPIRED" in error_msg or "expired" in error_msg.lower():
            raise HTTPException(status_code=400, detail=error_msg)
        elif "Invalid verification code" in error_msg or "Invalid" in error_msg:
            raise HTTPException(status_code=400, detail=error_msg)
        elif "password required" in error_msg.lower():
            raise HTTPException(status_code=400, detail=error_msg)
        else:
            raise HTTPException(status_code=500, detail=error_msg)

@router.get("/")
async def get_accounts():
    """Получает список всех аккаунтов"""
    accounts = account_storage.get_all_accounts()
    return {"accounts": accounts}

@router.get("/{account_id}")
async def get_account(account_id: int):
    """Получает информацию об аккаунте по ID"""
    account = account_storage.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account

@router.delete("/{account_id}")
async def delete_account(account_id: int):
    """Удаляет аккаунт"""
    try:
        account = account_storage.get_account(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Получаем путь к файлу сессии для удаления
        phone_number = account.get("phone_number")
        if phone_number:
            from backend.services.telegram_service import TelegramService
            telegram_service = TelegramService()
            session_path = telegram_service.get_session_path(phone_number)
            import os
            if os.path.exists(session_path):
                try:
                    os.remove(session_path)
                    print(f"Deleted session file: {session_path}")
                except Exception as e:
                    print(f"Warning: Could not delete session file: {e}")
        
        success = account_storage.delete_account(account_id)
        if success:
            return {"status": "success", "message": "Account deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Account not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{account_id}/check-status")
async def check_account_status(account_id: int):
    """Проверяет статус подключения аккаунта"""
    try:
        account = account_storage.get_account(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Проверяем, есть ли валидная сессия
        try:
            result = await telegram_service.connect_account(
                account["api_id"],
                account["api_hash"],
                account["phone_number"]
            )
            
            if result.get("status") == "already_connected":
                account_storage.update_account_connection(account_id, True)
                return {"is_connected": True, "status": "connected"}
            else:
                account_storage.update_account_connection(account_id, False)
                return {"is_connected": False, "status": "not_connected"}
        except Exception as e:
            account_storage.update_account_connection(account_id, False)
            return {"is_connected": False, "status": "error", "message": str(e)}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

