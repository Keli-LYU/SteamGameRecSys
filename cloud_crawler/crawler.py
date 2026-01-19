"""
云端爬虫服务 - Steam数据自动采集
部署在云端（GitHub Actions / Lambda / 云服务器），定时爬取Steam数据并存入MongoDB Atlas
"""
import asyncio
import os
import sys
from datetime import datetime
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie, Document
from pydantic import Field
from typing import List, Optional

# ============================================
# 配置
# ============================================
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb+srv://username:password@cluster.mongodb.net/")
DATABASE_NAME = os.getenv("DATABASE_NAME", "steamgamerec")
STEAMSPY_BASE_URL = "https://steamspy.com/api.php"

# ============================================
# 简化的Game模型（只用于爬虫）
# ============================================
class Game(Document):
    """游戏数据模型"""
    app_id: int
    name: str
    price: Optional[float] = None
    genres: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    release_date: Optional[str] = None
    positive_reviews: Optional[int] = None
    negative_reviews: Optional[int] = None
    owners: Optional[str] = None
    players_forever: Optional[int] = None
    players_2weeks: Optional[int] = None
    average_forever: Optional[int] = None
    average_2weeks: Optional[int] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "games"
        indexes = ["app_id"]


# ============================================
# 数据库初始化
# ============================================
async def init_database():
    """连接MongoDB Atlas"""
    print(f"🔗 正在连接MongoDB Atlas...")
    client = AsyncIOMotorClient(MONGODB_URL)
    await init_beanie(
        database=client[DATABASE_NAME],
        document_models=[Game]
    )
    print(f"✅ 已连接到数据库: {DATABASE_NAME}")


# ============================================
# 爬取函数
# ============================================
async def fetch_all_games_list():
    """
    获取所有游戏列表（分页）
    注意：SteamSpy限制每60秒一次请求
    """
    print("\n📡 开始获取Steam游戏列表...")
    all_games = {}
    page = 0
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        while True:
            try:
                print(f"  📄 获取第 {page + 1} 页...")
                url = f"{STEAMSPY_BASE_URL}?request=all&page={page}"
                response = await client.get(url)
                response.raise_for_status()
                
                data = response.json()
                
                if not data or len(data) == 0:
                    break
                
                all_games.update(data)
                print(f"  ✅ 第 {page + 1} 页: {len(data)} 款游戏 (累计: {len(all_games)})")
                
                page += 1
                
                # API限流：每页等待60秒
                if len(data) == 1000:
                    print(f"  ⏳ 等待60秒...")
                    await asyncio.sleep(60)
                else:
                    break
                    
            except Exception as e:
                print(f"  ❌ 第 {page + 1} 页出错: {e}")
                break
    
    print(f"\n✅ 总共获取 {len(all_games)} 款游戏")
    return all_games


async def fetch_game_details(app_id: int, client: httpx.AsyncClient):
    """获取单个游戏详情"""
    try:
        url = f"{STEAMSPY_BASE_URL}?request=appdetails&appid={app_id}"
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"  ⚠️  游戏 {app_id} 获取失败: {e}")
        return None


async def import_game_to_db(game_data: dict):
    """将游戏数据导入数据库（更新或插入）"""
    try:
        app_id = int(game_data.get("appid", 0))
        
        # 检查游戏是否已存在
        existing_game = await Game.find_one(Game.app_id == app_id)
        
        # 安全处理价格（可能是字符串或数字）
        price_raw = game_data.get("price", 0)
        try:
            price = float(price_raw) / 100 if price_raw else 0
        except (ValueError, TypeError):
            price = 0  # 如果是 "free" 或其他非数字，设为0
        
        # 安全处理类型（可能是字典或字符串）
        genre_raw = game_data.get("genre", {})
        if isinstance(genre_raw, dict):
            genres = list(genre_raw.keys())
        elif isinstance(genre_raw, str):
            genres = [genre_raw] if genre_raw else []
        else:
            genres = []
        
        game_info = {
            "app_id": app_id,
            "name": game_data.get("name", "Unknown"),
            "price": price,
            "genres": genres,
            "positive_reviews": game_data.get("positive", 0),
            "negative_reviews": game_data.get("negative", 0),
            "owners": game_data.get("owners", "0"),
            "players_forever": game_data.get("players_forever", 0),
            "players_2weeks": game_data.get("players_2weeks", 0),
            "average_forever": game_data.get("average_forever", 0),
            "average_2weeks": game_data.get("average_2weeks", 0),
            "updated_at": datetime.utcnow()
        }
        
        if existing_game:
            # 更新现有游戏
            await existing_game.set(game_info)
            return "updated"
        else:
            # 插入新游戏
            new_game = Game(**game_info)
            await new_game.insert()
            return "inserted"
            
    except Exception as e:
        print(f"  ❌ 导入游戏 {game_data.get('appid')} 失败: {e}")
        return "failed"


