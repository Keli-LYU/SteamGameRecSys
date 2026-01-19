# 混合云架构快速参考

## 🏗️ 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                          ☁️ 云端                                 │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  MongoDB Atlas (免费512MB)                              │    │
│  │  ┌──────────────┬──────────────┬────────────────┐     │    │
│  │  │ games集合    │sentiment_logs│ (用户数据移除)  │     │    │
│  │  │ ~100k游戏    │ 分析历史     │                 │     │    │
│  │  └──────────────┴──────────────┴────────────────┘     │    │
│  └──────────────────▲──────────────────────────────────────┘    │
│                     │                                            │
│  ┌──────────────────┴────────────────────────────────┐          │
│  │  GitHub Actions (定时爬虫)                         │          │
│  │  ⏰ Cron: 0 2 * * * (每天UTC 2:00)                │          │
│  │  📥 快速模式: 更新Top 1000游戏 (~5分钟)           │          │
│  │  📥 完整模式: 遍历所有游戏 (~8小时)               │          │
│  └────────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ MongoDB连接 (TLS加密)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                          💻 本地                                 │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Backend Service (FastAPI + Docker)                     │    │
│  │  ┌────────────────┬──────────────┬──────────────┐     │    │
│  │  │ 推荐引擎       │ BERT情感分析 │ Steam API     │     │    │
│  │  │ (本地计算)     │ (本地AI模型) │ (实时查询)    │     │    │
│  │  └────────────────┴──────────────┴──────────────┘     │    │
│  │  ● 读取云端游戏数据                                    │    │
│  │  ● 计算个性化推荐                                      │    │
│  │  ● 运行BERT模型 (~1.5GB内存)                          │    │
│  └──────────────────▲─────────────────────────────────────┘    │
│                     │                                            │
│  ┌──────────────────┴────────────────────────────────┐          │
│  │  SQLite Database (本地文件)                        │          │
│  │  📁 /app/data/user_preferences.db                 │          │
│  │  ┌─────────────────────────────────────────┐     │          │
│  │  │ user_preferences表                       │     │          │
│  │  │ - genre_weights (类型权重)              │     │          │
│  │  │ - clicked_games (点击历史)              │     │          │
│  │  │                                          │     │          │
│  │  │ game_cache表                             │     │          │
│  │  │ - 本地游戏缓存 (24小时TTL)              │     │          │
│  │  └─────────────────────────────────────────┘     │          │
│  │  ✅ 隐私数据不离开本地                             │          │
│  └────────────────────────────────────────────────────┘          │
│                     ▲                                            │
│  ┌──────────────────┴────────────────────────────────┐          │
│  │  Frontend (React + Nginx)                          │          │
│  │  🌐 http://localhost:3000                         │          │
│  │  ● 游戏浏览                                        │          │
│  │  ● 个性化推荐                                      │          │
│  │  ● 情感分析                                        │          │
│  └────────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

## 📊 数据流

### 1. 游戏数据更新流程
```
Steam API
   ↓
云端爬虫 (GitHub Actions)
   ↓
MongoDB Atlas
   ↓
本地Backend API
   ↓
Frontend显示
```

### 2. 用户交互流程
```
用户点击游戏
   ↓
Frontend发送请求
   ↓
Backend API
   ├─→ 从MongoDB Atlas读取游戏信息
   └─→ 保存用户偏好到本地SQLite
```

### 3. 推荐生成流程
```
Frontend请求推荐
   ↓
Backend API
   ├─→ 从本地SQLite读取用户偏好
   ├─→ 从MongoDB Atlas读取所有游戏
   ├─→ 本地计算匹配分数
   └─→ 返回Top N推荐
```

## 🎯 关键配置

### 环境变量 (.env)
```bash
# 云端MongoDB连接
MONGODB_ATLAS_URI=mongodb+srv://user:pass@cluster.mongodb.net/

# 数据库名称
DATABASE_NAME=steamgamerec

# 本地SQLite路径
USER_PREFS_DB=/app/data/user_preferences.db
```

### Docker Compose
```bash
# 启动混合云架构
docker-compose -f docker-compose.hybrid.yml up --build

# 查看日志
docker-compose -f docker-compose.hybrid.yml logs -f backend

# 停止服务
docker-compose -f docker-compose.hybrid.yml down
```

