# ============================================
# SteamGameRecSys Frontend Dockerfile
# ============================================
# 多阶段构建 - 优化生产镜像大小

# Stage 1: Build
FROM node:18-alpine as build

WORKDIR /app

# 复制package文件并安装依赖
COPY package*.json ./
RUN npm install

# 复制源代码并构建
COPY . .
RUN npm run build

# Stage 2: Production
FROM nginx:alpine

# 复制构建产物到nginx
COPY --from=build /app/build /usr/share/nginx/html

# 复制nginx配置 (支持React Router)
RUN echo 'server { \
    listen 80; \
    location / { \
    root /usr/share/nginx/html; \
    index index.html; \
    try_files $uri $uri/ /index.html; \
    } \
    }' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
