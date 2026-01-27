/**
 * Wishlist Component
 * 愿望单界面 - 显示用户添加的游戏收藏
 */
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import '../styles/Wishlist.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// 获取Steam游戏图片URL
const getSteamImageUrl = (appId, imageType = 'header') => {
    const imageTypes = {
        header: `https://cdn.akamai.steamstatic.com/steam/apps/${appId}/header.jpg`,
        capsule: `https://cdn.akamai.steamstatic.com/steam/apps/${appId}/capsule_231x87.jpg`,
        library: `https://cdn.akamai.steamstatic.com/steam/apps/${appId}/library_600x900.jpg`,
    };
    return imageTypes[imageType] || imageTypes.header;
};

// 计算Steam评价等级
const getReviewRating = (positive, negative) => {
    const total = positive + negative;
    if (total === 0) return { label: 'No Reviews', percentage: 0 };
    
    const percentage = (positive / total) * 100;
    
    if (percentage >= 95 && total >= 500) return { label: 'Overwhelmingly Positive', percentage };
    if (percentage >= 80) return { label: 'Very Positive', percentage };
    if (percentage >= 70 && total >= 50) return { label: 'Positive', percentage };
    if (percentage >= 70) return { label: 'Mostly Positive', percentage };
    if (percentage >= 40) return { label: 'Mixed', percentage };
    if (percentage >= 20) return { label: 'Mostly Negative', percentage };
    if (percentage < 20 && total >= 500) return { label: 'Overwhelmingly Negative', percentage };
    return { label: 'Negative', percentage };
};

function Wishlist() {
    const [games, setGames] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [imageErrors, setImageErrors] = useState({});

    // 加载游戏数据
    useEffect(() => {
        loadGames();
    }, []);

    const loadGames = async () => {
        try {
            setLoading(true);
            const response = await axios.get(`${API_BASE_URL}/wishlist?user_id=default_user`);
            setGames(response.data);
            setError(null);
        } catch (err) {
            setError('Failed to load wishlist games');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };
    const removeFromWishlist = async (appId, gameName) => {
        try {
            await axios.delete(`${API_BASE_URL}/wishlist/${appId}?user_id=default_user`);
            await loadGames();
        } catch (err) {
            console.error('Failed to remove game:', err);
            alert('Failed to remove game from wishlist');
        }
    };

    const openSteamPage = (appId) => {
        window.open(`https://store.steampowered.com/app/${appId}`, '_blank');
    };

    const handleImageError = (appId) => {
        setImageErrors(prev => ({ ...prev, [appId]: true }));
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
                                {/* Game Image */}
                                <div className="game-image-container" onClick={() => openSteamPage(game.app_id)}>
                                    {!imageErrors[game.app_id] ? (
                                        <img 
                                            src={getSteamImageUrl(game.app_id, 'header')} 
                                            alt={game.name}
                                            className="game-image"
                                            onError={() => handleImageError(game.app_id)}
                                        />
                                    ) : (
                                        <div className="game-image-placeholder">
                                            <span>🎮</span>
                                        </div>
                                    )}
                                </div>
                                
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
                                        {game.genres && game.genres.length > 0 && game.genres.slice(0, 5).map((genre, idx) => (
                                            <span key={idx} className="genre-tag">{genre}</span>
                                        ))}
                                        {game.genres && game.genres.length > 5 && (
                                            <span className="genre-tag tag-more">+{game.genres.length - 5}</span>
                                        )}
                                    </div>

                                    {(() => {
                                        const rating = getReviewRating(game.positive_reviews || 0, game.negative_reviews || 0);
                                        const getLabelClass = (label) => {
                                            if (label.includes('Positive')) return 'positive-rating';
                                            if (label.includes('Negative')) return 'negative-rating';
                                            if (label === 'Mixed') return 'mixed-rating';
                                            return '';
                                        };
                                        return (
                                            <div className="game-reviews">
                                                <div className="review-bar">
                                                    <div 
                                                        className="review-bar-positive" 
                                                        style={{ width: `${rating.percentage}%` }}
                                                    />
                                                </div>
                                                <div className={`review-label ${getLabelClass(rating.label)}`}>{rating.label}</div>
                                            </div>
                                        );
                                    })()}
                                </div>
                                
                                <button 
                                    className="remove-button"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        removeFromWishlist(game.app_id, game.name);
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
