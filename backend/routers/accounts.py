from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from backend.services.telegram_service import TelegramService
from backend.database.account_storage import AccountStorage
import os
import shutil

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
                # ВАЖНО: Удаляем старую невалидную сессию перед запросом нового кода
                from backend.services.telegram_service import TelegramService
                temp_service = TelegramService()
                session_path = temp_service.get_session_path(phone)
                for path in [session_path, session_path + ".session", f"{session_path}.session"]:
                    if os.path.exists(path):
                        try:
                            os.remove(path)
                            print(f"Removed old session for existing account: {path}")
                        except Exception as e:
                            print(f"Could not remove session {path}: {e}")
                
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

@router.post("/upload-session")
async def upload_session(
    session_file: UploadFile = File(...),
    api_id: str = Form(...),
    api_hash: str = Form(...),
    phone_number: str = Form(...),
    name: str = Form(None)
):
    """
    Загружает готовый файл сессии и добавляет аккаунт.
    Используется когда нельзя получить код подтверждения на сервере.
    """
    import sys
    print(f"\n{'#'*60}", file=sys.stderr, flush=True)
    print(f"### UPLOAD SESSION REQUEST ###", file=sys.stderr, flush=True)
    print(f"### Phone: {phone_number}", file=sys.stderr, flush=True)
    print(f"### File: {session_file.filename}", file=sys.stderr, flush=True)
    print(f"{'#'*60}\n", file=sys.stderr, flush=True)
    
    try:
        # Валидация
        api_id_str = (api_id or "").strip()
        api_hash_str = (api_hash or "").strip()
        phone_str = (phone_number or "").strip()
        
        if not api_id_str:
            raise HTTPException(status_code=400, detail="API ID is required")
        if not api_hash_str:
            raise HTTPException(status_code=400, detail="API Hash is required")
        if not phone_str:
            raise HTTPException(status_code=400, detail="Phone number is required")
        
        # Проверяем API ID
        try:
            api_id_int = int(api_id_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="API ID must be a number")
        
        # Нормализуем номер телефона
        phone = phone_str.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if not phone.startswith("+"):
            if phone.startswith("8") and len(phone) == 11:
                phone = "+7" + phone[1:]
            else:
                raise HTTPException(
                    status_code=400, 
                    detail="Phone number must start with '+' (e.g., +79991234567)"
                )
        
        # Создаем папку sessions если нет
        os.makedirs("sessions", exist_ok=True)
        
        # Формируем имя файла сессии
        phone_clean = phone.replace("+", "")
        session_filename = f"{phone_clean}.session"
        session_path = os.path.join("sessions", session_filename)
        
        # Удаляем старую сессию если есть
        for ext in ["", ".session"]:
            old_path = f"sessions/{phone_clean}{ext}"
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                    print(f"Removed old session: {old_path}", file=sys.stderr, flush=True)
                except Exception as e:
                    print(f"Could not remove {old_path}: {e}", file=sys.stderr, flush=True)
        
        # Сохраняем загруженный файл
        print(f"Saving session to: {session_path}", file=sys.stderr, flush=True)
        with open(session_path, "wb") as buffer:
            content = await session_file.read()
            buffer.write(content)
        
        print(f"Session file saved, size: {len(content)} bytes", file=sys.stderr, flush=True)
        
        # Проверяем валидность сессии
        from pyrogram import Client
        
        test_client = Client(
            f"sessions/{phone_clean}",
            api_id=api_id_int,
            api_hash=api_hash_str
        )
        
        try:
            print("Testing session validity...", file=sys.stderr, flush=True)
            await test_client.start()
            me = await test_client.get_me()
            await test_client.stop()
            
            print(f"Session valid! User: {me.first_name} (@{me.username})", file=sys.stderr, flush=True)
            
            # Проверяем существующий аккаунт
            existing_account = None
            all_accounts = account_storage.get_all_accounts()
            for acc in all_accounts:
                if acc.get("phone_number") == phone:
                    existing_account = acc
                    break
            
            if existing_account:
                # Обновляем существующий аккаунт
                account_storage.update_account_connection(existing_account["id"], True)
                account_id = existing_account["id"]
                print(f"Updated existing account {account_id}", file=sys.stderr, flush=True)
            else:
                # Создаем новый аккаунт
                account_id = account_storage.add_account({
                    "api_id": api_id_str,
                    "api_hash": api_hash_str,
                    "phone_number": phone,
                    "name": name.strip() if name else None,
                    "is_connected": True
                })
                # Сразу помечаем как подключенный
                account_storage.update_account_connection(account_id, True)
                print(f"Created new account {account_id}", file=sys.stderr, flush=True)
            
            return {
                "status": "success",
                "account_id": account_id,
                "message": f"Session uploaded successfully! Account: {me.first_name} (@{me.username or 'no username'})",
                "user_info": {
                    "id": me.id,
                    "first_name": me.first_name,
                    "last_name": me.last_name,
                    "username": me.username
                }
            }
            
        except Exception as e:
            # Сессия невалидна - удаляем файл
            if os.path.exists(session_path):
                os.remove(session_path)
            
            error_msg = str(e)
            print(f"Session validation failed: {error_msg}", file=sys.stderr, flush=True)
            
            if "AUTH_KEY" in error_msg or "not registered" in error_msg.lower():
                raise HTTPException(
                    status_code=400, 
                    detail="Session file is invalid or expired. Please create a new session locally."
                )
            else:
                raise HTTPException(status_code=400, detail=f"Session validation failed: {error_msg}")
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Upload session error: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

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
    """Проверяет статус подключения аккаунта - только проверка, без запроса кода"""
    import sys
    try:
        account = account_storage.get_account(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        phone = account.get("phone_number", "")
        phone_clean = phone.replace("+", "").replace(" ", "").replace("-", "")
        
        # Проверяем наличие файла сессии
        session_path = f"sessions/{phone_clean}.session"
        if not os.path.exists(session_path):
            print(f"check-status: No session file for {phone}", file=sys.stderr, flush=True)
            account_storage.update_account_connection(account_id, False)
            return {"is_connected": False, "status": "no_session"}
        
        # Пробуем подключиться с существующей сессией (без запроса кода!)
        from pyrogram import Client
        import asyncio
        
        client = None
        try:
            client = Client(
                f"sessions/{phone_clean}",
                api_id=int(account["api_id"]),
                api_hash=account["api_hash"]
            )
            
            await client.start()
            me = await client.get_me()
            await client.stop()
            
            # Даём время на освобождение файла
            await asyncio.sleep(0.5)
            
            print(f"check-status: Session valid for {phone} - {me.first_name}", file=sys.stderr, flush=True)
            account_storage.update_account_connection(account_id, True)
            return {"is_connected": True, "status": "connected", "user": me.first_name}
            
        except Exception as e:
            error_msg = str(e)
            print(f"check-status: Session invalid for {phone}: {error_msg}", file=sys.stderr, flush=True)
            
            # Закрываем клиент если открыт
            if client:
                try:
                    await client.stop()
                except:
                    pass
            
            # НЕ удаляем сессию и НЕ запрашиваем код - просто сообщаем статус
            account_storage.update_account_connection(account_id, False)
            return {"is_connected": False, "status": "session_invalid", "message": error_msg}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

