# Deploy do Oriens em produção (VPS Hostinger · Ubuntu 24.04)

Arquitetura mais simples que funciona:

```
Internet ──▶ Nginx (host, :80/:443, TLS) ──▶ App (container, gunicorn multi-worker, 127.0.0.1:8000) ──▶ PostgreSQL (container)
                                          └─▶ estáticos servidos direto pelo Nginx (/static/)
                              Worker (container, sem porta) ──▶ PostgreSQL (mesmo banco)
```

- **Nginx + Certbot** rodam direto no Ubuntu (apt) — mais fácil de depurar, renovação automática.
- **App + PostgreSQL + Worker** rodam em containers via `docker-compose.prod.yml`.
- **App (web)** roda com `gunicorn -k uvicorn.workers.UvicornWorker -w 3` (multi-worker desde a auditoria de produção — antes era um único processo `uvicorn`).
- **Worker** é um processo **único e separado** (`app/worker.py`) que cuida dos lembretes e da captura por Telegram. Não deve ser escalado (>1 réplica duplicaria envios/updates).
- **Anexos** ficam no volume `appdata` (gravados em `/app/data`).
- **Front sem CDN:** Tailwind/HTMX/Alpine/SortableJS e a fonte Inter são auto-hospedados em `app/static/vendor/` — nenhuma dependência de rede externa para o app carregar.

---

## Nginx (estado atual: NO HOST, acesso por IP)

A VPS roda nginx **no host** (`/etc/nginx/sites-enabled/oriens`) com a config
**`nginx/oriens-ip.conf`** (rate-limit no `/auth/login`, gzip, headers de segurança e
`/static/` servido direto de `/opt/oriens/app/static/` com cache 30d — seguro porque
as URLs de asset carregam `?v=APP_VERSION`). Atualizar a config:

```bash
cp /opt/oriens/nginx/oriens-ip.conf /etc/nginx/sites-available/oriens
nginx -t && systemctl reload nginx
```

> **Deploy recomendado** (injeta o git SHA para cache-busting dos estáticos/PWA):
> ```bash
> git pull && APP_VERSION=$(git rev-parse --short HEAD) docker compose -f docker-compose.prod.yml up -d --build
> ```
> Sem `APP_VERSION`, o build usa `prod` fixo — funciona, mas navegadores/PWA podem
> servir CSS/JS antigos até o cache expirar.

O compose também traz um serviço `nginx` em container (`nginx/oriens-docker.conf`),
**opt-in** via profile — só para ambientes SEM nginx no host:
`docker compose -f docker-compose.prod.yml --profile nginx up -d`.

**Fechar o acesso direto (depois de validar `http://IP/`):** em
`docker-compose.prod.yml`, troque a porta do serviço `app` de `"8000:8000"` para
`"127.0.0.1:8000:8000"` e suba de novo — todo o tráfego passa a ir pelo nginx
(rate-limit/gzip valem de verdade).

> Quando houver domínio + HTTPS, migre para `nginx/oriens.conf` (server_name real)
> + certbot, conforme o guia original abaixo.

## Migrações pesadas antes do deploy (opcional)

O `init_db()` roda no boot com `lock_timeout=5s` / `statement_timeout=120s` (PG):
uma migração que não conseguir lock falha rápido e o `restart: always` re-tenta —
melhor do que congelar o site. Para migrações potencialmente demoradas (ex.: um
futuro `ALTER` que reescreva uma tabela grande), rode ANTES de trocar os containers:

```bash
docker compose -f docker-compose.prod.yml run --rm app python scripts/run_migrations.py
```

Assim o boot dos containers novos vira uma passada rápida por guards idempotentes.

---

## 0. Pré-requisitos

- VPS Hostinger com Ubuntu 24.04 e acesso `root` (ou usuário com `sudo`).
- Um domínio. No painel DNS, crie 2 registros **A** apontando para o IP da VPS:
  - `seudominio.com.br`     → `IP_DA_VPS`
  - `www.seudominio.com.br` → `IP_DA_VPS`
- Aguarde o DNS propagar (pode levar de minutos a algumas horas).

> Em todos os passos abaixo, troque `seudominio.com.br` pelo seu domínio real.

---

## 1. Acessar a VPS e atualizar o sistema

```bash
ssh root@IP_DA_VPS
apt update && apt upgrade -y
```

## 2. Instalar Docker + Nginx + Certbot

```bash
# Docker (script oficial)
curl -fsSL https://get.docker.com | sh

# Nginx e Certbot (plugin nginx)
apt install -y nginx certbot python3-certbot-nginx git
```

## 3. Firewall (UFW)

