import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import './index.css';
import HomePage from './pages/HomePage';
import ParsingStats from './components/ParsingStats';

function Navigation() {
  const location = useLocation();
  
  return (
    <nav className="navigation">
      <Link 
        to="/" 
        className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}
      >
        🏠 Главная
      </Link>
      <Link 
        to="/stats" 
        className={`nav-link ${location.pathname === '/stats' ? 'active' : ''}`}
      >
        📊 Статистика
      </Link>
    </nav>
  );
}

function App() {
  return (
    <Router>
      <div className="container">
        <h1>Telegram Chat Parser</h1>
        <Navigation />
        
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/stats" element={<ParsingStats />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;

