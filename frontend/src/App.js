/**
 * SteamGameRecSys Frontend - Main Application
 * React应用主文件 - 路由配置和布局
 */
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import GameExplorer from './components/GameExplorer';
import SentimentPage from './components/SentimentPage';
import Wishlist from './components/Wishlist';
import './styles/App.css';

function App() {
    return (
        <Router>
            <div className="app">
                {/* Sidebar Navigation */}
                <nav className="sidebar">
                    <div className="sidebar-header">
                        <h1>SteamGameRecSys</h1>
                        <p>游戏推荐与智能分析</p>
                    </div>

                    <ul className="nav-links">
                        <li>
                            <Link to="/" className="nav-link">
                                <span>Game Explorer</span>
                            </Link>
                        </li>
                        <li>
                            <Link to="/wishlist" className="nav-link">
                                <span>My Wishlist</span>
                            </Link>
                        </li>
                        <li>
                            <Link to="/sentiment" className="nav-link">
                                <span>Sentiment Analysis</span>
                            </Link>
                        </li>
                    </ul>

                    <div className="sidebar-footer">
                        <p>Powered by BERT & Steam API</p>
                    </div>
                </nav>

                {/* Main Content Area */}
                <main className="main-content">
                    <Routes>
                        <Route path="/" element={<GameExplorer />} />
                        <Route path="/wishlist" element={<Wishlist />} />
                        <Route path="/sentiment" element={<SentimentPage />} />
                    </Routes>
                </main>
            </div>
        </Router>
    );
}

export default App;
