import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './ParserControls.css';
import API_BASE from '../config';

function ParserControls() {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [isRunning, setIsRunning] = useState(false);

  // Проверяем статус парсера при загрузке
  useEffect(() => {
    checkParserStatus();
    // Обновляем статус каждые 5 секунд
    const interval = setInterval(checkParserStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const checkParserStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE}/parser/status`);
      setIsRunning(response.data.is_running);
    } catch (error) {
      console.error('Error checking parser status:', error);
    }
  };

  const handleStartParsing = async () => {
    setLoading(true);
    setMessage(null);

    try {
      await axios.post(`${API_BASE}/parser/start`);
      setMessage({ 
        type: 'success', 
        text: 'Парсинг запущен! Сообщения будут сохраняться в базу данных.' 
      });
      setIsRunning(true);
      checkParserStatus();
    } catch (error) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Ошибка запуска парсинга' 
      });
    } finally {
      setLoading(false);
    }
  };

  const handleStopParsing = async () => {
    setLoading(true);
    setMessage(null);

    try {
      await axios.post(`${API_BASE}/parser/stop`);
      setMessage({ 
        type: 'info', 
        text: 'Сигнал остановки отправлен. Парсер остановится после завершения текущей операции.' 
      });
      setTimeout(checkParserStatus, 2000);
    } catch (error) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Ошибка остановки парсинга' 
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
          <li>Все сообщения сохраняются в базу данных Supabase</li>
          <li>Сохраняются следующие данные: время сообщения, название чата, имя и фамилия, username, био, текст сообщения</li>
        </ul>
      </div>

      <div className="parser-buttons">
        <button 
          className={`btn ${isRunning ? 'btn-success' : 'btn-primary'}`}
          onClick={handleStartParsing}
          disabled={loading || isRunning}
        >
          {loading && !isRunning ? 'Запуск...' : isRunning ? 'Парсинг запущен ✓' : 'Запустить парсинг'}
        </button>

        {isRunning && (
          <button 
            className="btn btn-danger"
            onClick={handleStopParsing}
            disabled={loading}
          >
            {loading ? 'Остановка...' : 'Остановить парсинг'}
          </button>
        )}
      </div>

      {isRunning && (
        <div className="running-status">
          <span className="status-indicator"></span>
          Парсер работает. Нажмите "Остановить" для завершения.
        </div>
      )}
    </div>
  );
}

export default ParserControls;

