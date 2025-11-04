// API configuration
// В production используем тот же домен (если фронт и бэк на одном домене)
// или явный URL бэкенда
const API_BASE = process.env.REACT_APP_API_URL || 
                window.location.origin.includes('twc1.net') 
                  ? 'https://wemdio-parser-0daf.twc1.net' 
                  : 'http://localhost:8000';

export default API_BASE + '/api';

