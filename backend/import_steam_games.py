"""
Steam游戏数据导入脚本
从SteamSpy API批量导入游戏数据到MongoDB

使用方法:
    docker-compose exec backend python import_steam_games.py --all
    docker-compose exec backend python import_steam_games.py --limit 1000

参数:
    --all: 导入所有游戏（忽略--limit参数）
    --limit: 导入游戏数量限制 (默认: 1000)
    --batch-size: 批量处理大小 (默认: 50)
    --skip: 跳过前N款游戏（用于断点续传）
    --delay: API请求延迟秒数 (默认: 0.5)
    --retry: 失败重试次数 (默认: 3)
"""
import asyncio
import httpx
import argparse
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from datetime import datetime
import sys
import os
import json
from pathlib import Path

# 添加app目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
from models import Game

# MongoDB配置
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://mongodb:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "steamgamerec")

# SteamSpy API配置
STEAMSPY_BASE_URL = "https://steamspy.com/api.php"

# 进度文件
PROGRESS_FILE = "/tmp/import_progress.json"


async def init_database():
    """初始化数据库连接"""
    client = AsyncIOMotorClient(MONGODB_URL)
    await init_beanie(
        database=client[DATABASE_NAME],
        document_models=[Game]
    )
    print(f"✓ 数据库已连接: {DATABASE_NAME}")


async def fetch_all_games():
    """
    从SteamSpy获取所有游戏的基础信息（支持分页）
    注意: SteamSpy API限制 - all请求每60秒只能1次
    返回: dict {app_id: game_data}
    """
    print("正在从SteamSpy获取所有游戏列表...")
    print("⚠️  注意: SteamSpy 'all'端点限制每60秒1次请求，获取全部数据需要较长时间...")
    
    all_games = {}
    page = 0
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        while True:
            try:
                print(f"  正在获取第 {page + 1} 页...")
                url = f"{STEAMSPY_BASE_URL}?request=all&page={page}"
                response = await client.get(url)
                response.raise_for_status()
                
                data = response.json()
                
                # 如果返回空数据或没有新数据，说明已经获取完所有游戏
                if not data or len(data) == 0:
                    break
                
                all_games.update(data)
                print(f"  ✓ 第 {page + 1} 页: 获取 {len(data)} 款游戏 (累计: {len(all_games)} 款)")
                
                page += 1
                
                # SteamSpy API限制: all请求每60秒1次
                # 为了避免被限流，每页之间等待60秒
                if len(data) == 1000:  # 如果返回满页，说明可能还有下一页
                    print(f"  ⏳ 等待60秒以遵守API限制...")
                    await asyncio.sleep(60)
                else:
                    break  # 如果不是满页，说明这是最后一页了
                    
            except Exception as e:
                print(f"  ✗ 获取第 {page + 1} 页时出错: {str(e)}")
                break
    
    print(f"✓ 总共获取到 {len(all_games)} 款游戏")
    return all_games


async def fetch_game_details(app_id: int, client: httpx.AsyncClient, retry_count: int = 3):
    """
    获取单个游戏的详细信息（带重试机制）
    """
    for attempt in range(retry_count):
        try:
            url = f"{STEAMSPY_BASE_URL}?request=appdetails&appid={app_id}"
            response = await client.get(url)
            response.raise_for_status()
            
            data = response.json()
            
            # 验证数据有效性
            if not data or not data.get('name'):
                return None
            
            # 处理价格
            price_raw = data.get("price", "0")
            try:
                price = float(price_raw) / 100 if price_raw not in [None, '', '0'] else 0.0
            except (ValueError, TypeError):
                price = 0.0
            
            # 构建游戏对象
            game_data = {
                "app_id": app_id,
                "name": data.get("name", "Unknown"),
                "price": price,
                "genres": data.get("genre", "").split(", ") if data.get("genre") else [],
                "description": data.get("short_description", "No description available"),
                "release_date": data.get("release_date", "Unknown"),
                "positive_reviews": data.get("positive", 0),
                "negative_reviews": data.get("negative", 0),
            }
            
            return game_data
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:  # Too Many Requests
                wait_time = (attempt + 1) * 2  # 递增等待时间
                print(f"  ⚠ API限流，等待{wait_time}秒...")
                await asyncio.sleep(wait_time)
            else:
                if attempt == retry_count - 1:
                    print(f"  ✗ 获取游戏 {app_id} 失败: HTTP {e.response.status_code}")
                return None
        except Exception as e:
            if attempt == retry_count - 1:
                print(f"  ✗ 获取游戏 {app_id} 失败: {e}")
            await asyncio.sleep(1)
    
    return None


