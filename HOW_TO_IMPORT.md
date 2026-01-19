# Steam游戏数据导入使用指南

## 快速开始 - 导入100款热门游戏

这是最简单的方法，适合快速测试推荐系统：

```bash
# 在项目根目录执行（Windows PowerShell）
docker-compose exec backend python quick_import.py
```

预计需要5-10分钟完成。

---

## 导入所有Steam游戏（推荐）

### ⚠️ 重要提示：SteamSpy API限制

SteamSpy的 `all` 端点有严格的速率限制：**每60秒只能请求1次**

- 每次请求返回1000款游戏
- 约10万款游戏需要请求100次
- **预计总耗时：100页 × 60秒 = 100分钟（约1.7小时）仅用于获取游戏列表**
- 加上详细信息获取，**总时间约8-12小时**

### 🚀 一键导入所有游戏
```bash
docker-compose exec backend python import_steam_games.py --all
```

这将导入Steam上的**所有游戏**（约10万款），预计需要**8-12小时**。

**特点:**
- ✅ 自动分页遍历所有Steam游戏（遵守60秒/页限制）
- ✅ 自动跳过已存在的游戏（断点续传）
- ✅ API限流保护和自动重试
- ✅ 实时进度显示和保存
- ✅ 可随时中断，重新运行继续导入

---

## 其他导入选项

### 导入指定数量的游戏
```bash
# 导入1000款游戏（默认）
docker-compose exec backend python import_steam_games.py

# 导入5000款游戏
docker-compose exec backend python import_steam_games.py --limit 5000

# 导入500款游戏
docker-compose exec backend python import_steam_games.py --limit 500
```

### 断点续传（从指定位置开始）
```bash
# 跳过前1000款，继续导入接下来的1000款
docker-compose exec backend python import_steam_games.py --skip 1000 --limit 1000

# 跳过前5000款，导入所有剩余游戏
docker-compose exec backend python import_steam_games.py --skip 5000 --all
```

### 调整性能参数
```bash
# 增加批次大小提升速度（需要更多内存）
docker-compose exec backend python import_steam_games.py --all --batch-size 100

# 增加API延迟避免限流（更稳定但更慢）
docker-compose exec backend python import_steam_games.py --all --delay 1.0

# 减少重试次数加快速度（可能失败更多）
docker-compose exec backend python import_steam_games.py --all --retry 2
```

### 组合使用
```bash
# 最快速配置（激进）
docker-compose exec backend python import_steam_games.py --all --batch-size 100 --delay 0.3 --retry 2

# 最稳定配置（保守）
docker-compose exec backend python import_steam_games.py --all --batch-size 30 --delay 1.5 --retry 5
```

---

## 参数说明

| 参数 | 说明 | 默认值 | 推荐范围 |
|------|------|--------|---------|
| `--all` | 导入所有游戏 | - | 推荐使用 |
| `--limit` | 限制导入数量 | 1000 | 100-10000 |
| `--batch-size` | 批次大小 | 50 | 20-100 |
| `--skip` | 跳过前N款游戏 | 0 | 0-100000 |
| `--delay` | API延迟（秒） | 0.5 | 0.3-2.0 |
| `--retry` | 失败重试次数 | 3 | 2-5 |

---

## 进度显示示例

```
======================================================================
Steam游戏数据批量导入工具 v2.0
======================================================================
✓ 数据库已连接: steamgamerec
正在从SteamSpy获取所有游戏列表...
✓ 获取到 98,754 款游戏

Steam游戏总数: 98,754 款
模式: 导入所有游戏
批次大小: 50
API延迟: 0.5秒
重试次数: 3
预计耗时: 14.8 小时

开始导入 (共1,976批次)...
======================================================================

[批次 1/1976] 处理 50 款游戏...
  进度: 20/50 | 成功: 17 | 跳过: 0 | 失败: 3
  进度: 40/50 | 成功: 36 | 跳过: 0 | 失败: 4
[批次 1] 完成 - 成功: 45 | 跳过: 0 | 失败: 5

...

[批次 100/1976] 处理 50 款游戏...
  进度: 20/50 | 成功: 18 | 跳过: 0 | 失败: 2
  进度: 40/50 | 成功: 38 | 跳过: 0 | 失败: 2
[批次 100] 完成 - 成功: 47 | 跳过: 0 | 失败: 3

📊 总体进度: 5000/98754 (5.1%)
   成功: 4523 | 跳过: 0 | 失败: 477
   速度: 2.3 游戏/秒 | 剩余时间: 11.3 小时

...

======================================================================
导入完成!
======================================================================
总计处理: 98,754 款游戏
✓ 成功导入: 94,231
○ 已存在跳过: 0
✗ 失败: 4,523
⏱ 耗时: 782.5 分钟 (46950.3 秒)
⚡ 平均速度: 2.10 游戏/秒
======================================================================
```

---

## 验证导入结果

### 方法1: 通过API查看
```powershell
# 查看游戏数量
Invoke-WebRequest -Uri "http://localhost:8000/games" | Select-Object -ExpandProperty Content | ConvertFrom-Json | Measure-Object

# 查看前5款游戏
Invoke-WebRequest -Uri "http://localhost:8000/games?limit=5" | Select-Object -ExpandProperty Content | ConvertFrom-Json | ConvertTo-Json
```

### 方法2: 通过MongoDB查看
```bash
# 进入MongoDB
docker-compose exec mongodb mongosh steamgamerec

# 查看游戏数量
db.games.countDocuments()

# 查看游戏示例
db.games.find().limit(3).pretty()

# 退出
exit
```

### 方法3: 通过前端查看
访问 http://localhost:3000/wishlist 查看所有游戏。

---

## 清空数据库重新导入

如果需要重新导入：

```bash
# 删除所有游戏数据
docker-compose exec mongodb mongosh steamgamerec --eval "db.games.deleteMany({})"

# 重新导入
docker-compose exec backend python quick_import.py
```

---

## 导入时间参考

| 游戏数量 | 预计时间 | 数据库大小 |
|---------|---------|-----------|
| 100     | 5-10分钟  | ~1 MB     |
| 500     | 10-20分钟 | ~3-5 MB   |
| 1000    | 15-30分钟 | ~5-10 MB  |
| 10000   | 2-5小时   | ~50-100 MB|
| 全部    | 10-20小时 | ~500 MB-1GB|

---

## 故障排除

### "Connection refused"
```bash
# 检查容器状态
docker-compose ps

# 重启服务
docker-compose restart backend mongodb
```

### "HTTP 429 Too Many Requests"
API限流，脚本会自动重试。如果频繁出现，增加延迟：
- 编辑脚本中的 `await asyncio.sleep(0.5)` 改为 `await asyncio.sleep(1.0)`

### 查看导入日志
```bash
# 实时查看日志
docker-compose logs -f backend
```
