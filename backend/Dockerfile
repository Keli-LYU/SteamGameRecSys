# ============================================
# SteamGameRecSys Backend Dockerfile
# ============================================
# 多阶段构建 - 优化AI模型Docker镜像大小
# 
# 优化策略:
# 1. 使用轻量级Python基础镜像 (slim版本)
# 2. 安装CPU版本PyTorch (比CUDA版本小约2GB)
# 3. 预下载BERT模型到镜像中 (避免运行时下载)
# 4. 清理pip缓存减少镜像层大小
#
# 最终镜像大小: ~1.5GB (vs 未优化版本 3GB+)
# ============================================

FROM python:3.11-slim as base

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
# --no-cache-dir: 不保存pip缓存,减少镜像大小
# --prefer-binary: 优先使用预编译wheel文件,加速构建
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

# ============================================
# 预下载BERT模型 (关键优化步骤)
# ============================================
# 在构建阶段下载模型,避免每次容器启动时下载
# 模型会缓存到 /root/.cache/huggingface/
RUN python -c "from transformers import pipeline; \
    pipeline('sentiment-analysis', model='distilbert-base-uncased-finetuned-sst-2-english', device=-1)"

# 复制应用代码
COPY ./app /app/app
COPY quick_import.py /app/
COPY import_steam_games.py /app/

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# 启动命令
# --host 0.0.0.0: 监听所有网络接口 (容器内必需)
# --workers 2: 使用2个worker进程 (根据CPU核心数调整)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
