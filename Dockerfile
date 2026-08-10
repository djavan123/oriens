# Dockerfile — imagem de produção do Oriens

# ── Estágio 1: CSS ──────────────────────────────────────────────────────────
# O Tailwind roda AQUI, no build, e some da imagem final. Antes ele ia junto
# para o navegador (static/vendor/tailwind.js, 407 KB) e compilava a folha de
# estilo a cada carga de página. Só o .css gerado é copiado adiante.
FROM node:22-alpine AS css
WORKDIR /build
COPY package.json package-lock.json tailwind.config.js ./
RUN npm ci --omit=optional
COPY app/templates ./app/templates
COPY app/static/css/tailwind.src.css ./app/static/css/tailwind.src.css
RUN npm run build:css

# ── Estágio 2: aplicação ────────────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=America/Sao_Paulo \
    WEB_CONCURRENCY=3

WORKDIR /app

# tzdata: necessário para o fuso (lembretes em hora local)
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 120 --retries 5 -r requirements.txt

COPY . .

# O CSS gerado no estágio anterior sobrescreve o que veio do repo — assim a
# imagem nunca sai com um tailwind.css desatualizado em relação aos templates.
COPY --from=css /build/app/static/css/tailwind.css ./app/static/css/tailwind.css

# Versão do build (cache-busting de estáticos/PWA). O compose de prod injeta o git SHA.
ARG APP_VERSION=prod
ENV APP_VERSION=$APP_VERSION

EXPOSE 8000

# Produção: gunicorn com workers Uvicorn (multi-worker). Os loops de fundo NÃO
# rodam aqui — ficam no serviço `worker` (python -m app.worker). Nº de workers vem
# de WEB_CONCURRENCY (lido nativamente pelo gunicorn quando -w não é passado) —
# ajustável no compose sem rebuild (regra prática: 2×núcleos+1). Ao mudar,
# redimensione DB_POOL_SIZE/DB_MAX_OVERFLOW para não estourar o max_connections do PG.
CMD ["gunicorn", "app.main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8000", \
     "--timeout", "60", \
     "--access-logfile", "-"]
