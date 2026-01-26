/**
 * GameExplorer Component
 * 游戏浏览界面 - 显示Steam游戏列表和详情
 */
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import '../styles/GameExplorer.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function GameExplorer() {
    const [topGames, setTopGames] = useState([]);
    const [recommendedGames, setRecommendedGames] = useState([]);
    const [loading, setLoading] = useState(true);
    const [loadingRecommendations, setLoadingRecommendations] = useState(false);
    const [error, setError] = useState(null);

    // 加载游戏数据
    useEffect(() => {
        loadTopGames();
        loadRecommendations();
    }, []);

    const loadTopGames = async () => {
        try {
            setLoading(true);
            const response = await axios.get(`${API_BASE_URL}/steam/top/games?limit=10`);
            setTopGames(response.data);
            setError(null);
        } catch (err) {
            setError('Failed to load top games');
            console.error('Failed to load top games:', err);
        } finally {
            setLoading(false);
        }
    };

    const loadRecommendations = async () => {
        try {
            setLoadingRecommendations(true);
            const response = await axios.get(`${API_BASE_URL}/recommendations?limit=10`);
            setRecommendedGames(response.data);
        } catch (err) {
            console.error('Failed to load recommendations:', err);
        } finally {
            setLoadingRecommendations(false);
        }
    };

    const recordGameClick = async (appId) => {
        try {
            await axios.post(`${API_BASE_URL}/preferences/click?app_id=${appId}`);
        } catch (err) {
            console.error('Failed to record click:', err);
        }
    };

    const handleRecommendedGameClick = async (appId) => {
        await recordGameClick(appId);
        openSteamPage(appId);
    };

    // 添加游戏到wishlist
    const addGameToLibrary = async (appId) => {
        try {
            const response = await axios.post(`${API_BASE_URL}/wishlist/${appId}?user_id=default_user`);
            alert(response.data.message);
        } catch (err) {
            console.error('Failed to add game:', err);
            if (err.response?.data?.detail) {
                alert(`Failed: ${err.response.data.detail}`);
            } else {
                alert('Failed to add game to wishlist');
            }
        }
    };

    const openSteamPage = (appId) => {
        window.open(`https://store.steampowered.com/app/${appId}`, '_blank');
    };

    if (loading) {
        return (
            <div className="loading-container">
                <div className="spinner"></div>
                <p>Loading games...</p>
            </div>
        );
    }

    return (
        <div className="game-explorer">
            <header className="page-header">
                <h1>Game Explorer</h1>
                <p>Browse and discover Steam games</p>
            </header>

            {error && (
                <div className="error-banner">
                    <p>{error}</p>
                </div>
            )}

            {/* Top Games from Steam */}
            <section className="top-games-section">
                <h2>Trending on Steam</h2>
                <div className="top-games-grid">
                    {topGames.map(game => (
                        <div key={game.app_id} className="top-game-card">
                            <div 
                                className="game-content"
                                onClick={() => openSteamPage(game.app_id)}
                                style={{ cursor: 'pointer', flex: 1 }}
                            >
                                <h3>{game.name}</h3>
                                
                                {/* Tags/Genres */}
                                {game.genres && game.genres.length > 0 && (
                                    <div className="game-tags">
                                        {game.genres.slice(0, 3).map((genre, idx) => (
                                            <span key={idx} className="tag">{genre}</span>
                                        ))}
                                    </div>
                                )}
                                
                                <div className="reviews">
                                    <span className="positive">+{game.positive_reviews}</span>
                                    <span className="negative">-{game.negative_reviews}</span>
                                </div>
                            </div>
                            <button 
                                className="add-button"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    addGameToLibrary(game.app_id);
                                }}
                                title="Add to your wishlist"
                            >
                                Add to Wishlist
                            </button>
                        </div>
                    ))}
                </div>
            </section>

            {/* Recommended Games Section */}
            <section className="recommended-games-section">
                <div className="section-header">
                    <h2>Recommended Games</h2>
                    <button 
                        className="refresh-button"
                        onClick={loadRecommendations}
                        disabled={loadingRecommendations}
                    >
                        {loadingRecommendations ? 'Loading...' : 'Refresh'}
                    </button>
                </div>
                
                {loadingRecommendations ? (
                    <div className="loading-spinner">
                        <div className="spinner"></div>
                    </div>
                ) : (
                    <div className="recommended-games-grid">
                        {recommendedGames.map(game => (
                            <div key={game.app_id || game._id} className="recommended-game-card">
                                <div 
                                    className="game-content"
                                    onClick={() => handleRecommendedGameClick(game.app_id)}
                                    style={{ cursor: 'pointer' }}
                                >
                                    <h3>{game.name}</h3>
                                    
                                    {/* Tags/Genres */}
                                    {game.genres && game.genres.length > 0 && (
                                        <div className="game-tags">
                                            {game.genres.slice(0, 3).map((genre, idx) => (
                                                <span key={idx} className="tag">{genre}</span>
                                            ))}
                                        </div>
                                    )}
                                    
                                    {game.price !== undefined && (
                                        <div className="game-price-display">
                                            {game.price ? `$${game.price}` : 'Free'}
                                        </div>
                                    )}
                                    
                                    {game.positive_reviews !== null && game.positive_reviews !== undefined && (
                                        <div className="reviews">
                                            <span className="positive">+{game.positive_reviews}</span>
                                            <span className="negative">-{game.negative_reviews}</span>
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </section>
        </div>
    );
}

export default GameExplorer;
