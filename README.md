# SteamGameRecSys

**Steam游戏推荐与智能分析系统** - 集成BERT情感分析的全栈AI应用

![Architecture](https://img.shields.io/badge/Architecture-Hybrid%20Cloud-blue)
![Backend](https://img.shields.io/badge/Backend-FastAPI%20%2B%20BERT-green)
![Frontend](https://img.shields.io/badge/Frontend-React-61DAFB)
![Database](https://img.shields.io/badge/Database-MongoDB-47A248)
![K8s](https://img.shields.io/badge/Orchestration-Kubernetes-326CE5)

## 📋 项目概述

SteamGameRecSys是一个高级全栈项目,包含两个核心业务板块:

1. **🎮 游戏数据与推荐**: 从Steam获取数据,展示并推荐游戏
2. **🧠 NLP情感分析实验室**: 集成BERT模型,提供文本情感分析服务并记录历史

## 🏗️ 系统架构

### 混合云部署架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Hybrid Cloud Architecture               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────────┐         ┌──────────────────────┐   │
│  │   AWS EKS Cloud    │◄────────┤  Local Minikube      │   │
│  │                    │  VPN/   │                      │   │
│  │  ┌──────────────┐  │ Tunnel  │  ┌────────────────┐ │   │
│  │  │   Frontend   │  │         │  │   MongoDB      │ │   │
│  │  │   (React)    │  │         │  │  StatefulSet   │ │   │
│  │  │  Deployment  │  │         │  │                │ │   │
│  │  └──────┬───────┘  │         │  │  PVC: 10Gi     │ │   │
│  │         │          │         │  └────────────────┘ │   │
│  │  ┌──────▼───────┐  │         │                      │   │
│  │  │   Backend    │  │         └──────────┬───────────┘   │
│  │  │  (FastAPI +  │  │                    │               │
│  │  │    BERT)     │──┼────────────────────┘               │
│  │  │  Deployment  │  │    MongoDB Connection              │
│  │  └──────────────┘  │    (NodePort 30017)                │
│  │                    │                                     │
│  │  Resources:        │                                     │
│  │  - Memory: 2GB     │                                     │
│  │  - CPU: 1 core     │                                     │
│  │  - HPA: 2-5 pods   │                                     │
│  └────────────────────┘                                     │
└─────────────────────────────────────────────────────────────┘
```

### 技术栈

#### Frontend (前端)
- **React 18**: 单页应用框架
- **React Router**: 客户端路由
- **Axios**: HTTP客户端
- **Modern CSS**: 渐变、动画、响应式设计

#### Backend (后端)
- **FastAPI**: 高性能Python Web框架
- **BERT模型**: `distilbert-base-uncased-finetuned-sst-2-english`
  - 参数量: 66M (轻量级)
  - 模型大小: ~250MB
  - 任务: 情感二分类 (Positive/Negative)
- **HuggingFace Transformers**: NLP模型库
- **PyTorch**: 深度学习框架 (CPU版本)
- **SteamSpy API**: Steam数据获取

#### Database (数据库)
- **MongoDB 7.0**: NoSQL文档数据库
- **Beanie**: 异步ODM (Object Document Mapper)
- **Collections**:
  - `games`: 游戏元数据
  - `users`: 用户行为日志
  - `sentiment_logs`: NLP分析历史

#### Infrastructure (基础设施)
- **Kubernetes**: 容器编排
  - 本地: Minikube (MongoDB StatefulSet)
  - 云端: AWS EKS (Frontend + Backend Deployments)
- **Docker**: 容器化
- **Docker Compose**: 本地开发环境

## 📁 项目结构

```
SteamGameRecSys/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI入口
│   │   ├── models.py            # Beanie数据模型
│   │   ├── nlp_service.py       # BERT情感分析服务
│   │   ├── steam_service.py     # Steam API封装
│   │   └── database.py          # MongoDB连接
│   ├── requirements.txt         # Python依赖
│   ├── Dockerfile               # 后端镜像 (~1.5GB)
│   └── .env.example             # 环境变量示例
├── frontend/
│   ├── src/
│   │   ├── App.js               # 主应用
│   │   ├── components/
│   │   │   ├── GameExplorer.jsx # 游戏浏览界面
│   │   │   └── SentimentPage.jsx# NLP分析界面
│   │   └── styles/              # CSS样式
│   ├── package.json
│   └── Dockerfile               # 前端镜像
├── k8s/
│   ├── mongodb.yaml             # MongoDB StatefulSet
│   ├── backend.yaml             # Backend Deployment + HPA
│   └── frontend.yaml            # Frontend Deployment
├── docker-compose.yml           # 本地开发配置
└── README.md                    # 本文档
```

## 🚀 快速开始

### 方式1: Docker Compose (本地开发)

```bash
# 1. 克隆仓库
cd d:/ESIEE/E4/OpsDev/Projet/SteamGameRecSys

# 2. 启动所有服务
docker-compose up --build

# 3. 访问应用
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# MongoDB: localhost:27017
```

### 方式2: Kubernetes (混合云部署)

#### Step 1: 部署MongoDB到Minikube

```bash
# 启动Minikube
minikube start --memory=4096 --cpus=2

# 部署MongoDB StatefulSet
kubectl apply -f k8s/mongodb.yaml

# 验证部署
kubectl get statefulset mongodb
kubectl get pvc  # 检查持久化卷

# 获取Minikube IP (用于混合云连接)
minikube ip
# 示例输出: 192.168.49.2
```

#### Step 2: 配置Backend连接MongoDB

编辑 `k8s/backend.yaml` 中的ConfigMap:

```yaml
data:
  MONGODB_URL: "mongodb://192.168.49.2:30017"  # 替换为实际Minikube IP
```

#### Step 3: 部署Backend和Frontend到AWS EKS

```bash
# 切换到AWS EKS context
kubectl config use-context <your-eks-context>

# 构建并推送镜像到镜像仓库
docker build -t <your-registry>/steamgamerec-backend:latest ./backend
docker push <your-registry>/steamgamerec-backend:latest

docker build -t <your-registry>/steamgamerec-frontend:latest ./frontend
docker push <your-registry>/steamgamerec-frontend:latest

# 更新deployment镜像地址
# 编辑 k8s/backend.yaml 和 k8s/frontend.yaml 中的 image 字段

# 部署到EKS
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/frontend.yaml

# 查看服务状态
kubectl get pods
kubectl get svc

# 获取Frontend LoadBalancer地址
kubectl get svc frontend-service
```

## 📊 MongoDB数据模型

### Games Collection

```javascript
{
  "_id": ObjectId("..."),
  "app_id": 730,  // Steam App ID
  "name": "Counter-Strike 2",
  "price": 0.0,
  "genres": ["Action", "FPS"],
  "description": "...",
  "release_date": "2023-09-27",
  "positive_reviews": 500000,
  "negative_reviews": 50000,
  "created_at": ISODate("...")
}
```

### SentimentLogs Collection

```javascript
{
  "_id": ObjectId("..."),
  "text": "This game is absolutely amazing!",
  "label": "POSITIVE",  // POSITIVE or NEGATIVE
  "confidence": 0.9987,  // 0.0-1.0
  "related_game_id": 730,  // 可选
  "created_at": ISODate("...")
}
```

## 🔌 API文档

### 游戏管理

- `GET /games?skip=0&limit=20` - 获取游戏列表
- `POST /games` - 添加游戏
- `GET /games/{id}` - 获取游戏详情

### Steam代理

- `GET /steam/{app_id}` - 获取Steam游戏数据
- `GET /steam/top/games?limit=20` - 获取热门游戏

### NLP情感分析

- `POST /analyze` - 分析文本情感
  ```json
  {
    "text": "This game is great!",
    "related_game_id": 730  // 可选
  }
  ```
  
- `GET /history?skip=0&limit=50` - 获取分析历史

完整API文档: http://localhost:8000/docs (Swagger UI)

## 🧠 NLP模型详情

### BERT模型配置

- **模型**: `distilbert-base-uncased-finetuned-sst-2-english`
- **训练数据**: Stanford Sentiment Treebank (SST-2)
- **输出**: 二分类 (POSITIVE/NEGATIVE)
- **推理设备**: CPU
- **内存占用**: ~500MB (推理时)
- **首次加载**: 5-10秒

### 资源管理

```yaml
# Backend Pod资源配置
resources:
  requests:
    memory: "1536Mi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "1000m"
```

### 模型优化

1. **单例模式**: 全局仅加载一次模型
2. **模型预热**: 应用启动时执行测试推理
3. **预下载**: Docker镜像构建时下载模型
4. **文本截断**: 限制输入512 tokens

## 🧪 测试

### 测试Backend API

```bash
# 健康检查
curl http://localhost:8000/

# 测试情感分析
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "This game is absolutely phenomenal!"}'

# 获取分析历史
curl http://localhost:8000/history
```

### 测试Frontend

1. 访问 http://localhost:3000
2. 点击侧边栏 "Sentiment Analysis"
3. 输入文本并提交分析
4. 查看结果和历史记录

## 📈 性能优化

### Docker镜像优化

- **Backend**: 使用PyTorch CPU版本,减少2GB体积
- **Frontend**: 多阶段构建,最终镜像仅包含Nginx + 静态文件

### Kubernetes优化

- **HPA**: 自动扩缩容 (Backend: 2-5 pods, Frontend: 3-10 pods)
- **资源限制**: 防止单个Pod占用过多资源
- **健康检查**: 延迟探针考虑BERT加载时间

## 🔒 安全考虑

1. **CORS配置**: 生产环境限制允许的域名
2. **环境变量**: 敏感信息存储在ConfigMap/Secret
3. **MongoDB认证**: 生产环境启用认证
4. **网络策略**: 限制Pod间通信

## 🐛 故障排查

### Backend Pod OOMKilled

```bash
# 检查资源使用
kubectl top pod <backend-pod-name>

# 增加内存限制
# 编辑 k8s/backend.yaml 增加 resources.limits.memory
```

### BERT模型加载失败

```bash
# 查看日志
kubectl logs <backend-pod-name>

# 可能原因:
# 1. 内存不足 -> 增加资源限制
# 2. 网络问题 -> 检查HuggingFace Hub连接
# 3. 镜像问题 -> 重新构建Docker镜像
```

### MongoDB连接失败 (混合云)

```bash
# 测试从AWS Pod连接到Minikube MongoDB
kubectl exec -it <backend-pod> -- curl minikube-ip:30017

# 可能需要配置:
# - VPN tunnel
# - 防火墙规则
# - Security Groups
```

## 📚 扩展功能建议

1. **用户认证**: 添加JWT认证
2. **游戏推荐**: 基于用户历史的协同过滤
3. **评论抓取**: 自动拉取Steam评论并分析
4. **多语言支持**: 支持中文情感分析
5. **GPU加速**: 在K8s中配置NVIDIA GPU支持

## 👥 贡献

开发者: 全栈工程师 & AI系统专家

## 📄 许可证

MIT License

---

**Built with ❤️ using FastAPI, React, BERT, and Kubernetes**
