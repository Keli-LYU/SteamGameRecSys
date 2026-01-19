# 混合云架构设计文档

## 📋 架构概述

### 原架构
- **本地存储** + **云端计算**
- MongoDB运行在本地Docker容器
- 所有服务在本地运行

### 新架构（混合云）
- **云端数据库存储** - MongoDB Atlas（云托管）
- **云端自动爬虫** - 定时任务自动爬取Steam数据
- **本地计算** - 推荐系统、情感分析在本地处理
- **本地用户偏好** - 用户点击偏好数据存储在本地

## 🏗️ 架构组件

```
┌─────────────────────────────────────────────────────────────────┐
│                        云端 (Cloud)                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐    ┌──────────────────────────────┐   │
│  │  MongoDB Atlas      │◄───│  Cloud Crawler Service       │   │
│  │  (游戏数据库)       │    │  (定时爬取Steam数据)         │   │
│  │  - games集合        │    │  - Cron: 每天运行            │   │
│  │  - sentiment_logs   │    │  - 自动导入新游戏            │   │
│  └──────▲──────────────┘    └──────────────────────────────┘   │
│         │                                                        │
└─────────┼────────────────────────────────────────────────────────┘
          │ MongoDB连接 (云端URI)
          │
┌─────────┼────────────────────────────────────────────────────────┐
│         │                  本地 (Local)                          │
├─────────┼────────────────────────────────────────────────────────┤
│         │                                                         │
│  ┌──────▼──────────────┐    ┌──────────────────────────────┐   │
│  │  Backend Service    │    │  Local SQLite DB             │   │
│  │  (本地FastAPI)      │    │  (用户偏好存储)              │   │
│  │  - 推荐算法计算     │◄───│  - user_preferences表        │   │
│  │  - 情感分析(BERT)   │    │  - 用户点击历史              │   │
│  │  - 读取云端游戏数据 │    │  - 离线可用                  │   │
│  └──────▲──────────────┘    └──────────────────────────────┘   │
│         │                                                         │
│  ┌──────┴──────────────┐                                        │
│  │  Frontend (React)   │                                        │
│  │  - 用户界面         │                                        │
│  │  - 游戏浏览         │                                        │
│  │  - 推荐显示         │                                        │
│  └─────────────────────┘                                        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## 🔑 核心设计原则

### 1. 数据分离策略
- **游戏数据（云端）**: 游戏元数据、评论、价格等公共数据存储在MongoDB Atlas
- **用户数据（本地）**: 用户点击偏好、浏览历史等隐私数据存储在本地SQLite

### 2. 计算本地化
- **推荐算法**: 在本地计算，保护用户隐私
- **BERT情感分析**: 大模型在本地运行，无需上传数据到云端
- **数据缓存**: 本地缓存常用游戏数据，减少云端访问

### 3. 云端自动化
- **定时爬虫**: 云端cron任务每天自动更新Steam数据
- **数据同步**: 自动将新游戏、价格变动同步到MongoDB Atlas
- **无需本地干预**: 数据更新完全自动化

## 📂 数据库设计

### 云端MongoDB Atlas
```javascript
// games - 游戏基础数据（公共只读）
{
  app_id: 730,
  name: "Counter-Strike 2",
  price: 0,
  genres: ["Action", "FPS"],
  positive_reviews: 500000,
  negative_reviews: 20000,
  updated_at: "2026-01-19"
}

// sentiment_logs - 情感分析日志（可选，也可本地）
{
  review_text: "Great game!",
  sentiment: "POSITIVE",
  score: 0.98,
  timestamp: "2026-01-19T10:00:00Z"
}
```

### 本地SQLite
```sql
-- user_preferences - 用户偏好数据（隐私数据）
CREATE TABLE user_preferences (
    user_id TEXT PRIMARY KEY,
    genre_weights TEXT,  -- JSON: {"Action": 5, "RPG": 3}
    clicked_games TEXT,  -- JSON: [730, 440, 570]
    updated_at TIMESTAMP
);

-- user_cache - 本地游戏缓存
CREATE TABLE game_cache (
    app_id INTEGER PRIMARY KEY,
    game_data TEXT,  -- JSON完整游戏数据
    cached_at TIMESTAMP
);
```

## 🚀 部署方案

### 阶段一：云端MongoDB设置

1. **注册MongoDB Atlas**
   ```bash
   # 访问 https://www.mongodb.com/cloud/atlas
   # 创建免费M0集群（512MB存储）
   # 获取连接URI: mongodb+srv://username:password@cluster.mongodb.net/
   ```

2. **配置网络访问**
   - 添加本地IP到白名单
   - 或设置允许所有IP（0.0.0.0/0）用于开发

3. **创建数据库用户**
   - 用户名: steamgamerec_user
   - 密码: 强密码
   - 权限: readWrite on steamgamerec database

### 阶段二：云端爬虫部署

选择以下任一方案：

#### 方案A：GitHub Actions（免费）
```yaml
# .github/workflows/crawler.yml
name: Steam Data Crawler
on:
  schedule:
    - cron: '0 2 * * *'  # 每天凌晨2点UTC运行
  workflow_dispatch:  # 手动触发

