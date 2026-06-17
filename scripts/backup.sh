#!/usr/bin/env bash
# scripts/backup.sh — backup do Oriens (PostgreSQL + anexos)
# Uso:   bash scripts/backup.sh
# Cron:  0 3 * * *  cd /opt/oriens && bash scripts/backup.sh >> /var/log/oriens-backup.log 2>&1
set -euo pipefail

# Diretório do projeto (onde está o docker-compose.prod.yml)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

COMPOSE="docker compose -f docker-compose.prod.yml"
BACKUP_DIR="$PROJECT_DIR/backups"
RETENTION_DAYS=7
STAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$BACKUP_DIR"

# 1) Banco PostgreSQL (dump comprimido)
$COMPOSE exec -T db pg_dump -U oriens oriens | gzip > "$BACKUP_DIR/oriens_db_$STAMP.sql.gz"

# 2) Anexos (volume montado em /app/data dentro do container app)
$COMPOSE exec -T app tar czf - -C /app/data . > "$BACKUP_DIR/oriens_data_$STAMP.tar.gz"

# 3) Retenção: remove backups com mais de RETENTION_DAYS dias
find "$BACKUP_DIR" -name 'oriens_*.gz' -mtime +$RETENTION_DAYS -delete

echo "[$(date '+%F %T')] Backup OK -> $BACKUP_DIR (db + anexos), retenção ${RETENTION_DAYS}d"
