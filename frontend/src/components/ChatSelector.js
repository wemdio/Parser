import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './ChatSelector.css';

const API_BASE = 'http://localhost:8000/api';

function ChatSelector({ accounts }) {
  const [selectedAccount, setSelectedAccount] = useState(null);
  const [chats, setChats] = useState([]);
  const [selectedChatIds, setSelectedChatIds] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    if (selectedAccount) {
      loadChats(selectedAccount.id);
      loadSelectedChats(selectedAccount.id);
    }
  }, [selectedAccount]);

  const loadChats = async (accountId) => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE}/chats/${accountId}`);
      setChats(response.data.chats || []);
      setMessage(null);
    } catch (error) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Ошибка загрузки чатов' 
      });
    } finally {
      setLoading(false);
    }
  };

  const loadSelectedChats = async (accountId) => {
    try {
      const response = await axios.get(`${API_BASE}/chats/${accountId}/selected`);
      setSelectedChatIds(response.data.chat_ids || []);
    } catch (error) {
      console.error('Error loading selected chats:', error);
    }
  };

  const handleAccountChange = (e) => {
    const accountId = parseInt(e.target.value);
    const account = accounts.find(acc => acc.id === accountId);
    setSelectedAccount(account || null);
  };

  const handleChatToggle = (chatId) => {
    setSelectedChatIds(prev => {
      if (prev.includes(chatId)) {
        return prev.filter(id => id !== chatId);
      } else {
        return [...prev, chatId];
      }
    });
  };

  const handleSaveSelection = async () => {
    if (!selectedAccount) return;

    try {
      setLoading(true);
      await axios.post(`${API_BASE}/chats/select`, {
        account_id: selectedAccount.id,
        chat_ids: selectedChatIds
      });
      setMessage({ 
        type: 'success', 
        text: `Выбрано чатов: ${selectedChatIds.length}` 
      });
    } catch (error) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Ошибка сохранения выбора' 
      });
    } finally {
      setLoading(false);
    }
  };

  const connectedAccounts = accounts.filter(acc => acc.is_connected);

  if (connectedAccounts.length === 0) {
    return (
      <div className="card">
        <h2>Выбор чатов для парсинга</h2>
        <p>Добавьте и подключите аккаунт для выбора чатов</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h2>Выбор чатов для парсинга</h2>
      
      {message && (
        <div className={`message message-${message.type}`}>
          {message.text}
        </div>
      )}

      <div className="input-group">
        <label>Выберите аккаунт:</label>
        <select 
          value={selectedAccount?.id || ''} 
          onChange={handleAccountChange}
          style={{ width: '100%', padding: '10px', fontSize: '14px' }}
        >
          <option value="">-- Выберите аккаунт --</option>
          {connectedAccounts.map(account => (
            <option key={account.id} value={account.id}>
              {account.name || account.phone_number} {account.is_connected && '(подключен)'}
            </option>
          ))}
        </select>
      </div>

      {selectedAccount && (
        <>
          {loading && chats.length === 0 ? (
            <div className="loading">Загрузка чатов...</div>
          ) : (
            <>
              <div className="chats-container">
                <h3>Доступные чаты:</h3>
                {chats.length === 0 ? (
                  <p>Чаты не найдены</p>
                ) : (
                  <div className="chats-list">
                    {chats.map(chat => (
                      <div key={chat.id} className="chat-item">
                        <label className="checkbox-label">
                          <input
                            type="checkbox"
                            checked={selectedChatIds.includes(chat.id)}
                            onChange={() => handleChatToggle(chat.id)}
                          />
                          <span className="chat-name">{chat.title}</span>
                          {chat.username && (
                            <span className="chat-username">@{chat.username}</span>
                          )}
                        </label>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <button 
                className="btn btn-success" 
                onClick={handleSaveSelection}
                disabled={loading || selectedChatIds.length === 0}
              >
                Сохранить выбор ({selectedChatIds.length})
              </button>
            </>
          )}
        </>
      )}
    </div>
  );
}

export default ChatSelector;