```bash
ufw allow OpenSSH
ufw allow 'Nginx Full'   # libera 80 e 443
ufw --force enable
```

> A porta 8000 **não** é liberada na internet — o app só escuta em `127.0.0.1`.

## 4. Obter o código

```bash
mkdir -p /opt/oriens && cd /opt/oriens
# Opção A: git
git clone SEU_REPOSITORIO .
# Opção B: copie os arquivos via scp/SFTP para /opt/oriens
```

## 5. Criar o arquivo `.env` de produção

```bash
cd /opt/oriens
cp .env.example .env
# Gere uma SECRET_KEY forte:
openssl rand -hex 32
nano .env
```

Preencha no `.env` (a senha do Postgres deve ser a **mesma** nos dois lugares):

```env
DATABASE_URL=postgresql+asyncpg://oriens:SENHA_FORTE@db:5432/oriens
POSTGRES_PASSWORD=SENHA_FORTE
SECRET_KEY=<cole o resultado do openssl>
DEBUG=false
COOKIE_SECURE=true
AI_ENABLED=false
AI_PROVIDER=null
```

> ⚠️ **Importante:** com `DEBUG=false`, o app **se recusa a subir** se `SECRET_KEY` ainda for o
> valor padrão do repositório (`troque-isso-em-producao`) — é um guard proposital contra subir em
> produção com uma chave JWT forjável. Se o container `app` reiniciar em loop logo após o deploy,
> confira `docker compose -f docker-compose.prod.yml logs app` primeiro por essa causa.

## 6. Subir os containers

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps               # db, app e worker devem estar "Up" (app "healthy")
docker compose -f docker-compose.prod.yml logs -f app worker  # "Application startup complete." / "Worker Oriens iniciado" (Ctrl+C p/ sair)
```

O serviço `app` roda com **gunicorn + 3 workers Uvicorn** (escala melhor que um único processo). O serviço `worker` é um processo único e separado que cuida dos lembretes e da captura por Telegram — **não escale esse serviço** (mais de 1 réplica duplicaria envios/updates).

Teste local na VPS:

```bash
curl http://127.0.0.1:8000/health    # {"status":"ok"} — inclui um SELECT 1 no banco
```

## 7. Configurar o Nginx (proxy reverso)

```bash
cp /opt/oriens/nginx/oriens.conf /etc/nginx/sites-available/oriens
# edite o server_name com seu domínio:
nano /etc/nginx/sites-available/oriens

ln -s /etc/nginx/sites-available/oriens /etc/nginx/sites-enabled/oriens
rm -f /etc/nginx/sites-enabled/default   # remove o site padrão
nginx -t                                  # testa a config
systemctl reload nginx
```

Agora `http://seudominio.com.br` já deve abrir o Oriens.

> **`nginx/oriens.conf` já vem com:**
> - `location /static/` servindo os arquivos direto do disco (`alias /opt/oriens/app/static/`) —
>   ajuste o caminho no arquivo se seu repo não estiver em `/opt/oriens`.
> - `limit_req` no `/auth/login` (5 requisições/min por IP) — proteção básica contra
>   credential-stuffing, robusta mesmo com o app rodando vários workers gunicorn.

## 8. Ativar HTTPS (Let's Encrypt)

```bash
certbot --nginx -d seudominio.com.br -d www.seudominio.com.br
```

- Informe um e-mail, aceite os termos.
- Quando perguntar, escolha **redirecionar HTTP → HTTPS**.
- O Certbot edita o Nginx e instala o certificado automaticamente.

Renovação automática já vem configurada (timer do systemd). Teste:

```bash
certbot renew --dry-run
```

## 9. Primeiro acesso

Abra `https://seudominio.com.br` → você cai em `/auth/setup` para criar o primeiro usuário.
Pronto. Acesse pelo computador e pelo celular.

---

## 10. Instalar no celular (PWA)

- **Android (Chrome):** abra o site → menu (⋮) → **Instalar app** / **Adicionar à tela inicial**.
- **iPhone (Safari):** abra o site → botão **Compartilhar** → **Adicionar à Tela de Início**.

O app abre em tela cheia, com ícone próprio, como um aplicativo nativo.

> A instalação como PWA exige **HTTPS** (passo 8). Sem TLS o navegador não oferece a opção.

---

## 11. Backup do PostgreSQL (+ anexos)

O script `scripts/backup.sh` gera, em `/opt/oriens/backups/`:
- dump comprimido do banco (`oriens_db_*.sql.gz`);
- tarball dos anexos (`oriens_data_*.tar.gz`);
- mantém os últimos **7 dias** (apaga mais antigos).

Rodar manualmente:

```bash
cd /opt/oriens
bash scripts/backup.sh
```

