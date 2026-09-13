#!/bin/bash
set -e

# 0. 全局换国内源
npm config set registry https://registry.npmmirror.com
npm i -g pnpm
pnpm install
pnpm build

# 3. 把编译结果拷到部署目录
mkdir -p ../quasar-uav-deploy/dist
cp -r dist/spa/* ../quasar-uav-deploy/dist/

# 4. 启动容器
cd ../quasar-uav-master
docker-compose up -d --build

echo "====================================="
echo "Quasar 已部署到 http://<本机IP>"
echo "====================================="
