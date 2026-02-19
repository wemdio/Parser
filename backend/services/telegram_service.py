from pyrogram import Client
from pyrogram.errors import PhoneCodeInvalid, PhoneNumberInvalid, SessionPasswordNeeded, PhoneCodeExpired, FloodWait, PeerIdInvalid
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
        """Получает путь к файлу сессии (БЕЗ .session - Pyrogram добавит сам)"""
        safe_phone = phone_number.replace("+", "").replace("-", "").replace(" ", "")
        # НЕ добавляем .session - Pyrogram сам добавляет при создании Client
        return os.path.join(self.sessions_dir, safe_phone)
    
    async def create_client(self, api_id: str, api_hash: str, phone_number: str, use_existing_session: bool = False) -> Optional[Client]:
        """
        Создает клиент Telegram.
        
        Args:
            use_existing_session: Если True, НЕ передаём phone_number в Client,
                                  чтобы использовать существующую сессию без переавторизации.
        """
        try:
            session_path = self.get_session_path(phone_number)
            
            if use_existing_session:
                # Для существующих сессий - НЕ передаём phone_number!
                # Это предотвращает попытку переавторизации
                client = Client(
                    session_path,
                    api_id=int(api_id),
                    api_hash=api_hash
                )
            else:
                # Для новой авторизации - передаём phone_number
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
        session_path = self.get_session_path(phone_number)
        
        # СНАЧАЛА удаляем старую сессию если есть - это решает AUTH_KEY_UNREGISTERED
        for path in [session_path, f"{session_path}.session"]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                    print(f"Removed old session file: {path}")
                except Exception as e:
                    print(f"Could not remove old session {path}: {e}")
        
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
                error_str = str(check_error)
                print(f"Not authorized yet, will request code. Check error: {check_error}")
                
                # Если AUTH_KEY_UNREGISTERED - нужно пересоздать клиента
                if "AUTH_KEY_UNREGISTERED" in error_str or "not registered" in error_str.lower():
                    print("AUTH_KEY_UNREGISTERED detected, recreating session...")
                    try:
                        await client.disconnect()
                    except:
                        pass
                    
                    # Удаляем сессию ещё раз
                    for path in [session_path, f"{session_path}.session"]:
                        if os.path.exists(path):
                            try:
                                os.remove(path)
                                print(f"Removed invalid session: {path}")
                            except:
                                pass
                    
                    # Создаём новый клиент
                    client = await self.create_client(api_id, api_hash, phone_number)
                    if not client:
                        raise Exception("Failed to recreate client after AUTH_KEY_UNREGISTERED")
                    await client.connect()
            
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
        import sys
        import sqlite3
        
        print(f"\n{'='*50}", file=sys.stderr, flush=True)
        print(f"GET_CHATS for {phone_number}", file=sys.stderr, flush=True)
        print(f"{'='*50}", file=sys.stderr, flush=True)
        
        # ВАЖНО: Закрываем старый клиент если он застрял в памяти
        if phone_number in self._active_clients:
            try:
                old_client = self._active_clients[phone_number]
                print(f"Found stale client in memory, closing...", file=sys.stderr, flush=True)
                if old_client.is_connected:
                    await old_client.disconnect()
                del self._active_clients[phone_number]
                await asyncio.sleep(2)  # Даём время освободить файл
                print(f"Stale client closed", file=sys.stderr, flush=True)
            except Exception as e:
                print(f"Error closing stale client: {e}", file=sys.stderr, flush=True)
        
        # Retry logic для "database is locked" ошибки
        max_retries = 5
        retry_delay = 3  # секунды
        
        # Попробуем включить WAL mode для сессии
        session_path = self.get_session_path(phone_number)
        session_file = f"{session_path}.session"
        print(f"Session file: {session_file}", file=sys.stderr, flush=True)
        print(f"Session exists: {os.path.exists(session_file)}", file=sys.stderr, flush=True)
        
        if os.path.exists(session_file):
            try:
                conn = sqlite3.connect(session_file, timeout=30)
                conn.execute("PRAGMA journal_mode=WAL")
                conn.close()
                print(f"WAL mode enabled", file=sys.stderr, flush=True)
            except Exception as wal_err:
                print(f"Could not set WAL mode: {wal_err}", file=sys.stderr, flush=True)
        
        for attempt in range(max_retries):
            client = None
            try:
                # Небольшая задержка перед попыткой (даёт время освободить файл)
                if attempt > 0:
                    await asyncio.sleep(1)
                
                print(f"Attempt {attempt + 1}/{max_retries}", file=sys.stderr, flush=True)
                
                # Используем существующую сессию без попытки переавторизации
                client = await self.create_client(api_id, api_hash, phone_number, use_existing_session=True)
                
                if not client:
                    raise Exception("Failed to create client")
                
                print(f"Client created, connecting...", file=sys.stderr, flush=True)
                await client.connect()
                
                if not client.is_connected:
                    raise Exception("Not connected")
                
                print(f"Connected! Getting dialogs...", file=sys.stderr, flush=True)
                
                chats = []
                try:
                    async for dialog in client.get_dialogs():
                        try:
                            chat = dialog.chat
                            if chat and (chat.type.value in ["group", "supergroup", "channel"]):
                                chats.append({
                                    "id": chat.id,
                                    "title": chat.title,
                                    "username": chat.username
                                })
                        except AttributeError:
                            continue
                except AttributeError as e:
                    print(f"⚠️ Partial dialog load (pyrofork issue): {e}", file=sys.stderr, flush=True)
                
                print(f"Found {len(chats)} chats", file=sys.stderr, flush=True)
                
                await client.disconnect()
                
                # Даём время на освобождение файла
                await asyncio.sleep(0.5)
                
                print(f"SUCCESS! Returning {len(chats)} chats", file=sys.stderr, flush=True)
                return chats
                
            except FloodWait as fw:
                # FloodWait - Telegram просит подождать
                wait_time = fw.value
                print(f"FloodWait: Telegram asks to wait {wait_time} seconds", file=sys.stderr, flush=True)
                
                if client:
                    try:
                        await client.disconnect()
                    except:
                        pass
                
                if attempt < max_retries - 1:
                    print(f"Waiting {wait_time}s before retry...", file=sys.stderr, flush=True)
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"FloodWait: Please wait {wait_time} seconds and try again")
                
            except Exception as e:
                error_msg = str(e)
                print(f"Error: {error_msg}", file=sys.stderr, flush=True)
                
                # Закрываем клиент если открыт
                if client:
                    try:
                        if client.is_connected:
                            await client.disconnect()
                        await asyncio.sleep(0.5)
                    except:
                        pass
                
                # Если "database is locked" - пробуем снова
                if "database is locked" in error_msg.lower() and attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    print(f"Database locked, retry {attempt + 1}/{max_retries} in {wait_time}s...", file=sys.stderr, flush=True)
                    await asyncio.sleep(wait_time)
                    continue
                
                raise Exception(f"Error getting chats: {error_msg}")
    
    async def parse_messages(
        self, 
        api_id: str, 
        api_hash: str, 
        phone_number: str, 
        chat_ids: List[int],
        hours_back: int = 1
    ) -> Dict:
        """Парсит сообщения за последние N часов из указанных чатов
        
        Returns:
            Dict with:
                - messages: List[Dict] - список спарсенных сообщений
                - stats: List[Dict] - статистика по каждому чату
        """
        from datetime import datetime, timedelta, timezone
        import time
        
        # Используем существующую сессию без попытки переавторизации
        client = await self.create_client(api_id, api_hash, phone_number, use_existing_session=True)
        
        if not client:
            raise Exception("Failed to create client")
        
        try:
            await client.connect()
            
            if not client.is_connected:
                raise Exception("Not connected")
            
            # 🔥 ЗАГРУЖАЕМ ВСЕ ЧАТЫ В КЭШ - исправляет "Peer id invalid"
            print(f"\n>>> 🔄 Loading chats into Pyrogram cache...", flush=True)
            dialog_count = 0
            try:
                async for dialog in client.get_dialogs(limit=500):
                    try:
                        _ = dialog.chat
                        dialog_count += 1
                    except AttributeError:
                        continue
                print(f">>> ✅ Loaded {dialog_count} chats into cache", flush=True)
            except AttributeError as e:
                print(f">>> ⚠️ Partial cache load (pyrofork issue): {e}", flush=True)
            except Exception as e:
                print(f">>> ⚠️ Warning: Could not load all dialogs: {e}", flush=True)
            
            messages_data = []
            parsing_stats = []  # 📊 Статистика по каждому чату
            user_bio_cache = {}  # 🔄 Кэш био пользователей чтобы не вызывать get_chat() повторно
            
            # Используем UTC время для сравнения
            current_time = datetime.now(timezone.utc)
            time_limit = current_time - timedelta(hours=hours_back)
            
            print(f"\n>>> CURRENT TIME: {current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC", flush=True)
            print(f">>> TIME LIMIT: {time_limit.strftime('%Y-%m-%d %H:%M:%S')} UTC", flush=True)
            print(f">>> Will ONLY save messages AFTER {time_limit.strftime('%H:%M:%S')}", flush=True)
            
            for chat_id in chat_ids:
                chat_start_time = time.time()  # ⏱️ Время начала парсинга чата
                chat_stat = {
                    "chat_id": chat_id,
                    "chat_name": f"Chat {chat_id}",
                    "messages_found": 0,
                    "messages_saved": 0,
                    "messages_skipped": 0,
                    "status": "success",
                    "error_type": None,
                    "error_message": None,
                    "started_at": datetime.now(timezone.utc),
                    "execution_time_seconds": 0
                }
                try:
                    chat = await client.get_chat(chat_id)
                    chat_title = chat.title if hasattr(chat, 'title') else f"Chat {chat_id}"
                    chat_username = chat.username if hasattr(chat, 'username') else None
                    
                    # Проверяем является ли чат форумом (с топиками)
                    is_forum = getattr(chat, 'is_forum', False)
                    
                    # Обновляем название чата в статистике
                    chat_stat["chat_name"] = chat_title
                    
                    # Получаем сообщения с ограничением по времени
                    messages_in_chat = 0
                    skipped_old = 0
                    total_checked = 0
                    
                    print(f"\n>>> Fetching history for chat '{chat_title}' (username: {chat_username})...", flush=True)
                    
                    if is_forum:
                        print(f"    📁 This is a FORUM with topics!", flush=True)
                    
                    # Для форумов парсим все топики, для обычных чатов - обычная история
                    message_sources = []
                    
                    if is_forum:
                        # Получаем список топиков форума
                        try:
                            from pyrogram.raw import functions, types
                            
                            # Получаем топики через raw API
                            result = await client.invoke(
                                functions.channels.GetForumTopics(
                                    channel=await client.resolve_peer(chat_id),
                                    offset_date=0,
                                    offset_id=0,
                                    offset_topic=0,
                                    limit=100
                                )
                            )
                            
                            topics = []
                            if hasattr(result, 'topics'):
                                for topic in result.topics:
                                    if hasattr(topic, 'id'):
                                        topic_title = getattr(topic, 'title', f'Topic {topic.id}')
                                        topics.append({'id': topic.id, 'title': topic_title})
                            
                            print(f"    📋 Found {len(topics)} topics in forum", flush=True)
                            
                            # Добавляем каждый топик как источник сообщений
                            for topic in topics:
                                print(f"       - Topic: {topic['title']} (id: {topic['id']})", flush=True)
                                message_sources.append({
                                    'topic_id': topic['id'],
                                    'topic_title': topic['title']
                                })
                                
                        except Exception as forum_err:
                            print(f"    ⚠️ Could not get forum topics: {forum_err}", flush=True)
                            print(f"    📝 Will try to parse General topic only", flush=True)
                            message_sources.append({'topic_id': None, 'topic_title': None})
                    else:
                        # Обычный чат - один источник
                        message_sources.append({'topic_id': None, 'topic_title': None})
                    
                    # Парсим сообщения из всех источников (топиков или обычного чата)
                    for source in message_sources:
                        topic_id = source['topic_id']
                        topic_title = source['topic_title']
                        
                        if topic_title:
                            print(f"\n    >>> Parsing topic: '{topic_title}'...", flush=True)
                        
                        # Выбираем правильный метод для получения сообщений
                        if topic_id:
                            # Для топиков используем get_discussion_replies()
                            # get_chat_history НЕ поддерживает reply_to_message_id в Pyrogram 2.0.106
                            message_iterator = client.get_discussion_replies(chat_id, topic_id)
                        else:
                            # Для обычных чатов - стандартная история
                            message_iterator = client.get_chat_history(chat_id, limit=1000)
                        
                        async for message in message_iterator:
                            total_checked += 1
                            
                            # ИСПОЛЬЗУЕМ TIMESTAMP для точного определения времени
                            # Pyrogram возвращает time в локальном часовом поясе БЕЗ TZ info
                            # Поэтому используем timestamp (UNIX time - всегда UTC)
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
                                chat_stat["messages_skipped"] += 1  # 📊 Счётчик пропущенных сообщений
                                # Логируем первое пропущенное сообщение
                                if skipped_old == 1:
                                    print(f"    ✗ STOP: Message too old: {msg_date.strftime('%Y-%m-%d %H:%M:%S')} < {time_limit.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
                                break  # Старые сообщения - прекращаем (история идет от новых к старым)
                            
                            chat_stat["messages_found"] += 1  # 📊 Счётчик найденных сообщений
                            
                            # Получаем информацию о пользователе
                            user_info = {}
                            
                            # Логируем для отладки
                            if total_checked <= 3:
                                print(f"    Message #{total_checked} from_user: {message.from_user}", flush=True)
                                if hasattr(message, 'sender_chat'):
                                    print(f"    Message #{total_checked} sender_chat: {message.sender_chat}", flush=True)
                            
                            if message.from_user:
                                # Обычное сообщение от пользователя
                                uid = message.from_user.id
                                user_info = {
                                    "user_id": uid,  # Уникальный ID - всегда доступен
                                    "first_name": message.from_user.first_name,
                                    "last_name": message.from_user.last_name,
                                    "username": message.from_user.username,  # Может быть None
                                }
                                
                                # Пытаемся получить био пользователя (с кэшированием)
                                if uid in user_bio_cache:
                                    user_info["bio"] = user_bio_cache[uid]
                                else:
                                    try:
                                        user_full = await client.get_chat(uid)
                                        bio = None
                                        if hasattr(user_full, 'bio') and user_full.bio:
                                            bio = user_full.bio
                                        elif hasattr(user_full, 'about') and user_full.about:
                                            bio = user_full.about
                                        user_bio_cache[uid] = bio
                                        user_info["bio"] = bio
                                    except FloodWait as e:
                                        # Rate limit при получении био - просто пропускаем
                                        if total_checked <= 3:
                                            print(f"    Rate limit getting bio, skipping (wait {e.value}s)", flush=True)
                                        user_bio_cache[uid] = None
                                        user_info["bio"] = None
                                    except Exception as e:
                                        if total_checked <= 3:
                                            print(f"    Could not get bio: {e}", flush=True)
                                        user_bio_cache[uid] = None
                                        user_info["bio"] = None
                            elif hasattr(message, 'sender_chat') and message.sender_chat:
                                # Сообщение от канала или группы
                                sender_id = message.sender_chat.id
                                user_info = {
                                    "user_id": sender_id,
                                    "first_name": message.sender_chat.title,  # Название канала/группы
                                    "last_name": None,
                                    "username": message.sender_chat.username if hasattr(message.sender_chat, 'username') else None,
                                }
                                
                                # Пытаемся получить описание канала (с кэшированием)
                                if sender_id in user_bio_cache:
                                    user_info["bio"] = user_bio_cache[sender_id]
                                else:
                                    try:
                                        chat_full = await client.get_chat(sender_id)
                                        bio = None
                                        if hasattr(chat_full, 'description') and chat_full.description:
                                            bio = chat_full.description
                                        user_bio_cache[sender_id] = bio
                                        user_info["bio"] = bio
                                    except FloodWait as e:
                                        # Rate limit при получении описания - просто пропускаем
                                        if total_checked <= 3:
                                            print(f"    Rate limit getting description, skipping (wait {e.value}s)", flush=True)
                                        user_bio_cache[sender_id] = None
                                        user_info["bio"] = None
                                    except Exception as e:
                                        if total_checked <= 3:
                                            print(f"    Could not get channel description: {e}", flush=True)
                                        user_bio_cache[sender_id] = None
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
                                
                                # Создаем ссылку на профиль или сообщение
                                profile_link = None
                                if user_info.get("username"):
                                    # Если есть username - используем прямую ссылку на профиль
                                    profile_link = f"https://t.me/{user_info.get('username')}"
                                else:
                                    # Если нет username - создаём deep link на само сообщение
                                    if chat_username:
                                        # Публичный канал/группа - ссылка на сообщение
                                        message_link = f"https://t.me/{chat_username}/{message.id}"
                                        profile_link = f"Профиль скрыт. Сообщение в чате \"{chat_title}\": {message_link}"
                                    else:
                                        # Приватный чат - только описание
                                        profile_link = f"Профиль скрыт. Сообщение в приватном чате \"{chat_title}\" (ID сообщения: {message.id})"
                                
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
                                chat_stat["messages_saved"] += 1  # 📊 Счётчик сохранённых сообщений
                    
                    print(f">>> RESULT for '{chat_title}':", flush=True)
                    print(f"    - Checked: {total_checked} messages", flush=True)
                    print(f"    - Saved: {messages_in_chat} messages (within last hour)", flush=True)
                    print(f"    - Skipped: {skipped_old} messages (too old)", flush=True)
                    
                    # ✅ Финализируем статистику
                    chat_stat["execution_time_seconds"] = time.time() - chat_start_time
                    chat_stat["finished_at"] = datetime.now(timezone.utc)
                    parsing_stats.append(chat_stat)
                
                except FloodWait as e:
                    # 🔥 АВТОМАТИЧЕСКОЕ ОЖИДАНИЕ при rate limit
                    wait_seconds = e.value
                    print(f"⏳ Rate limit for chat {chat_id}: waiting {wait_seconds} seconds...", flush=True)
                    await asyncio.sleep(wait_seconds)
                    print(f"✅ Wait complete, retrying chat {chat_id}...", flush=True)
                    
                    # 🔄 Пробуем этот же чат ещё раз после ожидания
                    try:
                        retry_chat = await client.get_chat(chat_id)
                        retry_title = retry_chat.title if hasattr(retry_chat, 'title') else f"Chat {chat_id}"
                        
                        async for message in client.get_chat_history(chat_id, limit=1000):
                            total_checked += 1
                            original_date = message.date
                            if hasattr(original_date, 'timestamp'):
                                timestamp = original_date.timestamp()
                            else:
                                import calendar
                                timestamp = calendar.timegm(original_date.timetuple())
                            msg_date = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                            
                            if msg_date < time_limit:
                                break
                            
                            chat_stat["messages_found"] += 1
                            
                            if not message.from_user and not (hasattr(message, 'sender_chat') and message.sender_chat):
                                continue
                            
                            message_text = message.text or message.caption or ""
                            if message_text:
                                # Минимальная обработка при retry
                                uid = message.from_user.id if message.from_user else message.sender_chat.id
                                uname = message.from_user.username if message.from_user else getattr(message.sender_chat, 'username', None)
                                fname = message.from_user.first_name if message.from_user else getattr(message.sender_chat, 'title', None)
                                lname = message.from_user.last_name if message.from_user else None
                                
                                profile_link = f"https://t.me/{uname}" if uname else f"Профиль скрыт. Сообщение в чате \"{retry_title}\" (ID: {message.id})"
                                
                                messages_data.append({
                                    "message_time": msg_date.isoformat(),
                                    "chat_name": retry_title,
                                    "user_id": uid,
                                    "first_name": fname,
                                    "last_name": lname,
                                    "username": uname,
                                    "bio": user_bio_cache.get(uid),
                                    "profile_link": profile_link,
                                    "message": message_text
                                })
                                messages_in_chat += 1
                                chat_stat["messages_saved"] += 1
                        
                        chat_stat["status"] = "success"
                        chat_stat["error_type"] = None
                        chat_stat["error_message"] = f"Retried after FloodWait({wait_seconds}s)"
                        print(f"✅ Retry successful: saved {messages_in_chat} messages from {retry_title}", flush=True)
                    except Exception as retry_err:
                        print(f"❌ Retry failed for chat {chat_id}: {retry_err}", flush=True)
                        chat_stat["status"] = "error"
                        chat_stat["error_type"] = "FLOOD_WAIT"
                        chat_stat["error_message"] = f"Rate limit: waited {wait_seconds}s, retry failed: {retry_err}"
                    
                    chat_stat["execution_time_seconds"] = time.time() - chat_start_time
                    chat_stat["finished_at"] = datetime.now(timezone.utc)
                    parsing_stats.append(chat_stat)
                    continue
                except PeerIdInvalid:
                    # ⚠️ Чат недоступен (выгнали, удален, или нет прав)
                    print(f"⚠️ Chat {chat_id} is not accessible (kicked, deleted, or no access). Skipping.", flush=True)
                    
                    # 📊 Сохраняем статистику с ошибкой
                    chat_stat["status"] = "skipped"
                    chat_stat["error_type"] = "PeerIdInvalid"
                    chat_stat["error_message"] = "Chat not accessible (kicked, deleted, or no access)"
                    chat_stat["execution_time_seconds"] = time.time() - chat_start_time
                    chat_stat["finished_at"] = datetime.now(timezone.utc)
                    parsing_stats.append(chat_stat)
                    continue
                except Exception as e:
                    print(f"❌ Error parsing chat {chat_id}: {e}", flush=True)
                    
                    # 📊 Сохраняем статистику с ошибкой
                    chat_stat["status"] = "error"
                    chat_stat["error_type"] = "Other"
                    chat_stat["error_message"] = str(e)
                    chat_stat["execution_time_seconds"] = time.time() - chat_start_time
                    chat_stat["finished_at"] = datetime.now(timezone.utc)
                    parsing_stats.append(chat_stat)
                    continue
            
            await client.disconnect()
            
            # 📊 Возвращаем сообщения и статистику
            return {
                "messages": messages_data,
                "stats": parsing_stats
            }
            
        except Exception as e:
            if client and client.is_connected:
                try:
                    await client.disconnect()
                except:
                    pass
            raise Exception(f"Error parsing messages: {str(e)}")

