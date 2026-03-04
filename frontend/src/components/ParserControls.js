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
  const [realtime, setRealtime] = useState({ running: false, accounts: 0, messages_received: 0 });

  useEffect(() => {
    checkParserStatus();
    checkScheduleStatus();
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
      if (response.data.realtime) {
        setRealtime(response.data.realtime);
      }
    } catch (error) {
      console.error('Error checking schedule status:', error);
    }
  };

  const handleRealtimeToggle = async () => {
    setLoading(true);
    setMessage(null);
    try {
      if (realtime.running) {
        await axios.post(`${API_BASE}/parser/realtime/stop`);
        setMessage({ type: 'warning', text: 'Real-time режим остановлен.' });
      } else {
        await axios.post(`${API_BASE}/parser/realtime/start`);
        setMessage({ type: 'success', text: 'Real-time режим запущен! Сообщения будут приходить мгновенно.' });
      }
      await checkScheduleStatus();
    } catch (error) {
      setMessage({ type: 'error', text: error.response?.data?.detail || 'Ошибка управления real-time' });
    } finally {
      setLoading(false);
    }
  };

  const handleRealtimeRestart = async () => {
    setLoading(true);
    setMessage(null);
    try {
      await axios.post(`${API_BASE}/parser/realtime/restart`);
      setMessage({ type: 'success', text: 'Real-time перезапущен. Чаты обновлены.' });
      await checkScheduleStatus();
    } catch (error) {
      setMessage({ type: 'error', text: error.response?.data?.detail || 'Ошибка перезапуска' });
    } finally {
      setLoading(false);
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

      {/* Блок Real-time */}
      <div className="auto-parsing-section">
        <h3>⚡ Real-time режим</h3>
        <div className="auto-parsing-status">
          <div className={`status-badge ${realtime.running ? 'status-active' : 'status-paused'}`}>
            {realtime.running ? '⚡ Активен' : '⏸️ Выключен'}
          </div>
          {realtime.running && (
            <div className="next-run-info">
              Аккаунтов: <strong>{realtime.accounts}</strong> &nbsp;|&nbsp; 
              Получено сообщений: <strong>{realtime.messages_received}</strong>
              {realtime.queue_size > 0 && (
                <> &nbsp;|&nbsp; В очереди: <strong>{realtime.queue_size}</strong></>
              )}
            </div>
          )}
        </div>
        <div className="parser-buttons">
          <button 
            className={`btn ${realtime.running ? 'btn-warning' : 'btn-success'}`}
            onClick={handleRealtimeToggle}
            disabled={loading}
          >
            {loading ? '...' : realtime.running ? '⏸️ Остановить real-time' : '⚡ Запустить real-time'}
          </button>
          {realtime.running && (
            <button 
              className="btn btn-primary"
              onClick={handleRealtimeRestart}
              disabled={loading}
            >
              {loading ? '...' : '🔄 Перезапустить (обновить чаты)'}
            </button>
          )}
        </div>
      </div>

      <hr />

      {/* Блок автоматического парсинга (fallback) */}
      <div className="auto-parsing-section">
        <h3>⏰ Batch-парсинг (страховка, каждые 30 мин)</h3>
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
              {loading ? 'Отключение...' : '⏸️ Выключить batch-парсинг'}
            </button>
          ) : (
            <button 
              className="btn btn-success"
              onClick={handleResumeSchedule}
              disabled={loading}
            >
              {loading ? 'Включение...' : '▶️ Включить batch-парсинг'}
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
            <li><strong>Real-time:</strong> сообщения приходят мгновенно (задержка &lt; 3 сек)</li>
            <li><strong>Batch-парсинг:</strong> страховка каждые 30 мин, подбирает пропущенное</li>
            <li><strong>Ручной запуск:</strong> собирает сообщения за последний час прямо сейчас</li>
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

