from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class AccountCreate(BaseModel):
    api_id: str
    api_hash: str
    phone_number: str
    name: Optional[str] = None

class AccountResponse(BaseModel):
    id: int
    api_id: str
    phone_number: str
    name: Optional[str] = None
    is_connected: bool
    created_at: datetime

class ChatInfo(BaseModel):
    id: int
    title: str
    username: Optional[str] = None

class ChatSelect(BaseModel):
    account_id: int
    chat_ids: List[int]

class MessageData(BaseModel):
    message_time: datetime
    chat_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    bio: Optional[str] = None
    message: str