async def import_games_batch(app_ids: list, batch_num: int, total_batches: int, delay: float = 0.5, retry: int = 3):
    """
    批量导入游戏数据
    """
    print(f"\n[批次 {batch_num}/{total_batches}] 处理 {len(app_ids)} 款游戏...")
    
    success_count = 0
    skip_count = 0
    error_count = 0
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, app_id in enumerate(app_ids, 1):
            try:
                # 检查是否已存在
                existing = await Game.find_one(Game.app_id == app_id)
                if existing:
                    skip_count += 1
                    if i % 20 == 0:
                        print(f"  进度: {i}/{len(app_ids)} | 成功: {success_count} | 跳过: {skip_count} | 失败: {error_count}")
                    continue
                
                # 获取详细信息（带重试）
                game_data = await fetch_game_details(app_id, client, retry)
                
                if game_data:
                    # 保存到数据库
                    game = Game(**game_data)
                    await game.insert()
                    success_count += 1
                else:
                    error_count += 1
                
                # 每20个游戏显示一次进度
                if i % 20 == 0:
                    print(f"  进度: {i}/{len(app_ids)} | 成功: {success_count} | 跳过: {skip_count} | 失败: {error_count}")
                
                # API限流控制
                await asyncio.sleep(delay)
                
            except Exception as e:
                error_count += 1
                print(f"  ✗ 处理游戏 {app_id} 时出错: {e}")
    
    print(f"[批次 {batch_num}] 完成 - 成功: {success_count} | 跳过: {skip_count} | 失败: {error_count}")
    return success_count, skip_count, error_count


def save_progress(processed_count: int, total_count: int, success: int, skip: int, error: int):
    """保存导入进度"""
    try:
        progress = {
            "processed": processed_count,
            "total": total_count,
            "success": success,
            "skip": skip,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress, f)
    except Exception as e:
        print(f"保存进度失败: {e}")


def load_progress():
    """加载导入进度"""
    try:
        if Path(PROGRESS_FILE).exists():
            with open(PROGRESS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"加载进度失败: {e}")
    return None


