# 后端镜像：python:3.12-slim + 依赖 + 代码
FROM python:3.12-slim

WORKDIR /app

# 先只拷依赖清单再安装：只要 requirements.txt 不变，
# 重新构建时这一层直接走缓存，秒级完成
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再拷业务代码（.dockerignore 已排除 .env / venv / uploads）
COPY . .

# 简历文件目录：生产环境应挂载卷持久化（compose 里已配置）
VOLUME ["/app/uploads"]

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
