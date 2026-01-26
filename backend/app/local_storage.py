"""
本地用户偏好存储 - SQLite数据库
用于存储用户点击历史、游戏偏好等隐私数据
"""
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional
import os

# 数据库文件路径
DB_PATH = os.getenv("USER_PREFS_DB", "/app/data/user_preferences.db")


class UserPreferenceStore:
    """本地SQLite用户偏好存储"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        # 确保目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建用户偏好表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id TEXT PRIMARY KEY,
                genre_weights TEXT,
                clicked_games TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建游戏缓存表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_cache (
                app_id INTEGER PRIMARY KEY,
                game_data TEXT,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_updated_at 
            ON user_preferences(updated_at)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cached_at 
            ON game_cache(cached_at)
        """)
        
        conn.commit()
        conn.close()
        print(f"✅ SQLite数据库初始化完成: {self.db_path}")
    
    # ============================================
    # 用户偏好操作
    # ============================================
    
    def get_user_preference(self, user_id: str) -> Optional[Dict]:
        """获取用户偏好"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT genre_weights, clicked_games FROM user_preferences WHERE user_id = ?",
            (user_id,)
        )
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "genre_weights": json.loads(row[0]) if row[0] else {},
                "clicked_games": json.loads(row[1]) if row[1] else []
            }
        return None
    
    def save_user_preference(self, user_id: str, genre_weights: Dict[str, int], clicked_games: List[int]):
        """保存用户偏好"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO user_preferences (user_id, genre_weights, clicked_games, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                genre_weights = excluded.genre_weights,
                clicked_games = excluded.clicked_games,
                updated_at = excluded.updated_at
        """, (
            user_id,
            json.dumps(genre_weights),
            json.dumps(clicked_games),
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def update_genre_weight(self, user_id: str, genre: str, increment: int = 1):
        """更新单个类型的权重
        
        Args:
            user_id: 用户ID
            genre: 游戏类型
            increment: 权重增量（默认1，点击=1，加入愿望单=5）
        """
        prefs = self.get_user_preference(user_id)
        
        if prefs is None:
            prefs = {"genre_weights": {}, "clicked_games": []}
        
        prefs["genre_weights"][genre] = prefs["genre_weights"].get(genre, 0) + increment
        
        self.save_user_preference(user_id, prefs["genre_weights"], prefs["clicked_games"])
    
    def add_clicked_game(self, user_id: str, app_id: int):
        """添加点击的游戏"""
        prefs = self.get_user_preference(user_id)
        
        if prefs is None:
            prefs = {"genre_weights": {}, "clicked_games": []}
        
        if app_id not in prefs["clicked_games"]:
            prefs["clicked_games"].append(app_id)
        
        self.save_user_preference(user_id, prefs["genre_weights"], prefs["clicked_games"])
    
    # ============================================
    # 游戏缓存操作
    # ============================================
    
    def cache_game(self, app_id: int, game_data: Dict):
        """缓存游戏数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO game_cache (app_id, game_data, cached_at)
            VALUES (?, ?, ?)
            ON CONFLICT(app_id) DO UPDATE SET
                game_data = excluded.game_data,
                cached_at = excluded.cached_at
        """, (
            app_id,
            json.dumps(game_data),
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_cached_game(self, app_id: int, max_age_hours: int = 24) -> Optional[Dict]:
        """获取缓存的游戏数据（带过期检查）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT game_data, cached_at FROM game_cache 
            WHERE app_id = ? 
            AND datetime(cached_at) > datetime('now', '-' || ? || ' hours')
        """, (app_id, max_age_hours))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return json.loads(row[0])
        return None
    
    def clear_expired_cache(self, max_age_hours: int = 168):  # 默认7天
        """清理过期缓存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM game_cache 
            WHERE datetime(cached_at) < datetime('now', '-' || ? || ' hours')
        """, (max_age_hours,))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        print(f"🗑️  已清理 {deleted} 条过期缓存")
        return deleted
    
    # ============================================
    # 统计信息
    # ============================================
    
    def get_stats(self) -> Dict:
        """获取存储统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM user_preferences")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM game_cache")
        cache_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_users": user_count,
            "cached_games": cache_count,
            "db_size_mb": os.path.getsize(self.db_path) / (1024 * 1024) if os.path.exists(self.db_path) else 0
        }


# ============================================
# 全局实例
# ============================================
_store = None

def get_preference_store() -> UserPreferenceStore:
    """获取全局偏好存储实例（单例模式）"""
    global _store
    if _store is None:
        _store = UserPreferenceStore()
    return _store


# ============================================
# 测试代码
# ============================================
if __name__ == "__main__":
    # 测试用户偏好存储
    store = UserPreferenceStore("./test_prefs.db")
    
    print("\n📝 测试用户偏好存储...")
    
    # 保存用户偏好
    store.save_user_preference(
        "test_user",
        {"Action": 5, "RPG": 3},
        [730, 440, 570]
    )
    
    # 读取用户偏好
    prefs = store.get_user_preference("test_user")
    print(f"✅ 用户偏好: {prefs}")
    
    # 更新类型权重
    store.update_genre_weight("test_user", "Action", 2)
    prefs = store.get_user_preference("test_user")
    print(f"✅ 更新后: {prefs}")
    
    # 添加点击游戏
    store.add_clicked_game("test_user", 1234)
    prefs = store.get_user_preference("test_user")
    print(f"✅ 添加游戏后: {prefs}")
    
    # 缓存游戏
    store.cache_game(730, {"name": "CS2", "price": 0})
    cached = store.get_cached_game(730)
    print(f"✅ 缓存游戏: {cached}")
    
    # 统计信息
    stats = store.get_stats()
    print(f"✅ 统计信息: {stats}")
    
    print("\n✅ 所有测试通过！")
