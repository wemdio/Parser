import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './ParsingStats.css';
import API_BASE from '../config';

function ParsingStats() {
  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [sessionDetails, setSessionDetails] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadSessions();
    // Обновляем каждые 30 секунд
    const interval = setInterval(loadSessions, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadSessions = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE}/stats/parsing-sessions`);
      if (response.data.success) {
        setSessions(response.data.sessions);
      }
      setError(null);
    } catch (err) {
      console.error('Error loading sessions:', err);
      setError('Ошибка загрузки статистики');
    } finally {
      setLoading(false);
    }
  };

  const loadSessionDetails = async (sessionId) => {
    try {
      const response = await axios.get(`${API_BASE}/stats/parsing-stats?session_id=${sessionId}`);
      if (response.data.success) {
        setSessionDetails(response.data.logs);
        setSelectedSession(sessionId);
      }
    } catch (err) {
      console.error('Error loading session details:', err);
      setError('Ошибка загрузки деталей сессии');
    }
  };

  const formatDate = (isoString) => {
    const date = new Date(isoString);
    return date.toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusBadge = (status) => {
    const badges = {
      'success': { class: 'badge-success', text: '✅ Успех' },
      'error': { class: 'badge-error', text: '❌ Ошибка' },
      'skipped': { class: 'badge-skipped', text: '⏭️ Пропущено' }
    };
    const badge = badges[status] || { class: '', text: status };
    return <span className={`status-badge ${badge.class}`}>{badge.text}</span>;
  };

  const getErrorBadge = (errorType) => {
    const badges = {
      'FLOOD_WAIT': { class: 'error-flood', text: '⏳ Rate Limit' },
      'PeerIdInvalid': { class: 'error-peer', text: '🚫 Недоступен' },
      'Other': { class: 'error-other', text: '❌ Другая ошибка' }
    };
    const badge = badges[errorType] || { class: 'error-other', text: errorType };
    return <span className={`error-badge ${badge.class}`}>{badge.text}</span>;
  };

  if (loading && sessions.length === 0) {
    return <div className="loading">⏳ Загрузка статистики...</div>;
  }

  return (
    <div className="parsing-stats-container">
      <div className="stats-header">
        <h1>📊 Статистика парсинга</h1>
        <button className="btn btn-primary" onClick={loadSessions}>
          🔄 Обновить
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {/* Список сессий */}
      <div className="sessions-list">
        <h2>История запусков</h2>
        {sessions.length === 0 ? (
          <p className="no-data">Пока нет данных о парсинге</p>
        ) : (
          <div className="sessions-grid">
            {sessions.map((session) => (
              <div
                key={session.session_id}
                className={`session-card ${selectedSession === session.session_id ? 'selected' : ''}`}
                onClick={() => loadSessionDetails(session.session_id)}
              >
                <div className="session-header">
                  <span className="session-time">⏰ {formatDate(session.started_at)}</span>
                  <span className="session-accounts">
                    👤 {session.accounts.length} аккаунт(ов)
                  </span>
                </div>
                
                <div className="session-stats">
                  <div className="stat-item">
                    <span className="stat-label">Чатов:</span>
                    <span className="stat-value">{session.total_chats}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Сообщений:</span>
                    <span className="stat-value">{session.total_messages}</span>
                  </div>
                </div>

                <div className="session-status">
                  <span className="status-success">✅ {session.success_count}</span>
                  {session.error_count > 0 && (
                    <span className="status-error">❌ {session.error_count}</span>
                  )}
                  {session.skipped_count > 0 && (
                    <span className="status-skipped">⏭️ {session.skipped_count}</span>
                  )}
                </div>

                {session.errors.length > 0 && (
                  <div className="session-errors-preview">
                    ⚠️ {session.errors.length} ошибок
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Детали выбранной сессии */}
      {selectedSession && sessionDetails.length > 0 && (
        <div className="session-details">
          <h2>Детали сессии</h2>
          <button 
            className="btn btn-secondary"
            onClick={() => setSelectedSession(null)}
          >
            ← Назад к списку
          </button>

          <div className="details-table-container">
            <table className="details-table">
              <thead>
                <tr>
                  <th>Статус</th>
                  <th>Чат</th>
                  <th>Аккаунт</th>
                  <th>Найдено</th>
                  <th>Сохранено</th>
                  <th>Пропущено</th>
                  <th>Время (сек)</th>
                  <th>Ошибка</th>
                </tr>
              </thead>
              <tbody>
                {sessionDetails.map((log, index) => (
                  <tr key={index} className={`row-${log.status}`}>
                    <td>{getStatusBadge(log.status)}</td>
                    <td className="chat-name">
                      <strong>{log.chat_name}</strong>
                      <br />
                      <small>ID: {log.chat_id}</small>
                    </td>
                    <td>{log.phone_number}</td>
                    <td>{log.messages_found}</td>
                    <td className="saved-count">{log.messages_saved}</td>
                    <td>{log.messages_skipped}</td>
                    <td>{log.execution_time_seconds?.toFixed(2) || '—'}</td>
                    <td>
                      {log.error_type && (
                        <div className="error-details">
                          {getErrorBadge(log.error_type)}
                          {log.error_message && (
                            <div className="error-message-detail">
                              {log.error_message}
                            </div>
                          )}
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default ParsingStats;
