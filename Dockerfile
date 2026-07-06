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

# Produção: gunicorn com workers Uvicorn (multi-worker). Os loops de fundo NÃO
# rodam aqui — ficam no serviço `worker` (python -m app.worker). Ajuste -w conforme
# CPU da VPS (regra prática: 2×núcleos+1). Timeout maior tolera requisições lentas.
CMD ["gunicorn", "app.main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-w", "3", \
     "-b", "0.0.0.0:8000", \
     "--timeout", "60", \
     "--access-logfile", "-"]
