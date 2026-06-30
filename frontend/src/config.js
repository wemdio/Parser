// API configuration
// Merged single-app deploy: the backend serves this built frontend, so default
// to the SAME origin (relative "/api"). Override with REACT_APP_API_URL only for
// split/local setups (e.g. REACT_APP_API_URL=http://localhost:8000 for dev).
const API_BASE = process.env.REACT_APP_API_URL || '';

export default API_BASE + '/api';

