"""
快速导入热门游戏到数据库
从SteamSpy获取最热门的游戏并存入数据库

使用方法:
    docker-compose exec backend python quick_import.py
"""
import asyncio
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import os
import sys

sys.path.insert(0, '/app')
from app.models import Game

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://mongodb:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "steamgamerec")
STEAMSPY_BASE_URL = "https://steamspy.com/api.php"


async def init_db():
    """初始化数据库"""
    client = AsyncIOMotorClient(MONGODB_URL)
    await init_beanie(
        database=client[DATABASE_NAME],
        document_models=[Game]
    )
    print("✓ 数据库已连接")


async def fetch_and_save_top_games(limit=100):
    """获取并保存热门游戏"""
    print(f"正在获取前 {limit} 款热门游戏...")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 获取热门游戏列表
        url = f"{STEAMSPY_BASE_URL}?request=top100in2weeks"
        response = await client.get(url)
        data = response.json()
        
        top_games = list(data.items())[:limit]
        print(f"获取到 {len(top_games)} 款游戏")
        
        success = 0
        skip = 0
        
        for i, (app_id, game_basic) in enumerate(top_games, 1):
            try:
                app_id = int(app_id)
                
                # 检查是否已存在
                existing = await Game.find_one(Game.app_id == app_id)
                if existing:
                    skip += 1
                    continue
                
                # 获取详细信息
                detail_url = f"{STEAMSPY_BASE_URL}?request=appdetails&appid={app_id}"
                detail_response = await client.get(detail_url)
                detail_data = detail_response.json()
                
                if not detail_data.get('name'):
                    continue
                
                # 处理价格
                price_raw = detail_data.get("price", "0")
                try:
                    price = float(price_raw) / 100 if price_raw not in [None, '', '0'] else 0.0
                except:
                    price = 0.0
                
                # 创建游戏记录
                game = Game(
                    app_id=app_id,
                    name=detail_data.get("name", "Unknown"),
                    price=price,
                    genres=detail_data.get("genre", "").split(", ") if detail_data.get("genre") else [],
                    description=detail_data.get("short_description", ""),
                    release_date=detail_data.get("release_date", "Unknown"),
                    positive_reviews=detail_data.get("positive", 0),
                    negative_reviews=detail_data.get("negative", 0),
                )
                
                await game.insert()
                success += 1
                
                if i % 10 == 0:
                    print(f"进度: {i}/{len(top_games)} (成功: {success}, 跳过: {skip})")
                
                # 避免API限流
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"处理游戏 {app_id} 失败: {e}")
        
        print(f"\n完成! 成功: {success}, 跳过: {skip}")


async def main():
    await init_db()
    await fetch_and_save_top_games(100)


if __name__ == "__main__":
    asyncio.run(main())
