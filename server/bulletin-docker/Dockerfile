# 使用官方的 Python 3.11 轻量镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 先复制依赖文件，利用 Docker 缓存层
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制所有项目文件
COPY server.py .
COPY templates/ ./templates/

# 创建用于存放数据库的目录
RUN mkdir /app/data

# 声明数据卷（数据库文件会放在这里）
VOLUME /app/data

# 暴露服务端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]