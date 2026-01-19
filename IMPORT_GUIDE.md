# Steam游戏数据导入指南

本项目提供了多种方式从Steam导入游戏数据到MongoDB数据库。

## 方法1: 快速导入（推荐新手）

导入前100款热门游戏，适合快速测试和演示：

```bash
# 在项目根目录执行
docker-compose exec backend python quick_import.py
```

**特点:**
- ✅ 简单快速，约5-10分钟完成
- ✅ 导入最热门的100款游戏
- ✅ 包含完整的游戏信息（名称、类型、价格、评价等）

---

## 方法2: 批量导入（高级用户）

支持自定义数量的游戏导入，可导入数千款游戏：

### 导入1000款游戏（默认）
```bash
docker-compose exec backend python import_steam_games.py
```

### 导入指定数量的游戏
```bash
# 导入500款游戏
docker-compose exec backend python import_steam_games.py --limit 500

# 导入所有游戏（约10万款，需要数小时）
docker-compose exec backend python import_steam_games.py --limit 0
```

### 调整批次大小（优化性能）
```bash
# 每批处理100款游戏
docker-compose exec backend python import_steam_games.py --limit 1000 --batch-size 100
```

**参数说明:**
- `--limit`: 导入数量限制（默认1000，设为0表示全部）
- `--batch-size`: 批次大小（默认50，可调整为20-100）

---

## 方法3: 本地运行（不使用Docker）

如果你在本地开发环境中运行：

```bash
cd backend
python import_steam_games.py --limit 100
```

**前提条件:**
- Python 3.11+
- 已安装依赖: `pip install -r requirements.txt`
- MongoDB运行在 localhost:27017

---

## 导入进度示例

```
==============================================================
Steam游戏数据导入工具
==============================================================
✓ 数据库已连接: steamgamerec
正在从SteamSpy获取所有游戏列表...
✓ 获取到 98754 款游戏

计划导入 1000 款游戏
批次大小: 50

[批次 1/20] 处理 50 款游戏...
  进度: 10/50 (跳过: 0, 成功: 8, 失败: 2)
  进度: 20/50 (跳过: 0, 成功: 17, 失败: 3)
  ...
[批次 1] 完成 - 成功: 45, 跳过: 0, 失败: 5

...

==============================================================
导入完成!
==============================================================
总计处理: 1000 款游戏
成功导入: 950
已存在跳过: 0
失败: 50
耗时: 876.32 秒
==============================================================
```

---

## 验证导入结果

### 通过MongoDB查看
```bash
# 进入MongoDB容器
docker-compose exec mongodb mongosh steamgamerec

# 查看游戏数量
db.games.countDocuments()

# 查看最新导入的游戏
db.games.find().limit(5).pretty()
```

### 通过API查看
```bash
# 获取游戏列表
curl http://localhost:8000/games?limit=10

# 获取推荐游戏
curl http://localhost:8000/recommendations?limit=10
```

### 通过前端查看
访问 http://localhost:3000，在Wishlist页面可以看到所有导入的游戏。

---

## 注意事项

### API限流
SteamSpy API有请求频率限制：
- 脚本已内置0.5秒延迟避免限流
- 如遇到频繁失败，可增加延迟时间（修改 `asyncio.sleep(0.5)` 为更大值）

### 导入时间估算
- 100款游戏: ~5-10分钟
- 1000款游戏: ~15-30分钟
- 10000款游戏: ~2-5小时
- 全部游戏: ~10-20小时

### 数据库大小
- 1000款游戏: ~5-10 MB
- 10000款游戏: ~50-100 MB
- 全部游戏: ~500 MB - 1 GB

### 断点续传
脚本会自动跳过已存在的游戏，中途中断后可以重新运行继续导入。

---

## 故障排除

### 错误: "Connection refused"
```bash
# 确保MongoDB容器正在运行
docker-compose ps

# 重启服务
docker-compose restart mongodb backend
```

### 错误: "HTTPError 429"
说明API请求过于频繁，增加延迟时间：
- 修改脚本中的 `await asyncio.sleep(0.5)` 为 `await asyncio.sleep(1.0)`

### 导入速度太慢
- 增加批次大小: `--batch-size 100`
- 减少导入数量: `--limit 500`
- 使用快速导入脚本: `quick_import.py`

---

## 数据源

游戏数据来自 **SteamSpy API** (https://steamspy.com/api.php)

包含字段:
- 游戏ID (app_id)
- 游戏名称 (name)
- 价格 (price)
- 类型标签 (genres)
- 描述 (description)
- 发布日期 (release_date)
- 正面评价数 (positive_reviews)
- 负面评价数 (negative_reviews)

---

## 高级用法

### 只导入特定类型的游戏
修改脚本，在 `fetch_game_details` 函数中添加类型过滤：

```python
# 只导入包含"Action"类型的游戏
genres = data.get("genre", "").split(", ")
if "Action" not in genres:
    return None
```

### 导出数据到JSON
```bash
docker-compose exec mongodb mongoexport \
  --db=steamgamerec \
  --collection=games \
  --out=/tmp/games.json

docker cp steamgamerec-mongodb:/tmp/games.json ./games.json
```

### 清空现有数据重新导入
```bash
# 删除所有游戏数据
docker-compose exec mongodb mongosh steamgamerec --eval "db.games.deleteMany({})"

# 重新导入
docker-compose exec backend python quick_import.py
```
