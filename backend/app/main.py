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
from app.models import Game, SentimentLog, SentimentRequest, SentimentResponse, UserPreference, User
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
# 辅助函数
# ============================================
def normalize_genres(genres):
    """
    规范化genres格式，确保返回正确的字符串数组
    
    处理以下情况:
    - genres是字符串: "Action, Adventure" -> ["Action", "Adventure"]
    - genres是包含单个逗号分隔字符串的数组: ["Action, Adventure"] -> ["Action", "Adventure"]
    - genres已经是正确的数组: ["Action", "Adventure"] -> ["Action", "Adventure"]
    """
    if not genres:
        return []
    
    # 如果是字符串，直接分割
    if isinstance(genres, str):
        return [g.strip() for g in genres.split(", ")] if genres else []
    
    # 如果是数组
    if isinstance(genres, list):
        # 检查是否是单个元素且包含逗号（需要分割的情况）
        if len(genres) == 1 and isinstance(genres[0], str) and ", " in genres[0]:
            return [g.strip() for g in genres[0].split(", ")]
        # 已经是正确的数组格式
        return genres
    
    return []


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
@app.get("/games")
async def get_games(skip: int = 0, limit: int = 20):
    """
    获取游戏列表 (支持分页)
    
    Query参数:
    - skip: 跳过的记录数 (默认0)
    - limit: 返回的最大记录数 (默认20)
    """
    try:
        games = await Game.find_all().skip(skip).limit(limit).to_list()
        # 规范化genres格式并添加_id字段
        result = []
        for game in games:
            game_dict = game.dict()
            game_dict["genres"] = normalize_genres(game.genres)
            # 确保_id字段存在（前端需要）
            game_dict["_id"] = str(game.id)
            result.append(game_dict)
        return result
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
        from bson import ObjectId
        from bson.errors import InvalidId
        
        # 验证ObjectId格式
        try:
            obj_id = ObjectId(game_id)
        except (InvalidId, Exception) as e:
            logger.error(f"Invalid game_id format: {game_id}")
            raise HTTPException(status_code=400, detail=f"Invalid game ID format: {game_id}")
        
        game = await Game.get(game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        await game.delete()
        return {"message": "Game deleted successfully", "game_id": game_id}
    except HTTPException:
        raise
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
        # 规范化genres格式
        for game in games:
            game["genres"] = normalize_genres(game.get("genres", []))
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
    3. 计算匹配分数并引入随机性
    4. 80%基于偏好推荐 + 20%探索性推荐（增加多样性）
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
            result = []
            for game in all_games[:limit]:
                game_dict = {
                    "_id": str(game.id),
                    "app_id": game.app_id,
                    "name": game.name,
                    "price": game.price,
                    "genres": normalize_genres(game.genres),
                    "description": game.description,
                    "positive_reviews": game.positive_reviews,
                    "negative_reviews": game.negative_reviews,
                }
                result.append(game_dict)
            return result
        
        genre_weights = prefs["genre_weights"]
        clicked_games = set(prefs.get("clicked_games", []))
        
        # 根据偏好权重计算每个游戏的得分
        scored_games = []
        for game in all_games:
            # 规范化genres格式
            genres = normalize_genres(game.genres)
            
            # 基础得分：偏好匹配
            score = 0
            for genre in genres:
                score += genre_weights.get(genre, 0)
            
            # 添加较大的随机因子（增加多样性，避免总是推荐相同游戏）
            # 随机因子范围：0-100%的基础得分，确保每次推荐都有显著变化
            if score > 0:
                random_factor = random.uniform(0, score)  # 0-100%随机波动
            else:
                random_factor = random.uniform(0, 5)  # 无偏好时给予基础随机分
            score += random_factor
            
            # 降低已点击游戏的权重（但不完全排除）
            if game.app_id in clicked_games:
                score *= 0.7
            
            # 考虑评价数量（热门度）- 也添加随机波动
            if game.positive_reviews:
                popularity_score = min(game.positive_reviews / 10000, 1.0)  # 归一化到0-1
                score += popularity_score * random.uniform(0.3, 0.8)  # 0.3-0.8随机权重
            
            scored_games.append({
                "_id": str(game.id),
                "app_id": game.app_id,
                "name": game.name,
                "price": game.price,
                "genres": genres,
                "description": game.description,
                "positive_reviews": game.positive_reviews,
                "negative_reviews": game.negative_reviews,
                "score": score
            })
        
        # 按得分排序（降序）
        scored_games.sort(key=lambda x: x["score"], reverse=True)
        
        # 完全随机化策略：从所有游戏中随机选择，但高分游戏概率更高
        # 为了增加多样性，我们使用加权随机而不是简单排序
        
        # 计算总分用于加权随机
        total_score = sum(g["score"] for g in scored_games)
        
        if total_score > 0:
            # 使用加权随机选择
            recommended = []
            available_games = scored_games.copy()
            
            for _ in range(min(limit, len(available_games))):
                # 重新计算当前可用游戏的总分
                current_total = sum(g["score"] for g in available_games)
                if current_total == 0:
                    # 如果分数都为0，完全随机选择
                    selected = random.choice(available_games)
                else:
                    # 加权随机选择
                    rand_val = random.uniform(0, current_total)
                    cumulative = 0
                    selected = available_games[0]
                    for game in available_games:
                        cumulative += game["score"]
                        if cumulative >= rand_val:
                            selected = game
                            break
                
                recommended.append(selected)
                available_games.remove(selected)
        else:
            # 完全随机选择
            random.shuffle(scored_games)
            recommended = scored_games[:limit]
        
        # 移除score字段并返回
        result = []
        for game in recommended[:limit]:
            game.pop("score")
            result.append(game)
        
        return result
        
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
        
        # 更新类型权重（点击增加1分 - 表示浏览兴趣）
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
# API路由 - Wishlist管理
# ============================================
@app.get("/wishlist")
async def get_wishlist(user_id: str = "default_user"):
    """
    获取用户的wishlist游戏列表
    
    Query参数:
    - user_id: 用户ID (默认: default_user)
    
    返回: 用户收藏的游戏详细信息列表
    """
    try:
        # 获取或创建用户
        user = await User.find_one(User.user_id == user_id)
        if not user:
            user = User(user_id=user_id, username=user_id, favorite_games=[])
            await user.insert()
        
        # 如果wishlist为空，返回空列表
        if not user.favorite_games:
            return []
        
        # 获取wishlist中游戏的详细信息
        games = await Game.find({"app_id": {"$in": user.favorite_games}}).to_list()
        
        # 规范化genres格式并添加_id字段
        result = []
        for game in games:
            game_dict = game.dict()
            game_dict["genres"] = normalize_genres(game.genres)
            game_dict["_id"] = str(game.id)
            result.append(game_dict)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to fetch wishlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/wishlist/{app_id}")
async def add_to_wishlist(app_id: int, user_id: str = "default_user"):
    """
    添加游戏到用户wishlist
    
    Path参数:
    - app_id: Steam App ID
    
    Query参数:
    - user_id: 用户ID (默认: default_user)
    
    流程:
    1. 从Steam获取游戏信息（如果数据库中不存在）
    2. 保存游戏到games集合（全局游戏库）
    3. 添加app_id到用户的favorite_games列表
    """
    try:
        # 检查游戏是否已在全局游戏库中
        game = await Game.find_one(Game.app_id == app_id)
        
        if not game:
            # 从Steam获取游戏信息
            game_data = await steam_service.get_game_details(app_id)
            if not game_data:
                raise HTTPException(status_code=404, detail=f"Game {app_id} not found on Steam")
            
            # 保存到全局游戏库
            game = Game(**game_data)
            await game.insert()
            logger.info(f"Added new game to library: {game.name}")
        
        # 获取或创建用户
        user = await User.find_one(User.user_id == user_id)
        if not user:
            user = User(user_id=user_id, username=user_id, favorite_games=[])
            await user.insert()
        
        # 检查是否已在wishlist中
        if app_id in user.favorite_games:
            return {"message": "Game already in wishlist", "app_id": app_id, "name": game.name}
        
        # 添加到wishlist
        user.favorite_games.append(app_id)
        user.last_active = datetime.utcnow()
        await user.save()
        
        # 更新用户偏好权重（加入愿望单增加5分 - 表示强烈兴趣）
        store = get_preference_store()
        prefs = store.get_user_preference(user_id)
        if prefs is None:
            prefs = {"genre_weights": {}, "clicked_games": []}
        
        # 为游戏的每个类型增加5分权重
        genres = normalize_genres(game.genres)
        for genre in genres:
            prefs["genre_weights"][genre] = prefs["genre_weights"].get(genre, 0) + 5
        
        # 保存更新后的偏好
        store.save_user_preference(user_id, prefs["genre_weights"], prefs["clicked_games"])
        
        logger.info(f"Added game {game.name} to {user_id}'s wishlist and updated preferences (+5 weight per genre)")
        return {
            "message": "Game added to wishlist",
            "app_id": app_id,
            "name": game.name,
            "preference_boost": "+5 per genre"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add to wishlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/wishlist/{app_id}")
async def remove_from_wishlist(app_id: int, user_id: str = "default_user"):
    """
    从用户wishlist中移除游戏
    
    Path参数:
    - app_id: Steam App ID
    
    Query参数:
    - user_id: 用户ID (默认: default_user)
    
    注意: 只从用户wishlist中移除，不会删除全局游戏库中的游戏
    """
    try:
        # 获取用户
        user = await User.find_one(User.user_id == user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # 检查游戏是否在wishlist中
        if app_id not in user.favorite_games:
            raise HTTPException(status_code=404, detail="Game not in wishlist")
        
        # 从wishlist中移除
        user.favorite_games.remove(app_id)
        user.last_active = datetime.utcnow()
        await user.save()
        
        logger.info(f"Removed game {app_id} from {user_id}'s wishlist")
        return {"message": "Game removed from wishlist", "app_id": app_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove from wishlist: {e}")
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
