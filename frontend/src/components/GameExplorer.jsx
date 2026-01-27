/**
 * GameExplorer Component
 * 游戏浏览界面 - 显示Steam游戏列表和详情
 */
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import '../styles/GameExplorer.css';

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

function GameExplorer() {
    const [topGames, setTopGames] = useState([]);
    const [recommendedGames, setRecommendedGames] = useState([]);
    const [loading, setLoading] = useState(true);
    const [loadingRecommendations, setLoadingRecommendations] = useState(false);
    const [error, setError] = useState(null);
    const [imageErrors, setImageErrors] = useState({});
    const [wishlistAppIds, setWishlistAppIds] = useState(new Set());
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState([]);
    const [searching, setSearching] = useState(false);

    // 加载游戏数据和愿望单
    useEffect(() => {
        loadTopGames();
        loadRecommendations();
        loadWishlist();
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

    const loadWishlist = async () => {
        try {
            const response = await axios.get(`${API_BASE_URL}/wishlist?user_id=default_user`);
            const appIds = new Set(response.data.map(game => game.app_id));
            setWishlistAppIds(appIds);
        } catch (err) {
            console.error('Failed to load wishlist:', err);
        }
    };

    const handleSearch = async (e) => {
        e.preventDefault();
        if (!searchQuery.trim()) {
            setSearchResults([]);
            return;
        }

        try {
            setSearching(true);
            const response = await axios.get(`${API_BASE_URL}/games/search?q=${encodeURIComponent(searchQuery)}&limit=20`);
            setSearchResults(response.data);
        } catch (err) {
            console.error('Failed to search games:', err);
            setError('搜索失败，请重试');
        } finally {
            setSearching(false);
        }
    };

    const clearSearch = () => {
        setSearchQuery('');
        setSearchResults([]);
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
            // 更新本地wishlist状态
            setWishlistAppIds(prev => new Set([...prev, appId]));
        } catch (err) {
            console.error('Failed to add game:', err);
            if (err.response?.data?.detail) {
                alert(`Failed: ${err.response.data.detail}`);
            } else {
                alert('Failed to add game to wishlist');
            }
        }
    };

    // 检查游戏是否已在wishlist中
    const isInWishlist = (appId) => {
        return wishlistAppIds.has(appId);
    };

    const openSteamPage = (appId) => {
        window.open(`https://store.steampowered.com/app/${appId}`, '_blank');
    };

    const handleImageError = (appId) => {
        setImageErrors(prev => ({ ...prev, [appId]: true }));
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
                <div className="header-content">
                    <div className="header-text">
                        <h1>Game Explorer</h1>
                        <p>Browse and discover Steam games</p>
                    </div>
                    <form className="search-form" onSubmit={handleSearch}>
                        <input
                            type="text"
                            className="search-input"
                            placeholder="Search by game name or tags..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                        <button type="submit" className="search-button" disabled={searching}>
                            {searching ? 'Searching...' : 'Search'}
                        </button>
                        {searchQuery && (
                            <button type="button" className="clear-button" onClick={clearSearch}>
                                ✕
                            </button>
                        )}
                    </form>
                </div>
            </header>

            {error && (
                <div className="error-banner">
                    <p>{error}</p>
                </div>
            )}

            {/* Search Results */}
            {searchResults.length > 0 && (
                <section className="search-results-section">
                    <div className="section-header">
                        <h2>Search Results ({searchResults.length})</h2>
                        <button className="clear-search-button" onClick={clearSearch}>
                            Clear Search
                        </button>
                    </div>
                    <div className="search-results-grid">
                        {searchResults.map(game => (
                            <div key={game.app_id} className="top-game-card">
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
                                    style={{ cursor: 'pointer', flex: 1 }}
                                >
                                    <h3>{game.name}</h3>
                                    
                                    {game.genres && game.genres.length > 0 && (
                                        <div className="game-tags">
                                            {game.genres.slice(0, 5).map((genre, idx) => (
                                                <span key={idx} className="tag">{genre}</span>
                                            ))}
                                            {game.genres.length > 5 && (
                                                <span className="tag tag-more">+{game.genres.length - 5}</span>
                                            )}
                                        </div>
                                    )}
                                    
                                    {(() => {
                                        const rating = getReviewRating(game.positive_reviews || 0, game.negative_reviews || 0);
                                        return (
                                            <div className="reviews">
                                                <div className="review-bar">
                                                    <div 
                                                        className="review-bar-positive" 
                                                        style={{ width: `${rating.percentage}%` }}
                                                    />
                                                </div>
                                                <div className="review-label">{rating.label}</div>
                                            </div>
                                        );
                                    })()}
                                </div>
                                <button 
                                    className={`add-button ${isInWishlist(game.app_id) ? 'in-wishlist' : ''}`}
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        if (!isInWishlist(game.app_id)) {
                                            addGameToLibrary(game.app_id);
                                        }
                                    }}
                                    title={isInWishlist(game.app_id) ? "Already in wishlist" : "Add to your wishlist"}
                                    disabled={isInWishlist(game.app_id)}
                                >
                                    {isInWishlist(game.app_id) ? '✓ In Wishlist' : 'Add to Wishlist'}
                                </button>
                            </div>
                        ))}
                    </div>
                </section>
            )}

            {/* Top Games from Steam */}
            <section className="top-games-section">
                <h2>Trending on Steam</h2>
                <div className="top-games-grid">
                    {topGames.map(game => (
                        <div key={game.app_id} className="top-game-card">
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
                                style={{ cursor: 'pointer', flex: 1 }}
                            >
                                <h3>{game.name}</h3>
                                
                                {/* Tags/Genres */}
                                {game.genres && game.genres.length > 0 && (
                                    <div className="game-tags">
                                        {game.genres.slice(0, 5).map((genre, idx) => (
                                            <span key={idx} className="tag">{genre}</span>
                                        ))}
                                        {game.genres.length > 5 && (
                                            <span className="tag tag-more">+{game.genres.length - 5}</span>
                                        )}
                                    </div>
                                )}
                                
                                {(() => {
                                    const rating = getReviewRating(game.positive_reviews || 0, game.negative_reviews || 0);
                                    const getLabelClass = (label) => {
                                        if (label.includes('Positive')) return 'positive-rating';
                                        if (label.includes('Negative')) return 'negative-rating';
                                        if (label === 'Mixed') return 'mixed-rating';
                                        return '';
                                    };
                                    return (
                                        <div className="reviews">
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
                                className={`add-button ${isInWishlist(game.app_id) ? 'in-wishlist' : ''}`}
                                onClick={(e) => {
                                    e.stopPropagation();
                                    if (!isInWishlist(game.app_id)) {
                                        addGameToLibrary(game.app_id);
                                    }
                                }}
                                title={isInWishlist(game.app_id) ? "Already in wishlist" : "Add to your wishlist"}
                                disabled={isInWishlist(game.app_id)}
                            >
                                {isInWishlist(game.app_id) ? '✓ In Wishlist' : 'Add to Wishlist'}
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
                                {/* Game Image */}
                                <div className="game-image-container" onClick={() => handleRecommendedGameClick(game.app_id)}>
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
                                    onClick={() => handleRecommendedGameClick(game.app_id)}
                                    style={{ cursor: 'pointer' }}
                                >
                                    <h3>{game.name}</h3>
                                    
                                    {/* Tags/Genres */}
                                    {game.genres && game.genres.length > 0 && (
                                        <div className="game-tags">
                                            {game.genres.slice(0, 5).map((genre, idx) => (
                                                <span key={idx} className="tag">{genre}</span>
                                            ))}
                                            {game.genres.length > 5 && (
                                                <span className="tag tag-more">+{game.genres.length - 5}</span>
                                            )}
                                        </div>
                                    )}
                                    
                                    {game.price !== undefined && (
                                        <div className="game-price-display">
                                            {game.price ? `$${game.price}` : 'Free'}
                                        </div>
                                    )}
                                    
                                    {(() => {
                                        const rating = getReviewRating(game.positive_reviews || 0, game.negative_reviews || 0);
                                        const getLabelClass = (label) => {
                                            if (label.includes('Positive')) return 'positive-rating';
                                            if (label.includes('Negative')) return 'negative-rating';
                                            if (label === 'Mixed') return 'mixed-rating';
                                            return '';
                                        };
                                        return (
                                            <div className="reviews">
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
                                    className={`add-button ${isInWishlist(game.app_id) ? 'in-wishlist' : ''}`}
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        if (!isInWishlist(game.app_id)) {
                                            addGameToLibrary(game.app_id);
                                        }
                                    }}
                                    title={isInWishlist(game.app_id) ? "Already in wishlist" : "Add to your wishlist"}
                                    disabled={isInWishlist(game.app_id)}
                                >
                                    {isInWishlist(game.app_id) ? '✓ In Wishlist' : 'Add to Wishlist'}
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </section>
        </div>
    );
}

export default GameExplorer;
