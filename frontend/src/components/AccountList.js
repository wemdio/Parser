import React, { useState } from 'react';
import axios from 'axios';
import './AccountList.css';
import API_BASE from '../config';

function AccountList({ accounts, onRefresh }) {
  const [deleting, setDeleting] = useState({});
  const [checking, setChecking] = useState({});
  const [message, setMessage] = useState(null);

  const handleDelete = async (accountId) => {
    if (!window.confirm('Вы уверены, что хотите удалить этот аккаунт? Это действие нельзя отменить.')) {
      return;
    }

    setDeleting({ ...deleting, [accountId]: true });
    setMessage(null);

    try {
      await axios.delete(`${API_BASE}/accounts/${accountId}`);
      setMessage({ type: 'success', text: 'Аккаунт успешно удален' });
      if (onRefresh) {
        onRefresh();
      }
    } catch (error) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Ошибка при удалении аккаунта' 
      });
    } finally {
      setDeleting({ ...deleting, [accountId]: false });
    }
  };

  const handleCheckStatus = async (accountId) => {
    setChecking({ ...checking, [accountId]: true });
    setMessage(null);

    try {
      const response = await axios.post(`${API_BASE}/accounts/${accountId}/check-status`);
      const statusText = response.data.is_connected ? 'подключен' : 'не подключен';
      setMessage({ 
        type: response.data.is_connected ? 'success' : 'info', 
        text: `Статус аккаунта: ${statusText}` 
      });
      if (onRefresh) {
        onRefresh();
      }
    } catch (error) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Ошибка при проверке статуса' 
      });
    } finally {
      setChecking({ ...checking, [accountId]: false });
    }
  };

  if (accounts.length === 0) {
    return (
      <div className="card">
        <h2>Добавленные аккаунты</h2>
        <p>Аккаунты не добавлены</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h2>Добавленные аккаунты</h2>
      
      {message && (
        <div className={`message message-${message.type}`}>
          {message.text}
        </div>
      )}

      <div className="accounts-list">
        {accounts.map(account => (
          <div key={account.id} className="account-item">
            <div className="account-info">
              <div className="account-name">
                {account.name || account.phone_number}
              </div>
              <div className="account-phone">{account.phone_number}</div>
              <div className={`status-badge ${account.is_connected ? 'status-connected' : 'status-disconnected'}`}>
                {account.is_connected ? 'Подключен' : 'Не подключен'}
              </div>
              <div className="account-actions">
                <button
                  className="btn btn-primary"
                  onClick={() => handleCheckStatus(account.id)}
                  disabled={checking[account.id]}
                  style={{ marginRight: '10px', fontSize: '12px', padding: '5px 10px' }}
                >
                  {checking[account.id] ? 'Проверка...' : 'Проверить статус'}
                </button>
                <button
                  className="btn btn-danger"
                  onClick={() => handleDelete(account.id)}
                  disabled={deleting[account.id]}
                  style={{ fontSize: '12px', padding: '5px 10px' }}
                >
                  {deleting[account.id] ? 'Удаление...' : 'Удалить'}
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default AccountList;

