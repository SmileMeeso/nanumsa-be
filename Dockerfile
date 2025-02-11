# Base image
FROM python:3.12-slim

# 추가적으로 curl 설치
RUN apt-get update && apt-get install -y curl && apt-get clean

# 작업 디렉토리 설정
WORKDIR /app

# Poetry 설치
RUN pip install poetry

# 애플리케이션 코드 복사
COPY . .

# 의존성 설치
RUN poetry install

# FastAPI 서버 실행
CMD ["poetry", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers"]