import json
import os
from typing import List, Dict, Optional
from datetime import datetime

class AccountStorage:
    def __init__(self):
        self.storage_file = "accounts.json"
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Создает файл хранилища если его нет"""
        if not os.path.exists(self.storage_file):
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump({"accounts": [], "selected_chats": {}}, f, ensure_ascii=False, indent=2)
    
    def _read_data(self) -> dict:
        """Читает данные из файла"""
        try:
            with open(self.storage_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"accounts": [], "selected_chats": {}}
    
    def _write_data(self, data: dict):
        """Записывает данные в файл"""
        with open(self.storage_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_account(self, account_data: dict) -> int:
        """Добавляет аккаунт и возвращает его ID"""
        data = self._read_data()
        
        # Проверяем, нет ли уже такого аккаунта
        for acc in data["accounts"]:
            if acc["phone_number"] == account_data["phone_number"]:
                raise ValueError("Account with this phone number already exists")
        
        new_id = max([acc.get("id", 0) for acc in data["accounts"]], default=0) + 1
        
        account = {
            "id": new_id,
            "api_id": account_data["api_id"],
            "api_hash": account_data["api_hash"],
            "phone_number": account_data["phone_number"],
            "name": account_data.get("name"),
            "is_connected": False,
            "created_at": datetime.utcnow().isoformat()
        }
        
        data["accounts"].append(account)
        self._write_data(data)
        return new_id
    
    def get_account(self, account_id: int) -> Optional[dict]:
        """Получает аккаунт по ID"""
        data = self._read_data()
        for acc in data["accounts"]:
            if acc["id"] == account_id:
                return acc
        return None
    
    def get_all_accounts(self) -> List[dict]:
        """Получает все аккаунты"""
        data = self._read_data()
        return data["accounts"]
    
    def get_all_connected_accounts(self) -> List[dict]:
        """Получает все подключенные аккаунты"""
        data = self._read_data()
        return [acc for acc in data["accounts"] if acc.get("is_connected", False)]
    
    def update_account_connection(self, account_id: int, is_connected: bool):
        """Обновляет статус подключения аккаунта"""
        data = self._read_data()
        for acc in data["accounts"]:
            if acc["id"] == account_id:
                acc["is_connected"] = is_connected
                self._write_data(data)
                return
        raise ValueError("Account not found")
    
    def set_selected_chats(self, account_id: int, chat_ids: List[int]):
        """Устанавливает выбранные чаты для аккаунта"""
        data = self._read_data()
        if "selected_chats" not in data:
            data["selected_chats"] = {}
        data["selected_chats"][str(account_id)] = chat_ids
        self._write_data(data)
    
    def get_selected_chats(self, account_id: int) -> List[int]:
        """Получает выбранные чаты для аккаунта"""
        data = self._read_data()
        return data.get("selected_chats", {}).get(str(account_id), [])
    
    def delete_account(self, account_id: int) -> bool:
        """Удаляет аккаунт"""
        data = self._read_data()
        original_count = len(data["accounts"])
        data["accounts"] = [acc for acc in data["accounts"] if acc.get("id") != account_id]
        
        # Удаляем выбранные чаты для этого аккаунта
        if "selected_chats" in data:
            data["selected_chats"].pop(str(account_id), None)
        
        if len(data["accounts"]) < original_count:
            self._write_data(data)
            return True
        return False

