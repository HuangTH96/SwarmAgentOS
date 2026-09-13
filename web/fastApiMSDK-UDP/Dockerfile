# 使用官方 Python 运行时作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 换国内源 & 加长超时，防止大包半途中断
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple && \
    pip config set global.trusted-host mirrors.aliyun.com && \
    pip config set global.timeout 120 && \
    pip config set global.retries 10 && \
    pip install --no-cache-dir --upgrade pip setuptools wheel

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖（移除 --no-cache-dir 以利用缓存）
RUN pip install -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口 (HTTP 和 UDP 都使用 8081)
EXPOSE 8081/tcp
EXPOSE 8081/udp

# 启动命令
CMD ["python", "main.py"]

