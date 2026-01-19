"""
Steam API Integration Service
Steam数据获取服务 - 直接使用SteamSpy API

功能:
1. 获取游戏详细信息 (价格、类型、评价等)
2. 搜索游戏
3. 获取热门游戏列表

使用 SteamSpy API 的 HTTP 接口:
- https://steamspy.com/api.php
"""
import httpx
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class SteamService:
    """Steam API封装类 - 直接调用SteamSpy HTTP API"""
    
    BASE_URL = "https://steamspy.com/api.php"
    
    def __init__(self):
        """初始化HTTP客户端"""
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_game_details(self, app_id: int) -> Optional[Dict]:
        """
        获取单个游戏的详细信息
        
        Args:
            app_id (int): Steam App ID
        
        Returns:
            Dict: 游戏详细信息,如果未找到返回None
        """
        try:
            # 直接调用 SteamSpy HTTP API
            url = f"{self.BASE_URL}?request=appdetails&appid={app_id}"
            response = await self.client.get(url)
            response.raise_for_status()
            
            data = response.json()
            
            # 检查是否成功返回数据
            if not data or data.get('name') in ['', None]:
                logger.warning(f"Game {app_id} not found")
                return None
            
            # 处理价格 - SteamSpy 返回的可能是字符串或整数
            price_raw = data.get("price", "0")
            try:
                price = float(price_raw) / 100 if price_raw not in [None, '', '0'] else 0.0
            except (ValueError, TypeError):
                price = 0.0
            
            # 提取关键字段
            game_info = {
                "app_id": app_id,
                "name": data.get("name", "Unknown"),
                "price": price,
                "genres": data.get("genre", "").split(", ") if data.get("genre") else [],
                "description": data.get("short_description", "No description available"),
                "release_date": data.get("release_date", "Unknown"),
                "positive_reviews": data.get("positive", 0),
                "negative_reviews": data.get("negative", 0),
            }
            
            logger.info(f"Successfully fetched game: {game_info['name']}")
            return game_info
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching game {app_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch game {app_id}: {e}")
            return None
    
    async def get_top_games(self, limit: int = 20) -> List[Dict]:
        """
        获取热门游戏列表（带类型标签）
        
        Args:
            limit (int): 返回数量限制
        
        Returns:
            List[Dict]: 游戏列表
        """
        try:
            # 首先获取热门游戏列表（按最近两周排名）
            top_url = f"{self.BASE_URL}?request=top100in2weeks"
            top_response = await self.client.get(top_url)
            top_response.raise_for_status()
            top_data = top_response.json()
            
            # 获取前N个游戏的app_id
            top_app_ids = list(top_data.keys())[:limit]
            
            # 为每个游戏获取详细信息（包含genre）
            games = []
            for app_id in top_app_ids:
                try:
                    game_data = top_data[app_id]
                    
                    # 尝试从详细API获取genre信息
                    detail_url = f"{self.BASE_URL}?request=appdetails&appid={app_id}"
                    detail_response = await self.client.get(detail_url)
                    detail_response.raise_for_status()
                    detail_data = detail_response.json()
                    
                    games.append({
                        "app_id": int(app_id),
                        "name": game_data.get("name", "Unknown"),
                        "positive_reviews": game_data.get("positive", 0),
                        "negative_reviews": game_data.get("negative", 0),
                        "genres": detail_data.get("genre", "").split(", ") if detail_data.get("genre") else [],
                    })
                except (ValueError, TypeError, httpx.HTTPError) as e:
                    logger.warning(f"Skipping invalid game data for {app_id}: {e}")
                    continue
            
            logger.info(f"Successfully fetched {len(games)} top games with genres")
            return games
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching top games: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch top games: {e}")
            return []
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()


# 全局Steam服务实例
steam_service = SteamService()
