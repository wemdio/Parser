import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './index.css';
import AccountManager from './components/AccountManager';
import AccountList from './components/AccountList';
import ChatSelector from './components/ChatSelector';
import ParserControls from './components/ParserControls';

const API_BASE = 'http://localhost:8000/api';

function App() {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE}/accounts/`);
      setAccounts(response.data.accounts || []);
      setError(null);
    } catch (err) {
      setError('Ошибка загрузки аккаунтов: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleAccountAdded = () => {
    loadAccounts();
  };

  const handleAccountVerified = () => {
    loadAccounts();
  };

  if (loading && accounts.length === 0) {
    return <div className="loading">Загрузка...</div>;
  }

  return (
    <div className="container">
      <h1>Telegram Chat Parser</h1>
      
      {error && <div className="error-message">{error}</div>}

      <AccountManager 
        onAccountAdded={handleAccountAdded}
        onAccountVerified={handleAccountVerified}
      />

      <AccountList accounts={accounts} onRefresh={loadAccounts} />

      <ChatSelector accounts={accounts} />

      <ParserControls />
    </div>
  );
}

export default App;

