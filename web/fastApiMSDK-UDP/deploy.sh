#!/bin/bash
# fastApiMSDK-UDP 一键部署脚本
# ./deploy.sh [local|docker|docker-compose]  缺省 docker-compose
set -e

DEPLOY_TYPE=${1:-docker-compose}
PORT=8000                           # 与 main.py & docker-compose.yml 保持一致

red()   { echo -e "\033[31m$1\033[0m"; }
green() { echo -e "\033[32m$1\033[0m"; }

echo "=== fastApiMSDK-UDP 部署 ==="
echo "类型: $DEPLOY_TYPE | 端口: $PORT"

case $DEPLOY_TYPE in
  local)
    echo "--- 本地虚拟环境部署 ---"
    command -v python3 >/dev/null || { red "错误: python3 未安装"; exit 1; }
    python3 -m venv venv
    source venv/bin/activate
    pip config set global.timeout 60
    pip config set global.retries 10
    pip config set global.index-url https://mirrors.aliyun.com/pypi/simple
    pip config set global.trusted-host mirrors.aliyun.com
    pip install -U pip setuptools wheel
    pip install -r requirements.txt
    green "本地部署完成！启动命令："
    echo "  source venv/bin/activate && python main.py"
    ;;
  docker)
    echo "--- Docker 部署 ---"
    command -v docker >/dev/null || { red "错误: docker 未安装"; exit 1; }
    docker build -t fastapi-msdk-udp:latest .
    docker stop fastapi-msdk-udp >/dev/null 2>&1 || true
    docker rm   fastapi-msdk-udp >/dev/null 2>&1 || true
    docker run -d --name fastapi-msdk-udp \
      -p $PORT:$PORT --restart unless-stopped fastapi-msdk-udp:latest
    green "Docker 部署完成！访问: http://localhost:$PORT"
    ;;
  docker-compose)
    echo "--- Docker Compose 部署 ---"
    if ! (command -v docker-compose >/dev/null || docker compose version >/dev/null 2>&1); then
      red "错误: docker-compose 未安装"; exit 1
    fi
    [ -f docker-compose.yml ] || { red "错误: docker-compose.yml 不存在"; exit 1; }
    docker-compose down 2>/dev/null || true
    docker-compose up -d --build
    green "Docker Compose 部署完成！访问: http://localhost:$PORT"
    echo "查看日志: docker compose logs -f"
    ;;
  *)
    red "错误: 不支持的部署类型 '$DEPLOY_TYPE'"
    echo "支持类型: local | docker | docker-compose"
    exit 1
    ;;
esac

green "=== 部署结束 ==="
