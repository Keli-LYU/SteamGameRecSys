# 混合云架构迁移指南

## 🎯 迁移目标

将现有架构从**本地全栈**迁移到**混合云架构**：
- ☁️ **云端**：MongoDB Atlas数据库 + 自动爬虫
- 💻 **本地**：推荐算法 + BERT情感分析 + 用户偏好存储

## 📋 迁移检查清单

### 第一步：准备MongoDB Atlas（15分钟）

- [ ] **1. 注册MongoDB Atlas账号**
  ```
  访问: https://www.mongodb.com/cloud/atlas
  点击: "Start Free" 或 "Try Free"
  使用: Google/GitHub账号或邮箱注册
  ```

- [ ] **2. 创建免费集群**
  ```
  Region: 选择最近的区域（如AWS Singapore）
  Tier: M0 Sandbox (FREE)
  Cluster Name: SteamGameRec
  ```

- [ ] **3. 创建数据库用户**
  ```
  Database Access > Add New Database User
  用户名: steamgamerec_user
  密码: [生成强密码并记录]
  权限: Atlas Admin 或 Read and write to any database
  ```

- [ ] **4. 配置网络访问**
  ```
  Network Access > Add IP Address
  开发环境: 0.0.0.0/0 (允许所有IP)
  生产环境: 添加具体IP白名单
  ```

- [ ] **5. 获取连接URI**
  ```
  Clusters > Connect > Drivers
  选择: Python / 3.11 or later
  复制: mongodb+srv://steamgamerec_user:<password>@...
  ```

### 第二步：迁移现有数据（可选，10分钟）

如果你已经有本地数据需要迁移：

```bash
# 1. 导出本地MongoDB数据
docker-compose exec mongodb mongodump --out=/tmp/dump --db=steamgamerec

# 2. 复制到本地
docker cp steamgamerec-mongodb:/tmp/dump ./mongodb_backup

# 3. 安装mongorestore工具（如果没有）
# Windows: https://www.mongodb.com/try/download/database-tools
# Linux/Mac: brew install mongodb-database-tools

# 4. 导入到MongoDB Atlas
mongorestore --uri="mongodb+srv://username:password@cluster.mongodb.net/" \
  --db=steamgamerec \
  ./mongodb_backup/steamgamerec
```

跳过此步骤，数据将在云端爬虫首次运行时自动填充。

### 第三步：配置本地环境（5分钟）

- [ ] **1. 创建.env文件**
  ```bash
  # 复制模板文件
  cp .env.example .env
  
  # 编辑.env文件
  # Windows: notepad .env
  # Linux/Mac: nano .env
  ```

- [ ] **2. 填写MongoDB Atlas连接信息**
  ```bash
  # 替换为你的实际连接URI
  MONGODB_ATLAS_URI=mongodb+srv://steamgamerec_user:YOUR_PASSWORD@cluster.mongodb.net/?retryWrites=true&w=majority
  DATABASE_NAME=steamgamerec
  ```

- [ ] **3. 验证配置**
  ```bash
  # 确保.env文件中没有<password>占位符
  # 确保密码正确
  cat .env  # Linux/Mac
  type .env  # Windows
  ```

### 第四步：启动混合云服务（5分钟）

- [ ] **1. 停止旧的本地服务**
  ```bash
  docker-compose down
  ```

- [ ] **2. 使用新配置启动**
  ```bash
  docker-compose -f docker-compose.hybrid.yml up --build
  ```

- [ ] **3. 检查服务状态**
  ```bash
  # 查看日志
  docker-compose -f docker-compose.hybrid.yml logs -f backend
  
  # 应该看到:
  # ✓ 数据库已连接: steamgamerec
  # ✅ SQLite数据库初始化完成
  ```

- [ ] **4. 测试API**
  ```bash
  # 访问 http://localhost:8000/docs
  # 应该能看到FastAPI文档页面
  ```

### 第五步：部署云端爬虫（10分钟）

- [ ] **1. 推送代码到GitHub**
  ```bash
  git add .
  git commit -m "Add hybrid cloud architecture"
  git push origin main
  ```

- [ ] **2. 配置GitHub Secrets**
  ```
  GitHub Repository > Settings > Secrets and variables > Actions
  点击: "New repository secret"
  
  Name: MONGODB_ATLAS_URI
  Value: mongodb+srv://steamgamerec_user:PASSWORD@cluster.mongodb.net/
  ```

