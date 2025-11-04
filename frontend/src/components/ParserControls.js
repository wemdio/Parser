import React, { useState } from 'react';
import axios from 'axios';
import './ParserControls.css';
import API_BASE from '../config';

function ParserControls() {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [isRunning, setIsRunning] = useState(false);

  const handleStartParsing = async () => {
    setLoading(true);
    setMessage(null);

    try {
      await axios.post(`${API_BASE}/parser/start`);
      setMessage({ 
        type: 'success', 
        text: 'Парсинг запущен! Сообщения будут сохраняться в базу данных. Парсинг будет автоматически запускаться каждый час.' 
      });
      setIsRunning(true);
    } catch (error) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Ошибка запуска парсинга' 
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card parser-controls">
      <h2>Управление парсером</h2>
      
      {message && (
        <div className={`message message-${message.type}`}>
          {message.text}
        </div>
      )}

      <div className="parser-info">
        <p>
          <strong>Как это работает:</strong>
        </p>
        <ul>
          <li>Парсер собирает сообщения за последний час из выбранных чатов</li>
          <li>После запуска парсинг будет автоматически выполняться каждый час</li>
          <li>Все сообщения сохраняются в базу данных Supabase</li>
          <li>Сохраняются следующие данные: время сообщения, название чата, имя и фамилия, username, био, текст сообщения</li>
        </ul>
      </div>

      <button 
        className={`btn ${isRunning ? 'btn-success' : 'btn-primary'}`}
        onClick={handleStartParsing}
        disabled={loading || isRunning}
      >
        {loading ? 'Запуск...' : isRunning ? 'Парсинг запущен' : 'Запустить парсинг'}
      </button>

      {isRunning && (
        <div className="running-status">
          <span className="status-indicator"></span>
          Парсер работает и будет автоматически обновлять данные каждый час
        </div>
      )}
    </div>
  );
}

export default ParserControls;

