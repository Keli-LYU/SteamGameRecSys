"""
FastAPI Application Entry Point
FastAPI主应用 - SteamGameRecSys后端服务器

API端点:
- GET  /              - 健康检查
- GET  /games         - 获取游戏列表
- POST /games         - 添加游戏
- GET  /games/{id}    - 获取单个游戏详情
- GET  /steam/{app_id}- 从Steam获取游戏数据
- POST /analyze       - NLP情感分析
- GET  /history       - 获取分析历史
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List, Optional
from datetime import datetime

from app.database import init_db, close_db
from app.models import Game, SentimentLog, SentimentRequest, SentimentResponse, UserPreference
from app.nlp_service import predict_sentiment, warmup_model
from app.steam_service import steam_service
from app.local_storage import get_preference_store

import logging
import random

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================
# 应用生命周期管理
# ============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用启动和关闭时的钩子函数
    - startup: 初始化数据库连接,预热NLP模型
    - shutdown: 关闭数据库连接
    """
    # Startup
    logger.info("Starting SteamGameRecSys Backend...")
    await init_db()
    warmup_model()  # 预热BERT模型
    logger.info("Application ready!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await close_db()
    await steam_service.close()
    logger.info("Goodbye!")


# ============================================
# FastAPI应用实例
# ============================================
app = FastAPI(
    title="SteamGameRecSys API",
    description="Steam游戏推荐与智能分析系统 - 后端API",
    version="1.0.0",
    lifespan=lifespan
)


# ============================================
# CORS中间件配置 (允许React前端跨域访问)
# ============================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# API路由 - 健康检查
# ============================================
@app.get("/")
async def root():
    """根路径 - 健康检查"""
    return {
        "status": "healthy",
        "service": "SteamGameRecSys Backend",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# API路由 - 游戏数据管理
# ============================================
@app.get("/games", response_model=List[Game])
async def get_games(skip: int = 0, limit: int = 20):
    """
    获取游戏列表 (支持分页)
    
    Query参数:
    - skip: 跳过的记录数 (默认0)
    - limit: 返回的最大记录数 (默认20)
    """
    try:
        games = await Game.find_all().skip(skip).limit(limit).to_list()
        return games
    except Exception as e:
        logger.error(f"Failed to fetch games: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/games", response_model=Game)
async def create_game(game: Game):
    """
    添加新游戏到数据库
    
    Body: Game对象 (JSON)
    """
    try:
        await game.insert()
        return game
    except Exception as e:
        logger.error(f"Failed to create game: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/games/{game_id}", response_model=Game)
async def get_game(game_id: str):
    """
    获取单个游戏详情 (通过MongoDB ObjectId)
    """
    try:
        game = await Game.get(game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        return game
    except Exception as e:
        logger.error(f"Failed to fetch game {game_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/games/{game_id}")
async def delete_game(game_id: str):
    """
    删除游戏 (通过MongoDB ObjectId)
    """
    try:
        game = await Game.get(game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        await game.delete()
        return {"message": "Game deleted successfully", "game_id": game_id}
    except Exception as e:
        logger.error(f"Failed to delete game {game_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# API路由 - Steam数据代理
# ============================================
@app.get("/steam/{app_id}")
async def get_steam_game(app_id: int):
    """
    从Steam获取游戏数据 (通过SteamSpy API)
    
    Path参数:
    - app_id: Steam App ID
    
    返回: 游戏详细信息 (不存储到数据库)
    """
    try:
        game_data = await steam_service.get_game_details(app_id)
        
        if not game_data:
            raise HTTPException(status_code=404, detail=f"Game {app_id} not found on Steam")
        
        return game_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Steam API error: {e}")
        raise HTTPException(status_code=500, detail="Steam API request failed")


@app.get("/steam/top/games")
async def get_top_steam_games(limit: int = 20):
    """
    获取Steam热门游戏列表
    
    Query参数:
    - limit: 返回数量 (默认20)
    """
    try:
        games = await steam_service.get_top_games(limit)
        return games
    except Exception as e:
        logger.error(f"Failed to fetch top games: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# API路由 - 游戏推荐系统
# ============================================
@app.get("/recommendations")
async def get_recommendations(user_id: str = "default_user", limit: int = 10):
    """
    获取个性化推荐游戏（基于本地SQLite存储的用户偏好）
    
    Query参数:
    - user_id: 用户ID (默认: default_user)
    - limit: 返回数量 (默认: 10)
    
    推荐逻辑:
    1. 从本地SQLite获取用户偏好权重
    2. 从云端MongoDB获取所有游戏
    3. 计算匹配分数并返回得分最高的游戏
    """
    try:
        # 使用本地SQLite获取用户偏好
        store = get_preference_store()
        prefs = store.get_user_preference(user_id)
        
        # 获取所有游戏（从云端MongoDB）
        all_games = await Game.find_all().to_list()
        
        if not all_games:
            # 如果数据库中没有游戏，从Steam获取热门游戏
            return await steam_service.get_top_games(limit)
        
        # 如果没有偏好或偏好为空，随机返回
        if not prefs or not prefs.get("genre_weights"):
            random.shuffle(all_games)
            return all_games[:limit]
        
        genre_weights = prefs["genre_weights"]
        
        # 根据偏好权重计算每个游戏的得分
        scored_games = []
        for game in all_games:
            score = 0
            for genre in game.genres:
                score += genre_weights.get(genre, 0)
            
            scored_games.append({
                "_id": str(game.id),
                "app_id": game.app_id,
                "name": game.name,
                "price": game.price,
                "genres": game.genres,
                "description": game.description,
                "positive_reviews": game.positive_reviews,
                "negative_reviews": game.negative_reviews,
                "score": score
            })
        
        # 按得分排序（降序）
        scored_games.sort(key=lambda x: x["score"], reverse=True)
        
        # 移除score字段并返回
        recommended = []
        for game in scored_games[:limit]:
            game.pop("score")
            recommended.append(game)
        
        return recommended
        
    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/preferences/click")
async def record_game_click(app_id: int, user_id: str = "default_user"):
    """
    记录用户点击游戏的行为，更新偏好权重（使用本地SQLite存储）
    
    Body: {
        "app_id": 游戏App ID,
        "user_id": 用户ID (可选)
    }
    """
    try:
        # 获取游戏信息（从云端MongoDB）
        game = await Game.find_one(Game.app_id == app_id)
        if not game:
            # 如果数据库中没有，从Steam获取
            game_data = await steam_service.get_game_details(app_id)
            if not game_data:
                raise HTTPException(status_code=404, detail="Game not found")
            genres = game_data.get("genres", [])
        else:
            genres = game.genres
        
        # 使用本地SQLite存储用户偏好
        store = get_preference_store()
        
        # 获取现有偏好
        prefs = store.get_user_preference(user_id)
        if prefs is None:
            prefs = {"genre_weights": {}, "clicked_games": []}
        
        # 更新类型权重（每次点击增加1）
        for genre in genres:
            prefs["genre_weights"][genre] = prefs["genre_weights"].get(genre, 0) + 1
        
        # 添加点击的游戏
        if app_id not in prefs["clicked_games"]:
            prefs["clicked_games"].append(app_id)
        
        # 保存到本地SQLite
        store.save_user_preference(user_id, prefs["genre_weights"], prefs["clicked_games"])
        
        return {
            "message": "Preference updated (local storage)",
            "genre_weights": prefs["genre_weights"],
            "storage": "local_sqlite"
        }
        
    except Exception as e:
        logger.error(f"Failed to record click: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# API路由 - NLP情感分析
# ============================================
@app.post("/analyze", response_model=SentimentResponse)
async def analyze_sentiment(request: SentimentRequest):
    """
    NLP情感分析端点
    
    Body: {
        "text": "待分析的文本",
        "related_game_id": 123 (可选)
    }
    
    返回: {
        "label": "POSITIVE" or "NEGATIVE",
        "confidence": 0.95,
        "text": "原始文本",
        "timestamp": "2024-..."
    }
    
    流程:
    1. 调用BERT模型进行情感推理
    2. 存储分析结果到MongoDB (sentiment_logs集合)
    3. 返回分析结果给前端
    """
    try:
        # Step 1: 调用NLP服务进行情感分析
        result = predict_sentiment(request.text)
        
        # Step 2: 存储到数据库
        log = SentimentLog(
            text=request.text,
            label=result["label"],
            confidence=result["confidence"],
            related_game_id=request.related_game_id
        )
        await log.insert()
        
        # Step 3: 返回响应
        return SentimentResponse(
            label=result["label"],
            confidence=result["confidence"],
            text=request.text,
            timestamp=log.created_at
        )
        
    except Exception as e:
        logger.error(f"Sentiment analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/history", response_model=List[SentimentLog])
async def get_sentiment_history(skip: int = 0, limit: int = 50):
    """
    获取情感分析历史记录 (按时间倒序)
    
    Query参数:
    - skip: 跳过记录数
    - limit: 返回数量 (默认50)
    
    返回: SentimentLog列表
    """
    try:
        logs = await SentimentLog.find_all()\
            .sort(-SentimentLog.created_at)\
            .skip(skip)\
            .limit(limit)\
            .to_list()
        
        return logs
        
    except Exception as e:
        logger.error(f"Failed to fetch history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 开发环境运行
# ============================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # 开发模式启用热重载
    )