- [ ] **3. 手动触发爬虫测试**
  ```
  GitHub Repository > Actions > Steam Data Crawler (Cloud)
  点击: "Run workflow"
  选择: Mode = quick (快速测试1000款游戏)
  ```

- [ ] **4. 查看执行结果**
  ```
  等待2-3分钟
  查看Actions日志，应该显示:
  ✅ 快速更新完成: 新增 XXX, 更新 XXX
  ```

### 第六步：验证完整流程（5分钟）

- [ ] **1. 检查云端数据**
  ```
  MongoDB Atlas > Browse Collections
  应该看到 steamgamerec > games 集合有数据
  ```

- [ ] **2. 测试推荐功能**
  ```
  访问: http://localhost:3000
  查看: "Recommended Games" 模块
  点击: 游戏卡片，检查本地偏好是否更新
  ```

- [ ] **3. 查看本地用户数据**
  ```bash
  # 进入后端容器
  docker-compose -f docker-compose.hybrid.yml exec backend bash
  
  # 查看SQLite数据库
  ls -lh /app/data/user_preferences.db
  
  # 退出
  exit
  ```

## 🔍 故障排查

### 问题1: 连接MongoDB Atlas失败

**症状**: `ServerSelectionTimeoutError` 或 `Authentication failed`

**解决方案**:
1. 检查.env文件中的URI是否正确
2. 确认密码中的特殊字符已URL编码
3. 检查Network Access白名单是否包含你的IP
4. 测试连接:
   ```bash
   docker-compose -f docker-compose.hybrid.yml exec backend python -c \
     "from motor.motor_asyncio import AsyncIOMotorClient; import os; \
      client = AsyncIOMotorClient(os.getenv('MONGODB_URL')); \
      print('连接成功!')"
   ```

### 问题2: GitHub Actions爬虫失败

**症状**: Actions运行失败，显示认证错误

**解决方案**:
1. 检查GitHub Secrets中的`MONGODB_ATLAS_URI`是否正确
2. 确认URI包含数据库用户名和密码
3. 测试本地运行爬虫:
   ```bash
   cd cloud_crawler
   pip install httpx motor beanie pydantic
   export MONGODB_URL="mongodb+srv://..."
   python crawler.py quick
   ```

### 问题3: 本地SQLite数据库不存在

**症状**: `FileNotFoundError: /app/data/user_preferences.db`

**解决方案**:
```bash
# 确保Volume挂载正确
docker-compose -f docker-compose.hybrid.yml down -v
docker-compose -f docker-compose.hybrid.yml up --build

# 手动初始化
docker-compose -f docker-compose.hybrid.yml exec backend python -c \
  "from app.local_storage import get_preference_store; get_preference_store()"
```

## 📊 监控与维护

### 日常监控

```bash
# 查看云端游戏数据量
# MongoDB Atlas Dashboard > Metrics

# 查看本地用户数据
docker-compose -f docker-compose.hybrid.yml exec backend python -c \
  "from app.local_storage import get_preference_store; \
   print(get_preference_store().get_stats())"

# 查看爬虫执行历史
# GitHub Repository > Actions > Steam Data Crawler
```

### 定期维护

1. **每周**: 检查GitHub Actions执行状态
2. **每月**: 清理过期缓存
   ```bash
   docker-compose -f docker-compose.hybrid.yml exec backend python -c \
     "from app.local_storage import get_preference_store; \
      get_preference_store().clear_expired_cache()"
   ```
3. **每季度**: 备份MongoDB Atlas数据

## 🎉 迁移完成！

完成以上步骤后，你的系统架构将变为：
- ✅ 云端MongoDB Atlas存储游戏数据
- ✅ GitHub Actions每天自动爬取更新
- ✅ 本地FastAPI提供推荐和分析服务
- ✅ 本地SQLite存储用户隐私数据

**下一步建议**:
1. 设置监控告警（MongoDB Atlas内置）
2. 配置完整爬虫定期全量更新
3. 添加Redis缓存层优化性能
4. 部署多个本地实例实现负载均衡

## 📞 获取帮助

遇到问题？检查以下资源：
- MongoDB Atlas文档: https://docs.atlas.mongodb.com/
- GitHub Actions文档: https://docs.github.com/actions
- 项目架构文档: `HYBRID_CLOUD_ARCHITECTURE.md`
