# fastApiMSDK-UDP 部署指南

## 项目概述

fastApiMSDK-UDP 是一个基于 FastAPI 的无人机控制系统，集成了：
- **HTTP API 服务** (端口 8081)
- **UDP 服务器** (端口 8081) 
- **WebSocket 通信**
- **Web 控制面板**

## 系统要求

### 最低要求
- **操作系统**: Linux/macOS/Windows
- **Python**: 3.8+ (本地部署)
- **Docker**: 20.10+ (容器部署)
- **内存**: 512MB+
- **磁盘**: 1GB+

### 网络要求
- **HTTP 端口**: 8081/tcp
- **UDP 端口**: 8081/udp
- 确保防火墙允许这些端口的访问

## 部署方式

### 1. 快速部署 (推荐)

使用提供的部署脚本：

```bash
# Docker Compose 部署 (推荐)
./deploy.sh docker-compose

# Docker 部署
./deploy.sh docker

# 本地部署
./deploy.sh local
```

### 2. 手动部署

#### 2.1 本地部署

```bash
# 1. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows

# 2. 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 3. 启动应用
python main.py
```

**优点**: 开发友好，易于调试  
**缺点**: 环境配置复杂，不适合生产

#### 2.2 Docker 部署

```bash
# 1. 构建镜像
docker build -t fastapi-msdk-udp:latest .

# 2. 运行容器
docker run -d \
  --name fastapi-msdk-udp \
  -p 8081:8081/tcp \
  -p 8081:8081/udp \
  --restart unless-stopped \
  fastapi-msdk-udp:latest
```

**优点**: 环境隔离，部署简单  
**缺点**: 需要手动管理容器

#### 2.3 Docker Compose 部署 (推荐)

```bash
# 1. 启动服务
docker-compose up -d --build

# 2. 查看状态
docker-compose ps

# 3. 查看日志
docker-compose logs -f

# 4. 停止服务
docker-compose down
```

**优点**: 自动化程度高，生产就绪  
**缺点**: 需要了解 Docker Compose

### 3. 云部署

#### 3.1 准备工作
- 云服务器 (阿里云、腾讯云等)
- 安装 Docker 和 Docker Compose
- 配置安全组，开放 8081 端口

#### 3.2 部署步骤
```bash
# 1. 上传代码到服务器
scp -r fastApiMSDK-UDP user@server:/opt/

# 2. 登录服务器
ssh user@server

# 3. 进入项目目录
cd /opt/fastApiMSDK-UDP

# 4. 执行部署
./deploy.sh docker-compose
```

## 验证部署

### 1. 健康检查
```bash
# 检查 HTTP 服务
curl http://localhost:8081/

# 检查服务状态 (Docker)
docker ps | grep fastapi-msdk-udp

# 检查日志 (Docker Compose)
docker-compose logs -f
```

### 2. 功能测试
- **Web 界面**: http://localhost:8081
- **API 文档**: http://localhost:8081/docs
- **客户端列表**: http://localhost:8081/api/clients

## 常见问题

### 1. 端口冲突
```bash
# 查看端口占用
netstat -tulpn | grep 8081

# 修改端口 (编辑 main.py)
uvicorn.run("main:app", host="0.0.0.0", port=8082, reload=True)
```

### 2. UDP 通信问题
- 检查防火墙设置
- 确保 UDP 端口未被占用
- 验证客户端连接地址

### 3. Docker 问题
```bash
# 重新构建镜像
docker-compose build --no-cache

# 清理 Docker 资源
docker system prune -a
```

## 性能优化

### 1. 生产环境配置
```bash
# 使用 Gunicorn (创建 gunicorn.conf.py)
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
bind = "0.0.0.0:8081"
```

### 2. 资源限制 (docker-compose.yml)
```yaml
services:
  fastapi-msdk-udp:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

## 监控和维护

### 1. 日志管理
```bash
# 查看实时日志
docker-compose logs -f --tail=100

# 日志轮转配置
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### 2. 自动重启
Docker Compose 已配置 `restart: unless-stopped`，确保服务自动重启。

## 安全建议

1. **网络安全**
   - 使用防火墙限制访问
   - 配置 HTTPS (生产环境)
   
2. **容器安全**
   - 定期更新基础镜像
   - 使用非 root 用户运行

3. **监控告警**
   - 配置服务监控
   - 设置异常告警

## 技术支持

- **项目文档**: 查看 API_DOCUMENTATION.md
- **日志位置**: 
  - 本地: 控制台输出
  - Docker: `docker-compose logs`
- **配置文件**: 
  - requirements.txt (依赖)
  - environment.yml (Conda 环境)
