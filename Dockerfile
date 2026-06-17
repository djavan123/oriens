# Dockerfile — imagem de produção do Oriens
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=America/Sao_Paulo

WORKDIR /app

# tzdata: necessário para o fuso (lembretes em hora local)
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 120 --retries 5 -r requirements.txt

COPY . .

EXPOSE 8000

# Produção: sem --reload. 1 worker já atende um app pessoal com folga.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
