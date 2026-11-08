FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STORAGE_DIR=/storage

WORKDIR /app

COPY source_code/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY source_code/ .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--timeout", "300", "rag.web:create_app()"]
