/**
 * Wishlist Component
 * 愿望单界面 - 显示用户添加的游戏收藏
 */
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import '../styles/Wishlist.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function Wishlist() {
    const [games, setGames] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [searchQuery, setSearchQuery] = useState('');

    // 加载游戏数据
    useEffect(() => {
        loadGames();
    }, []);

    const loadGames = async () => {
        try {
            setLoading(true);
            const response = await axios.get(`${API_BASE_URL}/games`);
            setGames(response.data);
            setError(null);
        } catch (err) {
            setError('Failed to load wishlist games');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };
    const removeFromWishlist = async (gameId, gameName) => {
        if (!window.confirm(`Remove "${gameName}" from your wishlist?`)) {
            return;
        }
        
        try {
            await axios.delete(`${API_BASE_URL}/games/${gameId}`);
            await loadGames();
            alert(`${gameName} has been removed from your wishlist`);
        } catch (err) {
            console.error('Failed to remove game:', err);
            alert('Failed to remove game from wishlist');
        }
    };

    const openSteamPage = (appId) => {
        window.open(`https://store.steampowered.com/app/${appId}`, '_blank');
    };
    // 过滤游戏
    const filteredGames = games.filter(game =>
        game.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    if (loading) {
        return (
            <div className="loading-container">
                <div className="spinner"></div>
                <p>Loading wishlist...</p>
            </div>
        );
    }

    return (
        <div className="wishlist">
            <header className="page-header">
                <h1>My Wishlist</h1>
                <p>Your saved games collection</p>
            </header>

            {/* Search Bar */}
            <div className="search-section">
                <input
                    type="text"
                    className="search-input"
                    placeholder="Search in wishlist..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                />
            </div>

            {error && (
                <div className="error-banner">
                    {error}
                </div>
            )}

            {/* Wishlist Games */}
            <section className="wishlist-section">
                <h2>Saved Games ({filteredGames.length})</h2>

                {filteredGames.length === 0 ? (
                    <div className="empty-state">
                        <p>Your wishlist is empty. Add games from Game Explorer!</p>
                    </div>
                ) : (
                    <div className="games-grid">
                        {filteredGames.map(game => (
                            <div key={game._id} className="game-card">
                                <div 
                                    className="game-content" 
                                    onClick={() => openSteamPage(game.app_id)}
                                    style={{ cursor: 'pointer' }}
                                >
                                    <div className="game-header">
                                        <h3>{game.name}</h3>
                                        <span className="game-price">
                                            {game.price ? `$${game.price}` : 'Free'}
                                        </span>
                                    </div>

                                    <div className="game-genres">
                                        {game.genres && game.genres.length > 0 && game.genres.slice(0, 3).map((genre, idx) => (
                                            <span key={idx} className="genre-tag">{genre}</span>
                                        ))}
                                    </div>

                                    <p className="game-description">
                                        {game.description?.substring(0, 100)}...
                                    </p>

                                    {game.positive_reviews !== null && (
                                        <div className="game-reviews">
                                            <span className="positive">
                                                +{game.positive_reviews}
                                            </span>
                                            <span className="negative">
                                                -{game.negative_reviews}
                                            </span>
                                        </div>
                                    )}
                                </div>
                                
                                <button 
                                    className="remove-button"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        removeFromWishlist(game._id, game.name);
                                    }}
                                    title="Remove from wishlist"
                                >
                                    Remove
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </section>
        </div>
    );
}

export default Wishlist;
