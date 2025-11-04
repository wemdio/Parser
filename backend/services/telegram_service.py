from pyrogram import Client
from pyrogram.errors import PhoneCodeInvalid, PhoneNumberInvalid, SessionPasswordNeeded, PhoneCodeExpired
import asyncio
import os
from typing import Optional, Dict, List
import json

class TelegramService:
    def __init__(self):
        self.sessions_dir = "sessions"
        os.makedirs(self.sessions_dir, exist_ok=True)
        # Храним активные клиенты в памяти
        self._active_clients = {}  # {phone_number: client}
    
    def get_session_path(self, phone_number: str) -> str:
        """Получает путь к файлу сессии"""
        safe_phone = phone_number.replace("+", "").replace("-", "").replace(" ", "")
        return os.path.join(self.sessions_dir, f"{safe_phone}.session")
    
    async def create_client(self, api_id: str, api_hash: str, phone_number: str) -> Optional[Client]:
        """Создает клиент Telegram"""
        try:
            session_path = self.get_session_path(phone_number)
            client = Client(
                session_path,
                api_id=int(api_id),
                api_hash=api_hash,
                phone_number=phone_number
            )
            return client
        except Exception as e:
            print(f"Error creating client: {e}")
            return None
    
    async def connect_account(self, api_id: str, api_hash: str, phone_number: str) -> Dict:
        """Подключает аккаунт и запрашивает код подтверждения"""
        client = None
        try:
            client = await self.create_client(api_id, api_hash, phone_number)
            
            if not client:
                raise Exception("Failed to create client")
            
            await client.connect()
            
            # Проверяем подключение (is_connected - это свойство, а не метод)
            if not client.is_connected:
                raise Exception("Failed to connect to Telegram")
            
            # Проверяем, авторизован ли уже клиент
            try:
                me = await client.get_me()
                if me:
                    await client.disconnect()
                    return {"status": "already_connected"}
            except Exception as check_error:
                # Не авторизован, нужно запросить код
                print(f"Not authorized yet, will request code. Check error: {check_error}")
                pass
            
            # Проверяем, нужна ли авторизация - запрашиваем код
            try:
                from datetime import datetime
                send_time = datetime.now()
                
                sent_code = await client.send_code(phone_number)
                
                print(f"\n{'='*50}", flush=True)
                print(f"CODE SENT SUCCESSFULLY", flush=True)
                print(f"Phone: {phone_number}", flush=True)
                print(f"Code hash: {sent_code.phone_code_hash}", flush=True)
                print(f"Time: {send_time.strftime('%H:%M:%S')}", flush=True)
                print(f"IMPORTANT: Code is valid for ~3 minutes!", flush=True)
                print(f"Session file: {self.get_session_path(phone_number)}", flush=True)
                print(f"KEEPING CLIENT ALIVE in memory!", flush=True)
                print(f"{'='*50}\n", flush=True)
                
                # НЕ отключаем клиент - храним в памяти для verify_code
                self._active_clients[phone_number] = client
                print(f"Stored client for {phone_number} in memory", flush=True)
                
                return {
                    "phone_code_hash": sent_code.phone_code_hash,
                    "needs_password": False,
                    "sent_at": send_time.isoformat()
                }
            except Exception as send_code_error:
                error_str = str(send_code_error)
                print(f"Error sending code: {error_str}")
                raise
            
        except PhoneNumberInvalid as e:
            if client:
                try:
                    if client.is_connected:
                        await client.disconnect()
                except:
                    pass
            raise Exception("Invalid phone number. Please check the phone number format (e.g., +79991234567)")
        except ValueError as e:
            if client:
                try:
                    if client.is_connected:
                        await client.disconnect()
                except:
                    pass
            error_msg = str(e)
            print(f"ValueError: {error_msg}")
            if "api_id" in error_msg.lower() or "api_hash" in error_msg.lower():
                raise Exception("Invalid API ID or API Hash. Please check your credentials from https://my.telegram.org")
            raise Exception(f"Validation error: {error_msg}")
        except Exception as e:
            error_str = str(e)
            print(f"Connection error details: {error_str}")
            print(f"Error type: {type(e).__name__}")
            
            if client:
                try:
                    if client.is_connected:
                        await client.disconnect()
                except:
                    pass
            
            # Более подробные сообщения об ошибках
            if "flood" in error_str.lower() or "FLOOD" in error_str:
                raise Exception("Too many requests. Please wait a few minutes before trying again.")
            elif "phone" in error_str.lower() or "number" in error_str.lower() or "PHONE" in error_str:
                raise Exception("Invalid phone number format. Use format: +79991234567")
            elif "api_id" in error_str.lower() or "API_ID" in error_str:
                raise Exception("Invalid API ID. Please check your API credentials.")
            elif "unauthorized" in error_str.lower():
                # Сессия существует, но не авторизована - это нормально, нужно запросить код
                raise Exception("Session exists but not authorized. Please try again.")
            else:
                raise Exception(f"Connection error: {error_str}")
    
    async def verify_code(
        self, 
        api_id: str, 
        api_hash: str, 
        phone_number: str, 
        phone_code: str, 
        phone_code_hash: str,
        password: Optional[str] = None
    ) -> bool:
        """Проверяет код подтверждения"""
        from datetime import datetime
        verify_time = datetime.now()
        
        print(f"\n{'='*50}", flush=True)
        print(f"VERIFY CODE STARTED", flush=True)
        print(f"Phone: {phone_number}", flush=True)
        print(f"Code: {phone_code}", flush=True)
        print(f"Code hash: {phone_code_hash}", flush=True)
        print(f"Time: {verify_time.strftime('%H:%M:%S')}", flush=True)
        
        # Проверяем, есть ли активный клиент в памяти
        if phone_number in self._active_clients:
            print(f"FOUND ACTIVE CLIENT in memory for {phone_number}!", flush=True)
            print(f"Using THE SAME client that requested the code", flush=True)
            client = self._active_clients[phone_number]
        else:
            print(f"WARNING: No active client in memory!", flush=True)
            print(f"Creating new client from session file", flush=True)
            client = await self.create_client(api_id, api_hash, phone_number)
        print(f"{'='*50}\n", flush=True)
        
        try:
            # Если клиент из памяти - он уже подключен
            if phone_number not in self._active_clients:
                print("Connecting new client...", flush=True)
                await client.connect()
            else:
                print("Client already connected from memory", flush=True)
            
            if not client.is_connected:
                print("Client not connected")
                return False
            
            try:
                print("Attempting sign in...")
                await client.sign_in(phone_number, phone_code_hash, phone_code)
                print("Sign in successful!")
                
                # Убираем из активных клиентов
                if phone_number in self._active_clients:
                    del self._active_clients[phone_number]
                    print(f"Removed {phone_number} from active clients", flush=True)
                
                await client.disconnect()
                return True
            except SessionPasswordNeeded:
                print("2FA password required")
                if password:
                    await client.check_password(password)
                    await client.disconnect()
                    return True
                else:
                    await client.disconnect()
                    raise Exception("2FA password required")
            except PhoneCodeInvalid:
                print("Invalid phone code")
                await client.disconnect()
                raise Exception("Invalid verification code. Please check the code and try again.")
            except PhoneCodeExpired:
                print("Phone code expired")
                await client.disconnect()
                raise Exception("PHONE_CODE_EXPIRED: Код подтверждения истек. Пожалуйста, запросите новый код.")
                
        except Exception as e:
            if client and client.is_connected:
                try:
                    await client.disconnect()
                except:
                    pass
            raise Exception(f"Verification error: {str(e)}")
    
    async def get_chats(self, api_id: str, api_hash: str, phone_number: str) -> List[Dict]:
        """Получает список чатов для аккаунта"""
        client = await self.create_client(api_id, api_hash, phone_number)
        
        if not client:
            raise Exception("Failed to create client")
        
        try:
            await client.connect()
            
            if not client.is_connected:
                raise Exception("Not connected")
            
            chats = []
            async for dialog in client.get_dialogs():
                chat = dialog.chat
                if chat and (chat.type.value in ["group", "supergroup", "channel"]):
                    chats.append({
                        "id": chat.id,
                        "title": chat.title,
                        "username": chat.username
                    })
            
            await client.disconnect()
            return chats
            
        except Exception as e:
            if client and client.is_connected:
                try:
                    await client.disconnect()
                except:
                    pass
            raise Exception(f"Error getting chats: {str(e)}")
    
    async def parse_messages(
        self, 
        api_id: str, 
        api_hash: str, 
        phone_number: str, 
        chat_ids: List[int],
        hours_back: int = 1
    ) -> List[Dict]:
        """Парсит сообщения за последние N часов из указанных чатов"""
        from datetime import datetime, timedelta, timezone
        
        client = await self.create_client(api_id, api_hash, phone_number)
        
        if not client:
            raise Exception("Failed to create client")
        
        try:
            await client.connect()
            
            if not client.is_connected:
                raise Exception("Not connected")
            
            messages_data = []
            # Используем UTC время для сравнения
            from datetime import timezone
            current_time = datetime.now(timezone.utc)
            time_limit = current_time - timedelta(hours=hours_back)
            
            print(f"\n>>> CURRENT TIME: {current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC", flush=True)
            print(f">>> TIME LIMIT: {time_limit.strftime('%Y-%m-%d %H:%M:%S')} UTC", flush=True)
            print(f">>> Will ONLY save messages AFTER {time_limit.strftime('%H:%M:%S')}", flush=True)
            
            for chat_id in chat_ids:
                try:
                    chat = await client.get_chat(chat_id)
                    chat_title = chat.title if hasattr(chat, 'title') else f"Chat {chat_id}"
                    
                    # Получаем сообщения с ограничением по времени
                    messages_in_chat = 0
                    skipped_old = 0
                    total_checked = 0
                    
                    print(f"\n>>> Fetching history for chat '{chat_title}'...", flush=True)
                    
                    async for message in client.get_chat_history(chat_id, limit=1000):
                        total_checked += 1
                        
                        # ИСПОЛЬЗУЕМ TIMESTAMP для точного определения времени
                        # Pyrogram возвращает time в локальном часовом поясе БЕЗ TZ info
                        # Поэтому используем timestamp (UNIX time - всегда UTC)
                        import time as time_module
                        
                        original_date = message.date
                        
                        # Получаем timestamp (секунды с 1970-01-01 UTC)
                        if hasattr(original_date, 'timestamp'):
                            timestamp = original_date.timestamp()
                        else:
                            # Fallback для старых версий
                            import calendar
                            timestamp = calendar.timegm(original_date.timetuple())
                        
                        # Преобразуем timestamp обратно в UTC datetime
                        msg_date = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                        
                        # Логируем первые 5 сообщений для отладки
                        if total_checked <= 5:
                            print(f"    Checking message #{total_checked}:", flush=True)
                            print(f"      Original datetime: {original_date.strftime('%Y-%m-%d %H:%M:%S')} (TZ: {original_date.tzinfo})", flush=True)
                            print(f"      Timestamp: {timestamp}", flush=True)
                            print(f"      UTC datetime: {msg_date.strftime('%Y-%m-%d %H:%M:%S')} UTC", flush=True)
                            print(f"      Time limit: {time_limit.strftime('%Y-%m-%d %H:%M:%S')} UTC", flush=True)
                        
                        # Проверяем что сообщение в пределах времени
                        if msg_date < time_limit:
                            skipped_old += 1
                            # Логируем первое пропущенное сообщение
                            if skipped_old == 1:
                                print(f"    ✗ STOP: Message too old: {msg_date.strftime('%Y-%m-%d %H:%M:%S')} < {time_limit.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
                            break  # Старые сообщения - прекращаем (история идет от новых к старым)
                        
                        # Получаем информацию о пользователе
                        user_info = {}
                        
                        # Логируем для отладки
                        if total_checked <= 3:
                            print(f"    Message #{total_checked} from_user: {message.from_user}", flush=True)
                            if hasattr(message, 'sender_chat'):
                                print(f"    Message #{total_checked} sender_chat: {message.sender_chat}", flush=True)
                        
                        if message.from_user:
                            # Обычное сообщение от пользователя
                            user_info = {
                                "user_id": message.from_user.id,  # Уникальный ID - всегда доступен
                                "first_name": message.from_user.first_name,
                                "last_name": message.from_user.last_name,
                                "username": message.from_user.username,  # Может быть None
                            }
                            
                            # Пытаемся получить био пользователя
                            try:
                                user_full = await client.get_chat(message.from_user.id)
                                if hasattr(user_full, 'bio') and user_full.bio:
                                    user_info["bio"] = user_full.bio
                                elif hasattr(user_full, 'about') and user_full.about:
                                    user_info["bio"] = user_full.about
                                else:
                                    user_info["bio"] = None
                            except Exception as e:
                                if total_checked <= 3:
                                    print(f"    Could not get bio: {e}", flush=True)
                                user_info["bio"] = None
                        elif hasattr(message, 'sender_chat') and message.sender_chat:
                            # Сообщение от канала или группы
                            user_info = {
                                "user_id": message.sender_chat.id,
                                "first_name": message.sender_chat.title,  # Название канала/группы
                                "last_name": None,
                                "username": message.sender_chat.username if hasattr(message.sender_chat, 'username') else None,
                            }
                            
                            # Пытаемся получить описание канала
                            try:
                                chat_full = await client.get_chat(message.sender_chat.id)
                                if hasattr(chat_full, 'description') and chat_full.description:
                                    user_info["bio"] = chat_full.description
                                else:
                                    user_info["bio"] = None
                            except Exception as e:
                                if total_checked <= 3:
                                    print(f"    Could not get channel description: {e}", flush=True)
                                user_info["bio"] = None
                        else:
                            # Служебное сообщение или анонимный админ
                            if total_checked <= 3:
                                print(f"    ⚠️ Message #{total_checked} has no from_user or sender_chat - skipping", flush=True)
                            continue  # Пропускаем такие сообщения
                        
                        message_text = ""
                        if message.text:
                            message_text = message.text
                        elif message.caption:
                            message_text = message.caption
                        
                        if message_text:  # Сохраняем только текстовые сообщения
                            # Логируем время сообщения для первых нескольких
                            if messages_in_chat < 5:
                                print(f"    ✓ SAVING message #{messages_in_chat + 1}: {msg_date.strftime('%Y-%m-%d %H:%M:%S')} (WITHIN time limit)", flush=True)
                            
                            # Создаем ссылку на профиль
                            profile_link = None
                            if user_info.get("username"):
                                # Если есть username - используем прямую ссылку
                                profile_link = f"https://t.me/{user_info.get('username')}"
                            elif user_info.get("user_id"):
                                # Если нет username - ссылка по ID (откроет профиль в приложении)
                                profile_link = f"tg://user?id={user_info.get('user_id')}"
                            
                            # Подготавливаем данные для сохранения
                            message_data = {
                                "message_time": msg_date.isoformat(),  # Используем правильное UTC время
                                "chat_name": chat_title,
                                "user_id": user_info.get("user_id"),  # Уникальный ID пользователя
                                "first_name": user_info.get("first_name"),
                                "last_name": user_info.get("last_name"),
                                "username": user_info.get("username"),  # Может быть пустым
                                "bio": user_info.get("bio"),
                                "profile_link": profile_link,  # Ссылка на профиль
                                "message": message_text
                            }
                            
                            # Логируем первые несколько сообщений для отладки
                            if messages_in_chat < 3:
                                print(f"    📦 Prepared data for saving:", flush=True)
                                print(f"       user_id: {message_data['user_id']}", flush=True)
                                print(f"       profile_link: {message_data['profile_link']}", flush=True)
                                print(f"       first_name: {message_data['first_name']}", flush=True)
                            
                            messages_data.append(message_data)
                            messages_in_chat += 1
                    
                    print(f">>> RESULT for '{chat_title}':", flush=True)
                    print(f"    - Checked: {total_checked} messages", flush=True)
                    print(f"    - Saved: {messages_in_chat} messages (within last hour)", flush=True)
                    print(f"    - Skipped: {skipped_old} messages (too old)", flush=True)
                
                except Exception as e:
                    print(f"Error parsing chat {chat_id}: {e}")
                    continue
            
            await client.disconnect()
            return messages_data
            
        except Exception as e:
            if client and client.is_connected:
                try:
                    await client.disconnect()
                except:
                    pass
            raise Exception(f"Error parsing messages: {str(e)}")