Agendar diariamente às 03:00 (cron do root):

```bash
crontab -e
# adicione a linha:
0 3 * * * cd /opt/oriens && bash scripts/backup.sh >> /var/log/oriens-backup.log 2>&1
```

**Restaurar o banco** a partir de um dump:

```bash
cd /opt/oriens
gunzip -c backups/oriens_db_AAAAMMDD_HHMMSS.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T db psql -U oriens -d oriens
```

**Restaurar anexos:**

```bash
docker compose -f docker-compose.prod.yml exec -T app \
  tar xzf - -C /app/data < backups/oriens_data_AAAAMMDD_HHMMSS.tar.gz
```

> Recomendado: de tempos em tempos, baixe os arquivos de `backups/` para fora da VPS
> (seu computador ou um drive na nuvem) com `scp`. É a forma mais simples de ter cópia off-site.

---

## 12. Migrar dados do SQLite (opcional)

Para um primeiro deploy, o mais simples é **começar do zero** (refazer o `/setup`).

Se você já tem dados no SQLite local e quer preservá-los, veja
`scripts/migrate_to_postgres.py` (instruções no cabeçalho do arquivo).

---

## 13. Operação do dia a dia

```bash
cd /opt/oriens

# ANTES de atualizar: guarde o commit atual para rollback rápido
git rev-parse HEAD | tee .last_good_commit

# Atualizar após mudanças no código
git pull
docker compose -f docker-compose.prod.yml up -d --build

# Ver status e logs (agora com o serviço `worker` além de `db`/`app`)
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f app worker

# Reiniciar / parar
docker compose -f docker-compose.prod.yml restart app worker
docker compose -f docker-compose.prod.yml down
```

---

## 14. Rollback rápido

A migração de schema é **aditiva e idempotente** (colunas/índices novos via `ADD COLUMN IF NOT
EXISTS` / `CREATE INDEX IF NOT EXISTS`, protegida por `pg_advisory_xact_lock`), então voltar para
um commit anterior é seguro — o banco já migrado continua funcionando com o código antigo.

```bash
cd /opt/oriens
git checkout "$(cat .last_good_commit)"     # volta ao código anterior (HEAD destacado)
docker compose -f docker-compose.prod.yml up -d --build --remove-orphans
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f app
```

- `--remove-orphans` remove o container `worker` se você voltar a uma versão do código anterior à
  auditoria de produção (que não tinha esse serviço) — o web volta a rodar os loops de lembrete
  internamente, como antes.
- **Continue sem `down -v`** — os volumes `pgdata`/`appdata` permanecem intactos.
- Para voltar à versão nova depois: `git checkout main && git pull && docker compose -f docker-compose.prod.yml up -d --build`.

**Causa nº 1 de falha no boot** (não precisa nem de rollback, é mais rápido corrigir o `.env`):
se `DEBUG=false` e `SECRET_KEY` ainda for o valor padrão do repositório, o app aborta o boot de
propósito. Sintoma: container `app` reiniciando em loop. Correção:
```bash
cd /opt/oriens
sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$(openssl rand -hex 32)/" .env
docker compose -f docker-compose.prod.yml up -d
```

---

## ✅ Checklist final de publicação

- [ ] DNS: `seudominio.com.br` e `www` apontando para o IP da VPS
- [ ] Docker, Nginx e Certbot instalados
- [ ] UFW ativo (SSH + Nginx Full); porta 8000 **não** exposta na internet
- [ ] `.env` criado com `DEBUG=false`, `COOKIE_SECURE=true`, `SECRET_KEY` forte
- [ ] `POSTGRES_PASSWORD` igual à senha em `DATABASE_URL`
- [ ] `docker compose -f docker-compose.prod.yml ps` → `db`, `app` (healthy) e `worker` "Up"
- [ ] `curl http://127.0.0.1:8000/health` → `{"status":"ok"}` (agora com ping no banco)
- [ ] Logs do `worker` mostram "Worker Oriens iniciado" sem erros
- [ ] Nginx com `server_name` correto, `nginx -t` OK, default removido
- [ ] HTTPS ativo (`certbot --nginx`) e redirecionando HTTP → HTTPS
- [ ] `certbot renew --dry-run` sem erros
- [ ] Primeiro usuário criado em `/auth/setup`
- [ ] Login funciona no computador e no celular
- [ ] PWA instalável no celular (ícone na tela inicial, abre em tela cheia)
- [ ] Upload e download de anexo funcionando
- [ ] Backup: `bash scripts/backup.sh` gera arquivos em `backups/`
- [ ] Cron de backup agendado (03:00)
- [ ] Backup copiado para fora da VPS pelo menos uma vez
