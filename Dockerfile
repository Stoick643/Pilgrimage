FROM python:3.12-slim

WORKDIR /app

COPY v3/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY v3/ ./v3/

CMD ["uvicorn", "v3.app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
