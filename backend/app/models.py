"""
Beanie Document Models (MongoDB ODM)
数据模型定义 - 使用Beanie ODM定义MongoDB集合的Schema
包含三个核心模型: Game, User, SentimentLog
"""
from datetime import datetime
from typing import Optional, List
from beanie import Document
from pydantic import BaseModel, Field


# ============================================
# Game Model - 游戏数据模型
# ============================================
class Game(Document):
    """
    Steam游戏数据模型
    对应MongoDB中的 'games' 集合
    """
    app_id: int = Field(..., description="Steam App ID")
    name: str = Field(..., description="游戏名称")
    price: Optional[float] = Field(None, description="价格 (USD)")
    genres: List[str] = Field(default_factory=list, description="游戏类型")
    description: Optional[str] = Field(None, description="游戏描述")
    release_date: Optional[str] = Field(None, description="发布日期")
    positive_reviews: Optional[int] = Field(None, description="正面评价数")
    negative_reviews: Optional[int] = Field(None, description="负面评价数")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "games"  # MongoDB集合名称


# ============================================
# User Model - 用户行为日志模型
# ============================================
class User(Document):
    """
    用户行为日志模型
    对应MongoDB中的 'users' 集合
    """
    user_id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    favorite_games: List[int] = Field(default_factory=list, description="收藏的游戏App ID列表")
    play_history: List[int] = Field(default_factory=list, description="游玩历史")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "users"


# ============================================
# UserPreference Model - 用户偏好模型
# ============================================
class UserPreference(Document):
    """
    用户游戏偏好模型
    对应MongoDB中的 'user_preferences' 集合
    
    存储用户对游戏类型的偏好权重
    """
    user_id: str = Field(default="default_user", description="用户ID")
    genre_weights: dict = Field(default_factory=dict, description="类型权重字典 {genre: weight}")
    clicked_games: List[int] = Field(default_factory=list, description="点击过的游戏App ID列表")
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "user_preferences"


# ============================================
# SentimentLog Model - NLP情感分析日志模型
# ============================================
class SentimentLog(Document):
    """
    情感分析历史记录模型
    对应MongoDB中的 'sentiment_logs' 集合
    
    存储BERT模型的分析结果:
    - 输入文本
    - 情感标签 (POSITIVE/NEGATIVE/NEUTRAL)
    - 置信度分数
    - 时间戳
    
    注意: 此模型替代原计划中的PostgreSQL存储方案,保持架构统一性
    """
    text: str = Field(..., description="待分析的文本")
    label: str = Field(..., description="情感标签: POSITIVE, NEGATIVE, NEUTRAL")
    confidence: float = Field(..., description="模型置信度 (0-1)", ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 可选字段: 如果文本来自Steam评论,可关联游戏ID
    related_game_id: Optional[int] = Field(None, description="关联的游戏App ID (可选)")
    
    class Settings:
        name = "sentiment_logs"


# ============================================
# Pydantic Request/Response Models
# ============================================
class SentimentRequest(BaseModel):
    """情感分析请求模型"""
    text: str = Field(..., min_length=1, max_length=5000, description="待分析的文本(1-5000字符)")
    related_game_id: Optional[int] = Field(None, description="可选: 关联的游戏ID")


class SentimentResponse(BaseModel):
    """情感分析响应模型"""
    label: str = Field(..., description="情感标签")
    confidence: float = Field(..., description="置信度")
    text: str = Field(..., description="原始文本")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="分析时间")