jobs:
  crawl:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install httpx motor beanie
      - name: Run crawler
        env:
          MONGODB_URL: ${{ secrets.MONGODB_ATLAS_URI }}
        run: python cloud_crawler/crawler.py
```

#### 方案B：云函数（AWS Lambda / Azure Functions）
```python
# 定时触发Lambda函数
# 每天自动执行爬虫脚本
```

#### 方案C：轻量云服务器（阿里云/腾讯云）
```bash
# 最低配置: 1核1G
# Cron定时任务
0 2 * * * cd /app && python crawler.py
```

### 阶段三：本地服务修改

1. **更新docker-compose.yml** - 移除本地MongoDB
2. **添加SQLite支持** - 本地用户偏好存储
3. **修改环境变量** - 连接云端MongoDB Atlas
4. **更新模型** - 分离云端/本地数据模型

## 🔧 实施步骤

### Step 1: 准备MongoDB Atlas
- [ ] 注册MongoDB Atlas账号
- [ ] 创建免费集群
- [ ] 获取连接URI
- [ ] 配置IP白名单

### Step 2: 迁移现有数据
```bash
# 导出本地MongoDB数据
docker-compose exec mongodb mongodump --out=/tmp/dump

# 导入到MongoDB Atlas
mongorestore --uri="mongodb+srv://..." /tmp/dump
```

### Step 3: 更新本地服务
```bash
# 设置环境变量
export MONGODB_URL="mongodb+srv://username:password@cluster.mongodb.net/"

# 重启服务
docker-compose up --build
```

### Step 4: 部署云端爬虫
```bash
# 推送代码到GitHub
git add cloud_crawler/
git commit -m "Add cloud crawler"
git push

# 配置GitHub Secrets
# MONGODB_ATLAS_URI=mongodb+srv://...
```

## 📊 性能优化

### 1. 本地缓存策略
```python
# 缓存热门游戏到本地SQLite
# 减少云端数据库访问
cache_ttl = 3600  # 1小时缓存
```

### 2. 连接池配置
```python
# MongoDB连接池优化
client = AsyncIOMotorClient(
    MONGODB_URL,
    maxPoolSize=50,
    minPoolSize=10
)
```

### 3. 读写分离
- **读操作**: 优先读本地缓存，未命中再访问云端
- **写操作**: 用户偏好直接写本地，游戏数据只读云端

## 💰 成本估算

| 组件 | 服务 | 配置 | 月成本 |
|------|------|------|--------|
| 云端数据库 | MongoDB Atlas | M0 (512MB) | 免费 |
| 云端爬虫 | GitHub Actions | 2000分钟/月 | 免费 |
| 本地计算 | 自有硬件 | - | 电费 |
| **总计** | | | **~0元** |

升级方案（生产环境）：
- MongoDB Atlas M10: $57/月（2GB存储，专用资源）
- 云服务器（腾讯云轻量）: ¥50/月（1核2G）

## 🔒 安全考虑

### 1. 敏感信息管理
```bash
# 使用环境变量存储URI
export MONGODB_ATLAS_URI="mongodb+srv://..."

# 不要在代码中硬编码密码
```

### 2. 网络安全
- MongoDB Atlas白名单限制IP
- HTTPS/TLS加密传输
- 定期轮换数据库密码

### 3. 数据隔离
- 用户偏好数据不上传云端
- 本地SQLite加密存储

## 📈 扩展性

### 横向扩展
- 云端数据库支持自动分片
- 本地可启动多个backend实例
- 前端通过Nginx负载均衡

### 垂直扩展
- MongoDB Atlas可升级配置
- 本地增加计算资源

## 🎯 后续优化方向

1. **CDN加速**: 游戏图片、资源使用CDN分发
2. **Redis缓存**: 添加Redis作为热数据缓存层
3. **读写分离**: MongoDB Atlas配置Read Replica
4. **监控告警**: 添加Prometheus + Grafana监控
5. **API网关**: 使用Kong/APISIX统一API管理

---

**准备好开始迁移了吗？** 我将按步骤帮你实施这个架构！
