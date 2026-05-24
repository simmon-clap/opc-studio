FROM python:3.12-slim

WORKDIR /app

COPY backend/pyproject.toml backend/pyproject.toml
COPY backend/app backend/app
COPY dashboards dashboards
COPY assets assets
COPY mock mock
COPY VERSION VERSION
COPY architecture.html architecture.html

RUN pip install --no-cache-dir -e backend/

ENV PYTHONPATH=/app/backend/app
ENV OPC_HOST=0.0.0.0
ENV OPC_DATA_DIR=/data

RUN mkdir -p /data
VOLUME /data

EXPOSE 8765

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8765}"]
