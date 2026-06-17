# Deploy do Oriens em produção (VPS Hostinger · Ubuntu 24.04)

Arquitetura mais simples que funciona:

```
Internet ──▶ Nginx (host, :80/:443, TLS) ──▶ App (container, 127.0.0.1:8000) ──▶ PostgreSQL (container)
```

- **Nginx + Certbot** rodam direto no Ubuntu (apt) — mais fácil de depurar, renovação automática.
- **App + PostgreSQL** rodam em containers via `docker-compose.prod.yml`.
- **Anexos** ficam no volume `appdata` (gravados em `/app/data`).

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

## 6. Subir os containers

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps          # db e app devem estar "Up"
docker compose -f docker-compose.prod.yml logs -f app  # "Application startup complete." (Ctrl+C p/ sair)
```

Teste local na VPS:

```bash
curl http://127.0.0.1:8000/health    # {"status":"ok"}
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

# Atualizar após mudanças no código
git pull
docker compose -f docker-compose.prod.yml up -d --build

# Ver logs
docker compose -f docker-compose.prod.yml logs -f app

# Reiniciar / parar
docker compose -f docker-compose.prod.yml restart app
docker compose -f docker-compose.prod.yml down
```

---

## ✅ Checklist final de publicação

- [ ] DNS: `seudominio.com.br` e `www` apontando para o IP da VPS
- [ ] Docker, Nginx e Certbot instalados
- [ ] UFW ativo (SSH + Nginx Full); porta 8000 **não** exposta na internet
- [ ] `.env` criado com `DEBUG=false`, `COOKIE_SECURE=true`, `SECRET_KEY` forte
- [ ] `POSTGRES_PASSWORD` igual à senha em `DATABASE_URL`
- [ ] `docker compose -f docker-compose.prod.yml ps` → `db` e `app` "Up"
- [ ] `curl http://127.0.0.1:8000/health` → `{"status":"ok"}`
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