### GitHub Actions Secret
```
Name: MONGODB_ATLAS_URI
Value: mongodb+srv://steamgamerec_user:PASSWORD@cluster.mongodb.net/
```

## ⚡ 常用命令

### 本地开发
```bash
# 1. 启动服务
docker-compose -f docker-compose.hybrid.yml up -d

# 2. 查看后端日志
docker-compose -f docker-compose.hybrid.yml logs -f backend

# 3. 进入后端容器
docker-compose -f docker-compose.hybrid.yml exec backend bash

# 4. 查看SQLite数据
docker-compose -f docker-compose.hybrid.yml exec backend python -c \
  "from app.local_storage import get_preference_store; \
   print(get_preference_store().get_stats())"

# 5. 清理过期缓存
docker-compose -f docker-compose.hybrid.yml exec backend python -c \
  "from app.local_storage import get_preference_store; \
   get_preference_store().clear_expired_cache()"
```

### 云端爬虫
```bash
# 1. 本地测试爬虫
cd cloud_crawler
pip install httpx motor beanie pydantic
export MONGODB_URL="mongodb+srv://..."
python crawler.py quick

# 2. 完整模式
python crawler.py full

# 3. GitHub Actions手动触发
# Repository > Actions > Steam Data Crawler > Run workflow
```

### API测试
```bash
# 健康检查
curl http://localhost:8000/

# 获取游戏列表
curl http://localhost:8000/games?limit=10

# 获取推荐（本地偏好）
curl http://localhost:8000/recommendations?user_id=test_user&limit=5

# 记录点击（保存到本地）
curl -X POST "http://localhost:8000/preferences/click?app_id=730&user_id=test_user"

# 情感分析
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "This game is amazing!"}'
```

## 🔧 故障排查

### 问题: 无法连接MongoDB Atlas
```bash
# 检查环境变量
docker-compose -f docker-compose.hybrid.yml exec backend env | grep MONGODB

# 测试连接
docker-compose -f docker-compose.hybrid.yml exec backend python -c \
  "from motor.motor_asyncio import AsyncIOMotorClient; \
   import os; \
   client = AsyncIOMotorClient(os.getenv('MONGODB_URL')); \
   print('连接成功!')"
```

### 问题: SQLite数据库不存在
```bash
# 手动初始化
docker-compose -f docker-compose.hybrid.yml exec backend python -c \
  "from app.local_storage import get_preference_store; \
   get_preference_store()"
```

### 问题: GitHub Actions失败
```bash
# 检查Secrets配置
# Settings > Secrets > Actions > MONGODB_ATLAS_URI

# 查看Actions日志
# Repository > Actions > [失败的workflow] > 查看详情
```

## 📈 性能指标

| 指标 | 本地全栈 | 混合云 |
|------|---------|--------|
| 推荐延迟 | 50-100ms | 50-100ms (相同) |
| 用户隐私 | ❌ 存储在本地DB | ✅ 完全本地 |
| 数据更新 | 手动运行脚本 | 自动每日更新 |
| 数据库成本 | 本地硬盘 | 免费 (512MB) |
| 扩展性 | 单机限制 | 云端可扩展 |
| 备份 | 手动 | 自动 |

## 💰 成本对比

### 开发/测试环境（推荐）
- MongoDB Atlas M0: **免费**
- GitHub Actions: **免费** (2000分钟/月)
- 本地计算: 仅电费
- **总成本: ~0元/月**

### 生产环境（可选升级）
- MongoDB Atlas M10: **$57/月** (2GB, 专用资源)
- GitHub Actions: **免费** (足够)
- 云服务器: **¥50/月** (腾讯云轻量 1核2G)
- **总成本: ~¥450/月**

## 🎉 验证清单

- [ ] MongoDB Atlas连接成功
- [ ] 本地SQLite数据库创建
- [ ] GitHub Actions配置完成
- [ ] API `/` 返回健康状态
- [ ] API `/games` 返回游戏列表
- [ ] API `/recommendations` 返回推荐
- [ ] 点击游戏后偏好保存到本地
- [ ] Frontend正常显示

---

**快速帮助**: 完整文档见 `HYBRID_CLOUD_ARCHITECTURE.md` 和 `MIGRATION_GUIDE.md`
