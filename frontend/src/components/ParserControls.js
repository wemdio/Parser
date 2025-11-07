import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './ParserControls.css';
import API_BASE from '../config';

function ParserControls() {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [autoParsingEnabled, setAutoParsingEnabled] = useState(true);
  const [nextRun, setNextRun] = useState(null);

  // Проверяем статус парсера и автопарсинга при загрузке
  useEffect(() => {
    checkParserStatus();
    checkScheduleStatus();
    // Обновляем статус каждые 5 секунд
    const interval = setInterval(() => {
      checkParserStatus();
      checkScheduleStatus();
    }, 5000);
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

  const checkScheduleStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE}/parser/schedule/status`);
      setAutoParsingEnabled(response.data.auto_parsing_enabled);
      setNextRun(response.data.next_run);
    } catch (error) {
      console.error('Error checking schedule status:', error);
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

  const handlePauseSchedule = async () => {
    setLoading(true);
    setMessage(null);

    try {
      await axios.post(`${API_BASE}/parser/schedule/pause`);
      setMessage({ 
        type: 'warning', 
        text: '⏸️ Автоматический парсинг ВЫКЛЮЧЕН. Парсинг по расписанию больше не будет запускаться.' 
      });
      await checkScheduleStatus();
    } catch (error) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Ошибка выключения автопарсинга' 
      });
    } finally {
      setLoading(false);
    }
  };

  const handleResumeSchedule = async () => {
    setLoading(true);
    setMessage(null);

    try {
      const response = await axios.post(`${API_BASE}/parser/schedule/resume`);
      setMessage({ 
        type: 'success', 
        text: `▶️ Автоматический парсинг ВКЛЮЧЕН. ${response.data.message || ''}` 
      });
      await checkScheduleStatus();
    } catch (error) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Ошибка включения автопарсинга' 
      });
    } finally {
      setLoading(false);
    }
  };

  const formatNextRun = (isoString) => {
    if (!isoString) return 'не запланировано';
    try {
      const date = new Date(isoString);
      return date.toLocaleString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return 'ошибка форматирования';
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

      {/* Блок автоматического парсинга */}
      <div className="auto-parsing-section">
        <h3>⏰ Автоматический парсинг (каждый час)</h3>
        <div className="auto-parsing-status">
          <div className={`status-badge ${autoParsingEnabled ? 'status-active' : 'status-paused'}`}>
            {autoParsingEnabled ? '✅ Включен' : '⏸️ Выключен'}
          </div>
          {autoParsingEnabled && nextRun && (
            <div className="next-run-info">
              Следующий запуск: <strong>{formatNextRun(nextRun)}</strong>
            </div>
          )}
        </div>
        <div className="parser-buttons">
          {autoParsingEnabled ? (
            <button 
              className="btn btn-warning"
              onClick={handlePauseSchedule}
              disabled={loading}
            >
              {loading ? 'Отключение...' : '⏸️ Выключить авто-парсинг'}
            </button>
          ) : (
            <button 
              className="btn btn-success"
              onClick={handleResumeSchedule}
              disabled={loading}
            >
              {loading ? 'Включение...' : '▶️ Включить авто-парсинг'}
            </button>
          )}
        </div>
      </div>

      <hr />

      {/* Блок ручного запуска */}
      <div className="manual-parsing-section">
        <h3>🚀 Ручной запуск парсинга</h3>
        <div className="parser-info">
          <p>
            <strong>Как это работает:</strong>
          </p>
          <ul>
            <li>Парсер собирает сообщения за последний час из выбранных чатов</li>
            <li>Все сообщения сохраняются в базу данных Supabase</li>
            <li>Сохраняются: время, название чата, имя и фамилия, username, био, текст сообщения</li>
          </ul>
        </div>

        <div className="parser-buttons">
          <button 
            className={`btn ${isRunning ? 'btn-success' : 'btn-primary'}`}
            onClick={handleStartParsing}
            disabled={loading || isRunning}
          >
            {loading && !isRunning ? 'Запуск...' : isRunning ? 'Парсинг запущен ✓' : 'Запустить парсинг сейчас'}
          </button>

          {isRunning && (
            <button 
              className="btn btn-danger"
              onClick={handleStopParsing}
              disabled={loading}
            >
              {loading ? 'Остановка...' : 'Остановить текущий парсинг'}
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
    </div>
  );
}

export default ParserControls;

