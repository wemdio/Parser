import React, { useState } from 'react';
import axios from 'axios';
import './AccountManager.css';

const API_BASE = 'http://localhost:8000/api';

function AccountManager({ onAccountAdded, onAccountVerified }) {
  const [showAddForm, setShowAddForm] = useState(false);
  const [showVerifyForm, setShowVerifyForm] = useState(false);
  const [showRequestNewCode, setShowRequestNewCode] = useState(false);
  const [formData, setFormData] = useState({
    api_id: '',
    api_hash: '',
    phone_number: '',
    name: ''
  });
  const [verificationData, setVerificationData] = useState({
    account_id: null,
    phone_code: '',
    phone_code_hash: '',
    password: ''
  });
  const [message, setMessage] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleVerifyInputChange = (e) => {
    setVerificationData({
      ...verificationData,
      [e.target.name]: e.target.value
    });
  };

  const handleAddAccount = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);

    try {
      const response = await axios.post(`${API_BASE}/accounts/add`, formData);
      
      console.log('Add account response:', response.data);
      console.log('Phone code hash received:', response.data.phone_code_hash);
      
      if (response.data.status === 'already_connected') {
        setMessage({ type: 'success', text: 'Аккаунт уже подключен!' });
        setShowAddForm(false);
        setFormData({ api_id: '', api_hash: '', phone_number: '', name: '' });
        onAccountAdded();
      } else if (response.data.status === 'already_exists') {
        const account = response.data.existing_account;
        const statusText = account.is_connected ? 'подключен' : 'не подключен';
        setMessage({ 
          type: 'info', 
          text: `Аккаунт с номером ${account.phone_number} уже существует (${statusText}). Используйте существующий аккаунт или добавьте другой номер.` 
        });
        setShowAddForm(false);
        setFormData({ api_id: '', api_hash: '', phone_number: '', name: '' });
        onAccountAdded();
      } else {
        const newVerificationData = {
          account_id: response.data.account_id,
          phone_code_hash: response.data.phone_code_hash,
          phone_code: '',
          password: ''
        };
        console.log('Setting verification data:', newVerificationData);
        setVerificationData(newVerificationData);
        setShowAddForm(false);
        setShowVerifyForm(true);
        setShowRequestNewCode(false);
        setMessage({ 
          type: 'info', 
          text: 'Код подтверждения отправлен. Введите код из Telegram.' 
        });
      }
    } catch (error) {
      const errorMessage = error.response?.data?.detail || error.message || 'Ошибка при добавлении аккаунта';
      console.error('Error adding account:', error);
      console.error('Error response:', error.response);
      setMessage({ 
        type: 'error', 
        text: errorMessage 
      });
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyCode = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);

    console.log('Sending verification with data:', verificationData);

    try {
      await axios.post(`${API_BASE}/accounts/verify`, verificationData);
      setMessage({ type: 'success', text: 'Аккаунт успешно подключен!' });
      setShowVerifyForm(false);
      setVerificationData({ account_id: null, phone_code: '', phone_code_hash: '', password: '' });
      onAccountVerified();
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Ошибка при проверке кода';
      console.error('Verification error:', error);
      console.error('Error detail:', error.response?.data?.detail);
      console.error('Full error response:', error.response);
      
      if (errorMsg.includes('password') || errorMsg.includes('2FA')) {
        setMessage({ 
          type: 'info', 
          text: 'Требуется пароль двухфакторной аутентификации. Введите пароль.' 
        });
      } else if (errorMsg.includes('expired') || errorMsg.includes('истек') || errorMsg.includes('PHONE_CODE_EXPIRED')) {
        setMessage({ 
          type: 'error', 
          text: 'Код подтверждения истек. Нажмите "Запросить новый код" чтобы получить новый код.' 
        });
        // Предлагаем запросить новый код
        setShowRequestNewCode(true);
      } else if (errorMsg.includes('Invalid') || errorMsg.includes('Неверный')) {
        setMessage({ 
          type: 'error', 
          text: 'Неверный код подтверждения. Проверьте код и попробуйте снова.' 
        });
      } else {
        // Показываем полное сообщение об ошибке
        setMessage({ 
          type: 'error', 
          text: `Ошибка верификации: ${errorMsg}` 
        });
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRequestNewCode = async () => {
    setLoading(true);
    setMessage(null);

    try {
      // Получаем данные аккаунта
      const accountsResponse = await axios.get(`${API_BASE}/accounts/`);
      const account = accountsResponse.data.accounts.find(acc => acc.id === verificationData.account_id);
      
      if (!account) {
        setMessage({ type: 'error', text: 'Аккаунт не найден' });
        return;
      }
      
      // Запрашиваем новый код (используем existing_account flow)
      const response = await axios.post(`${API_BASE}/accounts/add`, {
        api_id: account.api_id,
        api_hash: account.api_hash,
        phone_number: account.phone_number,
        name: account.name
      });
      
      if (response.data.status === 'already_exists') {
        // Если аккаунт существует и подключен
        setMessage({ 
          type: 'info', 
          text: 'Аккаунт уже существует и подключен.' 
        });
      } else if (response.data.phone_code_hash) {
        setVerificationData({
          ...verificationData,
          phone_code_hash: response.data.phone_code_hash,
          phone_code: ''
        });
        setShowRequestNewCode(false);
        setMessage({ 
          type: 'success', 
          text: 'Новый код подтверждения отправлен. Введите код из Telegram.' 
        });
      }
    } catch (error) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Ошибка при запросе нового кода' 
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <h2>Управление аккаунтами</h2>
      
      {message && (
        <div className={`message message-${message.type}`}>
          {message.text}
        </div>
      )}

      {!showAddForm && !showVerifyForm && (
        <button 
          className="btn btn-primary" 
          onClick={() => setShowAddForm(true)}
        >
          Добавить аккаунт
        </button>
      )}

      {showAddForm && (
        <form onSubmit={handleAddAccount}>
          <div className="input-group">
            <label>API ID:</label>
            <input
              type="text"
              name="api_id"
              value={formData.api_id}
              onChange={handleInputChange}
              required
              placeholder="Получить на https://my.telegram.org"
            />
          </div>
          
          <div className="input-group">
            <label>API Hash:</label>
            <input
              type="text"
              name="api_hash"
              value={formData.api_hash}
              onChange={handleInputChange}
              required
              placeholder="Получить на https://my.telegram.org"
            />
          </div>
          
          <div className="input-group">
            <label>Номер телефона:</label>
            <input
              type="text"
              name="phone_number"
              value={formData.phone_number}
              onChange={handleInputChange}
              required
              placeholder="+79991234567"
            />
          </div>
          
          <div className="input-group">
            <label>Имя аккаунта (необязательно):</label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleInputChange}
              placeholder="Мой аккаунт"
            />
          </div>
          
          <div style={{ display: 'flex', gap: '10px' }}>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Отправка...' : 'Добавить'}
            </button>
            <button 
              type="button" 
              className="btn" 
              onClick={() => {
                setShowAddForm(false);
                setFormData({ api_id: '', api_hash: '', phone_number: '', name: '' });
              }}
            >
              Отмена
            </button>
          </div>
        </form>
      )}

      {showVerifyForm && (
        <form onSubmit={handleVerifyCode}>
          <div className="input-group">
            <label>Код подтверждения:</label>
            <input
              type="text"
              name="phone_code"
              value={verificationData.phone_code}
              onChange={handleVerifyInputChange}
              required
              placeholder="Введите код из Telegram"
            />
          </div>
          
          <div className="input-group">
            <label>Пароль 2FA (если требуется):</label>
            <input
              type="password"
              name="password"
              value={verificationData.password}
              onChange={handleVerifyInputChange}
              placeholder="Пароль двухфакторной аутентификации"
            />
          </div>
          
          {showRequestNewCode && (
            <div style={{ marginBottom: '15px', padding: '10px', backgroundColor: '#fff3cd', borderRadius: '4px', border: '1px solid #ffc107' }}>
              <p style={{ margin: '0 0 10px 0', color: '#856404' }}>
                Код подтверждения истек. Нужен новый код?
              </p>
              <button 
                type="button"
                className="btn btn-primary"
                onClick={handleRequestNewCode}
                disabled={loading}
                style={{ fontSize: '12px', padding: '5px 15px' }}
              >
                Запросить новый код
              </button>
            </div>
          )}
          
          <div style={{ display: 'flex', gap: '10px' }}>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Проверка...' : 'Подтвердить'}
            </button>
            <button 
              type="button" 
              className="btn" 
              onClick={() => {
                setShowVerifyForm(false);
                setShowRequestNewCode(false);
                setVerificationData({ account_id: null, phone_code: '', phone_code_hash: '', password: '' });
              }}
            >
              Отмена
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

export default AccountManager;

