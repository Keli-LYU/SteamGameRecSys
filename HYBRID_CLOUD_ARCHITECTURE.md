# Hybrid Cloud Architecture Design Document

## 📋 Architecture Overview

### Original Architecture
- **Local Storage** + **Cloud Computing**
- MongoDB running in local Docker container
- All services running locally

### New Architecture (Hybrid Cloud)
- **Cloud Database Storage** - MongoDB Atlas (Cloud-hosted)
- **Cloud Auto Crawler** - Scheduled tasks to automatically crawl Steam data
- **Local Computing** - Recommendation system and sentiment analysis processed locally
- **Local User Preferences** - User click preference data stored locally

## 🏗️ Architecture Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        Cloud                                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐    ┌──────────────────────────────┐   │
│  │  MongoDB Atlas      │◄───│  Cloud Crawler Service       │   │
│  │  (Game Database)    │    │  (Scheduled Steam Crawler)   │   │
│  │  - games collection │    │  - Cron: Daily execution     │   │
│  │  - sentiment_logs   │    │  - Auto-import new games     │   │
│  └──────▲──────────────┘    └──────────────────────────────┘   │
│         │                                                        │
└─────────┼────────────────────────────────────────────────────────┘
          │ MongoDB Connection (Cloud URI)
          │
┌─────────┼────────────────────────────────────────────────────────┐
│         │                  Local                                 │
├─────────┼────────────────────────────────────────────────────────┤
│         │                                                         │
│  ┌──────▼──────────────┐    ┌──────────────────────────────┐   │
│  │  Backend Service    │    │  Local SQLite DB             │   │
│  │  (Local FastAPI)    │    │  (User Preferences)          │   │
│  │  - Recommendation   │◄───│  - user_preferences table    │   │
│  │  - Sentiment (BERT) │    │  - User click history        │   │
│  │  - Read cloud data  │    │  - Offline available         │   │
│  └──────▲──────────────┘    └──────────────────────────────┘   │
│         │                                                         │
│  ┌──────┴──────────────┐                                        │
│  │  Frontend (React)   │                                        │
│  │  - User Interface   │                                        │
│  │  - Game Explorer    │                                        │
│  │  - Recommendations  │                                        │
│  └─────────────────────┘                                        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## 🔑 Core Design Principles

### 1. Data Separation Strategy
- **Game Data (Cloud)**: Game metadata, reviews, prices stored in MongoDB Atlas
- **User Data (Local)**: User click preferences, browsing history stored in local SQLite

### 2. Local Computing
- **Recommendation Algorithm**: Computed locally to protect user privacy
- **BERT Sentiment Analysis**: Large model runs locally, no data upload to cloud
- **Data Caching**: Cache frequently used game data locally to reduce cloud access

### 3. Cloud Automation
- **Scheduled Crawler**: Cloud cron job updates Steam data daily automatically
- **Data Synchronization**: Auto-sync new games and price changes to MongoDB Atlas
- **No Local Intervention**: Data updates are fully automated

## 📂 Database Design

### Cloud MongoDB Atlas
```javascript
// games - Game base data (public read-only)
{
  app_id: 730,
  name: "Counter-Strike 2",
  price: 0,
  genres: ["Action", "FPS"],
  positive_reviews: 500000,
  negative_reviews: 20000,
  updated_at: "2026-01-19"
}

// sentiment_logs - Sentiment analysis logs (optional, can be local)
{
  review_text: "Great game!",
  sentiment: "POSITIVE",
  score: 0.98,
  timestamp: "2026-01-19T10:00:00Z"
}
```

### Local SQLite
```sql
-- user_preferences - User preference data (private data)
CREATE TABLE user_preferences (
    user_id TEXT PRIMARY KEY,
    genre_weights TEXT,  -- JSON: {"Action": 5, "RPG": 3}
    clicked_games TEXT,  -- JSON: [730, 440, 570]
    updated_at TIMESTAMP
);

-- game_cache - Local game cache
CREATE TABLE game_cache (
    app_id INTEGER PRIMARY KEY,
    game_data TEXT,  -- JSON full game data
    cached_at TIMESTAMP
);

## 📊 Performance Optimization

### 1. Local Caching Strategy
```python
# Cache popular games to local SQLite
# Reduce cloud database access
cache_ttl = 3600  # 1 hour cache
```

### 2. Connection Pool Configuration
```python
# MongoDB connection pool optimization
client = AsyncIOMotorClient(
    MONGODB_URL,
    maxPoolSize=50,
    minPoolSize=10
)
```

### 3. Read/Write Separation
- **Read Operations**: Read from local cache first, access cloud on cache miss
- **Write Operations**: User preferences write to local, game data read-only from cloud

## 💰 Cost Estimation

| Component | Service | Configuration | Monthly Cost |
|-----------|---------|--------------|--------------|
| Cloud Database | MongoDB Atlas | M0 (512MB) | Free |
| Cloud Crawler | GitHub Actions | 2000 min/month | Free |
| Local Computing | Own Hardware | - | Electricity |
| **Total** | | | **~$0** |

Upgrade Plan (Production):
- MongoDB Atlas M10: $57/month (2GB storage, dedicated resources)
- Cloud Server (Lightweight): $7/month (1 core 2GB)

## 🔒 Security Considerations

### 1. Sensitive Information Management
```bash
# Use environment variables to store URI
export MONGODB_ATLAS_URI="mongodb+srv://..."

# Never hardcode passwords in code
```

### 2. Network Security
- MongoDB Atlas IP whitelist restriction
- HTTPS/TLS encrypted transmission
- Regular database password rotation

### 3. Data Isolation
- User preference data not uploaded to cloud
- Local SQLite encrypted storage

## 📈 Scalability

### Horizontal Scaling
- Cloud database supports auto-sharding
- Multiple backend instances can run locally
- Frontend load balancing through Nginx

### Vertical Scaling
- MongoDB Atlas upgradeable configuration
- Increase local computing resources

## 🎯 Future Optimization Directions

1. **CDN Acceleration**: Use CDN for game images and resources
2. **Redis Caching**: Add Redis as hot data cache layer
3. **Read/Write Separation**: Configure MongoDB Atlas Read Replica
4. **Monitoring & Alerting**: Add Prometheus + Grafana monitoring
5. **API Gateway**: Use Kong/APISIX for unified API management

---

**Ready to start migration?** I'll help you implement this architecture step by step!