async def import_all_games(import_all: bool = False, limit: int = 1000, batch_size: int = 50, 
                          skip: int = 0, delay: float = 0.5, retry: int = 3):
    """
    主导入函数
    """
    start_time = datetime.now()
    print("\n" + "="*70)
    print("Steam游戏数据批量导入工具 v2.0")
    print("="*70)
    
    # 初始化数据库
    await init_database()
    
    # 获取所有游戏列表
    all_games = await fetch_all_games()
    
    # 转换为列表并排序（按app_id排序以保证一致性）
    app_ids = sorted([int(app_id) for app_id in all_games.keys()])
    total_available = len(app_ids)
    
    print(f"\nSteam游戏总数: {total_available:,} 款")
    
    # 应用skip参数
    if skip > 0:
        print(f"跳过前 {skip} 款游戏")
        app_ids = app_ids[skip:]
    
    # 确定要导入的游戏数量
    if import_all:
        print(f"模式: 导入所有游戏")
        games_to_import = len(app_ids)
    else:
        games_to_import = min(limit, len(app_ids))
        app_ids = app_ids[:games_to_import]
        print(f"模式: 限制导入 {games_to_import} 款游戏")
    
    print(f"批次大小: {batch_size}")
    print(f"API延迟: {delay}秒")
    print(f"重试次数: {retry}")
    
    # 检查是否有保存的进度
    saved_progress = load_progress()
    if saved_progress and not import_all:
        print(f"\n发现保存的进度:")
        print(f"  已处理: {saved_progress['processed']}/{saved_progress['total']}")
        print(f"  成功: {saved_progress['success']}, 跳过: {saved_progress['skip']}, 失败: {saved_progress['error']}")
    
    # 估算时间
    estimated_time = (games_to_import * (delay + 0.5)) / 60  # 分钟
    if estimated_time >= 60:
        print(f"预计耗时: {estimated_time/60:.1f} 小时")
    else:
        print(f"预计耗时: {estimated_time:.1f} 分钟")
    
    # 分批处理
    total_success = 0
    total_skip = 0
    total_error = 0
    processed = 0
    
    total_batches = (len(app_ids) + batch_size - 1) // batch_size
    
    print(f"\n开始导入 (共{total_batches}批次)...")
    print("="*70)
    
    for i in range(0, len(app_ids), batch_size):
        batch = app_ids[i:i + batch_size]
        batch_num = i // batch_size + 1
        
        success, skip_count, error = await import_games_batch(
            batch, batch_num, total_batches, delay, retry
        )
        
        total_success += success
        total_skip += skip_count
        total_error += error
        processed += len(batch)
        
        # 保存进度
        save_progress(processed, games_to_import, total_success, total_skip, total_error)
        
        # 每10个批次显示总体进度
        if batch_num % 10 == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = processed / elapsed if elapsed > 0 else 0
            remaining = (games_to_import - processed) / rate if rate > 0 else 0
            print(f"\n📊 总体进度: {processed}/{games_to_import} ({processed/games_to_import*100:.1f}%)")
            print(f"   成功: {total_success} | 跳过: {total_skip} | 失败: {total_error}")
            print(f"   速度: {rate:.1f} 游戏/秒 | 剩余时间: {remaining/60:.1f} 分钟\n")
    
    # 统计结果
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "="*70)
    print("导入完成!")
    print("="*70)
    print(f"总计处理: {processed:,} 款游戏")
    print(f"✓ 成功导入: {total_success:,}")
    print(f"○ 已存在跳过: {total_skip:,}")
    print(f"✗ 失败: {total_error:,}")
    print(f"⏱ 耗时: {duration/60:.1f} 分钟 ({duration:.1f} 秒)")
    print(f"⚡ 平均速度: {processed/duration:.2f} 游戏/秒")
    print("="*70)
    
    # 清理进度文件
    try:
        if Path(PROGRESS_FILE).exists():
            os.remove(PROGRESS_FILE)
    except:
        pass


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description='从Steam批量导入游戏数据到MongoDB',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 导入所有Steam游戏
  python import_steam_games.py --all
  
  # 导入1000款游戏（默认）
  python import_steam_games.py
  
  # 导入5000款游戏
  python import_steam_games.py --limit 5000
  
  # 从第1000款开始导入
  python import_steam_games.py --skip 1000 --limit 1000
  
  # 调整批次和延迟
  python import_steam_games.py --all --batch-size 100 --delay 1.0
        """
    )
    
    parser.add_argument('--all', action='store_true',
                       help='导入所有Steam游戏（忽略--limit参数）')
    parser.add_argument('--limit', type=int, default=1000, 
                       help='导入数量限制 (默认: 1000)')
    parser.add_argument('--batch-size', type=int, default=50,
                       help='批次大小 (默认: 50, 建议: 20-100)')
    parser.add_argument('--skip', type=int, default=0,
                       help='跳过前N款游戏（用于断点续传）')
    parser.add_argument('--delay', type=float, default=0.5,
                       help='API请求延迟秒数 (默认: 0.5, 建议: 0.3-2.0)')
    parser.add_argument('--retry', type=int, default=3,
                       help='失败重试次数 (默认: 3)')
    
    args = parser.parse_args()
    
    # 参数验证
    if args.batch_size < 1 or args.batch_size > 500:
        print("错误: batch-size 必须在 1-500 之间")
        return
    
    if args.delay < 0.1 or args.delay > 10:
        print("错误: delay 必须在 0.1-10 之间")
        return
    
    if args.skip < 0:
        print("错误: skip 不能为负数")
        return
    
    # 运行导入
    asyncio.run(import_all_games(
        import_all=args.all,
        limit=args.limit,
        batch_size=args.batch_size,
        skip=args.skip,
        delay=args.delay,
        retry=args.retry
    ))


if __name__ == "__main__":
    main()