# ============================================
# 主爬取任务
# ============================================
async def crawl_and_update():
    """
    主爬取流程：
    1. 获取所有游戏列表
    2. 批量获取游戏详情
    3. 更新到MongoDB Atlas
    """
    print("=" * 70)
    print("🤖 Steam云端爬虫服务启动")
    print(f"⏰ 运行时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 70)
    
    # 初始化数据库
    await init_database()
    
    # 获取游戏列表
    games_list = await fetch_all_games_list()
    
    if not games_list:
        print("❌ 未获取到游戏数据，任务终止")
        return
    
    # 批量导入
    print(f"\n📥 开始导入 {len(games_list)} 款游戏...")
    
    stats = {"inserted": 0, "updated": 0, "failed": 0}
    batch_size = 50
    delay = 0.5
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        game_ids = list(games_list.keys())
        
        for i in range(0, len(game_ids), batch_size):
            batch = game_ids[i:i + batch_size]
            print(f"\n[批次 {i//batch_size + 1}] 处理 {len(batch)} 款游戏...")
            
            for app_id in batch:
                # 获取详细信息
                details = await fetch_game_details(int(app_id), client)
                
                if details:
                    result = await import_game_to_db(details)
                    stats[result] = stats.get(result, 0) + 1
                else:
                    stats["failed"] += 1
                
                await asyncio.sleep(delay)
            
            # 批次统计
            print(f"  ✅ 新增: {stats['inserted']} | 更新: {stats['updated']} | 失败: {stats['failed']}")
    
    # 最终统计
    print("\n" + "=" * 70)
    print("🎉 爬取任务完成！")
    print(f"📊 新增游戏: {stats['inserted']}")
    print(f"🔄 更新游戏: {stats['updated']}")
    print(f"❌ 失败: {stats['failed']}")
    print(f"⏱️  完成时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 70)


# ============================================
# 快速更新模式（仅更新Top 1000）
# ============================================
async def quick_update_top_games():
    """
    快速更新模式：只更新前1000款热门游戏
    适用于每日增量更新
    """
    print("⚡ 快速更新模式 - Top 1000游戏")
    
    await init_database()
    
    print("\n📡 获取Top 1000游戏...")
    async with httpx.AsyncClient(timeout=60.0) as client:
        url = f"{STEAMSPY_BASE_URL}?request=all&page=0"
        response = await client.get(url)
        response.raise_for_status()
        games_list = response.json()
    
    print(f"✅ 获取到 {len(games_list)} 款游戏")
    
    stats = {"inserted": 0, "updated": 0, "failed": 0}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, (app_id, _) in enumerate(games_list.items(), 1):
            details = await fetch_game_details(int(app_id), client)
            
            if details:
                result = await import_game_to_db(details)
                stats[result] = stats.get(result, 0) + 1
            else:
                stats["failed"] += 1
            
            if i % 100 == 0:
                print(f"  进度: {i}/{len(games_list)} | 新增: {stats['inserted']} | 更新: {stats['updated']}")
            
            await asyncio.sleep(0.5)
    
    print(f"\n✅ 快速更新完成: 新增 {stats['inserted']}, 更新 {stats['updated']}, 失败 {stats['failed']}")


# ============================================
# 命令行入口
# ============================================
if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "quick"
    
    if mode == "full":
        # 完整爬取所有游戏
        asyncio.run(crawl_and_update())
    else:
        # 快速更新Top 1000
        asyncio.run(quick_update_top_games())
