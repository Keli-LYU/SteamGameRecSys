"""
MongoDB Database Configuration and Initialization
数据库配置模块 - 负责初始化MongoDB连接和Beanie ODM
"""
import os
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.models import Game, User, SentimentLog, UserPreference

# MongoDB连接配置
# 生产环境: 从环境变量读取MongoDB URI (支持混合云连接)
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "steamgamerec")


async def init_db():
    """
    初始化数据库连接
    - 创建异步MongoDB客户端
    - 初始化Beanie ODM并注册所有Document模型
    - 在Kubernetes中,此函数在应用启动时调用
    """
    # 创建MongoDB异步客户端
    client = AsyncIOMotorClient(MONGODB_URL)
    
    # 初始化Beanie - 注册所有Document模型
    await init_beanie(
        database=client[DATABASE_NAME],
        document_models=[Game, User, SentimentLog, UserPreference]
    )
    
    print(f"Database initialized: {DATABASE_NAME}")
    print(f"Registered models: Game, User, SentimentLog, UserPreference")


async def close_db():
    """
    关闭数据库连接
    - 优雅关闭时调用
    """
    # Beanie会自动处理连接池关闭
    print("🔒 Database connection closed")
