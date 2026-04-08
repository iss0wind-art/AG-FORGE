FROM python:3.12-slim

WORKDIR /app

# 의존성 먼저 설치 (캐시 레이어 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 복사
COPY . .

# 포트 노출
EXPOSE 8000

# 기동
CMD ["python", "-m", "uvicorn", "server.api:app", \
     "--host", "0.0.0.0", "--port", "8000", "--log-level", "warning"]
