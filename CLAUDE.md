# CLAUDE.md — Oriens

Este arquivo é lido automaticamente pelo Claude Code a cada sessão.
Não apagar. Não mover. Atualizar conforme o projeto evolui.

---

## PAPEL

Você é um Senior Python Engineer construindo comigo o **Oriens** — sistema GTD pessoal.

Construa incrementalmente, uma fase por vez. Após cada fase, pare e aguarde minha confirmação antes de avançar.

---

## REGRAS DE OPERAÇÃO

- Gere código completo e funcional. Sem pseudocódigo, sem `# TODO`, sem `# implementar aqui`.
- Todo arquivo gerado deve ter o caminho completo no cabeçalho como comentário.
- Se houver mais de uma forma válida de implementar algo, escolha a mais simples e justifique em uma linha.
- Não explique o que vai fazer. Faça. Se precisar de contexto, pergunte antes de gerar.
- Após cada fase: liste o que foi entregue, o que falta, e qual é o próximo passo.
- Use o terminal para rodar comandos quando necessário (`pip install`, `docker`).

---

## FILTRO DE DECISÃO TÉCNICA

Toda escolha deve responder: *"isso torna o sistema mais simples ou mais difícil de manter?"*
Se a resposta for "mais difícil", a escolha está errada.

---

## STACK (NÃO NEGOCIÁVEL)

| Camada | Tecnologia | Versão |
|---|---|---|
| Backend | Python | 3.12+ |
| Framework | FastAPI | 0.115.0 |
| Servidor | Uvicorn | 0.30.6 |
| ORM | SQLAlchemy | 2.0.35 |
| Frontend JS | HTMX | 1.9.12 (CDN) |
| Frontend JS | Alpine.js | 3.14.1 (CDN) |
| CSS | TailwindCSS | CDN |
| Templates | Jinja2 | 3.1.4 |
| Auth | PyJWT + bcrypt | 2.9.0 + 4.2.0 |
| Banco | SQLite (dev) / PostgreSQL (prod) | aiosqlite 0.20 / asyncpg 0.29 |
| Testes | pytest + pytest-asyncio | 8.3.3 + 0.24.0 |
| IA (opcional) | Anthropic / OpenAI | ≥0.40.0 / ≥1.50.0 |
| Deploy | Docker Compose (prod) | VPS Ubuntu 24.04 |

> **Banco único, dois ambientes:** o mesmo código roda em **SQLite no dev** e **PostgreSQL na produção**, controlado só pela `DATABASE_URL`.
> **Migrations:** gerenciadas via `database.py` → `init_db()` com `Base.metadata.create_all` + `_ensure_columns()` (ALTER TABLE por coluna) + `_migrate_data()` (seed e migrações de dados). **`_ensure_columns()` e `_migrate_data()` rodam apenas em SQLite** (guard por `conn.dialect.name`). Para **migrações aditivas em PostgreSQL** (prod já no ar), use `_ensure_columns_postgres()` — `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` (idempotente) no dict `_ENSURE_COLUMNS_PG`. `init_db()` roda **sempre** no startup (lifespan), inclusive com `DEBUG=false`. **Alembic não está em uso ativo.**

---

## ESTRUTURA DE PASTAS (ESTADO ATUAL — PÓS SCRIPT 3 + DEPLOY)

```
C:\Projetos\Sistema tarefas\
├── app/
│   ├── __init__.py
│   ├── main.py                        # FastAPI app, routers, lifespan (init_db sempre) + loop de lembretes (SCRIPT 4)
│   ├── config.py                      # Pydantic Settings (DATABASE_URL, SECRET_KEY, AI_*, COOKIE_SECURE, TELEGRAM_*)
│   ├── database.py                    # init_db(); _ensure_columns/_migrate_data (SQLite) + _ensure_columns_postgres (PG)
│   ├── templates_env.py               # Jinja2 env global (função `now`, `fmt_size`)
│   ├── models/
│   │   ├── __init__.py                # Exporta todos os models (+ Label)
│   │   ├── user.py
│   │   ├── project.py                 # + proxima_acao, premissas, responsavel_id; status: nao_iniciado/em_andamento/concluido
│   │   ├── task.py                    # EnergyLevel aqui; + responsavel_id; + tags
│   │   ├── note.py
│   │   ├── capture.py
│   │   ├── context.py                 # type → String(50) nullable; + user_id (contextos dinâmicos)
│   │   ├── weekly_directive.py
│   │   ├── project_comment.py
│   │   ├── project_attachment.py      # anexos em DISCO: /app/data/attachments/{project_id}/
│   │   ├── project_milestone.py
│   │   ├── project_risk.py
│   │   ├── project_audit.py
│   │   ├── project_timeline.py        # TimelineEventType enum + ProjectTimeline model
│   │   └── label.py                   # Label (etiquetas por usuário) — SCRIPT 3
│   ├── schemas/
│   ├── repositories/
│   │   ├── ... (user, project, task, note, capture, weekly, comment, attachment, milestone, risk, audit, timeline)
│   │   ├── context_repo.py            # + get_all_by_user/get_by_id/create/delete (SCRIPT 3)
│   │   └── label_repo.py              # CRUD de etiquetas — SCRIPT 3
│   ├── services/
│   │   ├── project_service.py         # audit trail + timeline (project_created, status_changed)
│   │   ├── task_service.py            # verb validation, priority_score + timeline (task_created, task_done)
│   │   ├── capture_service.py         # process_as_task/project/note/discard
│   │   ├── dashboard_service.py       # DashboardData: tasks + weekly_theme
│   │   ├── weekly_directive_service.py
│   │   ├── ai_service.py              # Protocol + ClaudeProvider + OpenAIProvider + NullProvider
│   │   └── reminder_service.py        # lembretes: send_telegram, process_due_telegram, get_due_popups — SCRIPT 4
│   ├── routes/
│   │   ├── auth.py                    # cookies com secure=COOKIE_SECURE
│   │   ├── dashboard.py               # usa resolve_active_context()
│   │   ├── projects.py                # usa resolve_active_context()
│   │   ├── capture.py                 # usa resolve_active_context()
│   │   ├── weekly.py                  # usa resolve_active_context()
│   │   ├── settings.py               # GET /settings (etiquetas + contextos) — SCRIPT 3
│   │   └── api/
│   │       ├── tasks.py               # aceita responsavel_id, context_id, tags
│   │       ├── projects.py            # aceita responsavel_id; anexos em disco
│   │       ├── capture.py
│   │       ├── ai.py
│   │       ├── context.py             # cookie agora guarda context_id (int) — SCRIPT 3
│   │       ├── settings.py            # CRUD etiquetas + contextos — SCRIPT 3
│   │       └── reminders.py           # GET /due (popup) + POST /{id}/ack — SCRIPT 4
│   ├── templates/
│   │   ├── base.html                  # tokens oriens-*, Inter, Tailwind, HTMX, Alpine + PWA (manifest, SW)
│   │   ├── base_app.html              # sidebar RESPONSIVA (hambúrguer no mobile) + contextos dinâmicos
│   │   ├── dashboard.html             # grid-cols-1 md:grid-cols-2 (responsivo)
│   │   ├── capture.html
│   │   ├── process.html
│   │   ├── weekly.html
│   │   ├── settings.html              # etiquetas + contextos (SCRIPT 3)
│   │   ├── auth/ (login.html, setup.html)
│   │   ├── projects/
│   │   │   ├── list.html              # kanban grid-cols-1 md:grid-cols-3 (responsivo)
│   │   │   ├── detail.html            # responsivo + "Atividade Recente" + modal histórico; contexto obrigatório — SCRIPT 4
│   │   │   └── reports.html
│   │   └── partials/
│   │       ├── task_item.html         # badge de contexto, etiquetas e 🔔 lembrete
│   │       ├── task_form.html         # CRIAÇÃO só com título (SCRIPT 4)
│   │       ├── task_edit_form.html    # energia/prazo/resp/etiquetas/quick win/lembrete; contexto travado se for de projeto
│   │       ├── reminder_popup.html    # toasts de lembrete (SCRIPT 4)
│   │       └── ... (subtasks, project_card/form/comment/attachment/milestone/risk, capture, process, ai_result)
│   ├── static/                        # PWA: manifest.webmanifest, sw.js, icon.svg
│   └── utils/
│       ├── auth.py                    # cookie: oriens_token
│       ├── verb_validator.py
│       ├── overload_detector.py       # score = (proj*2) + tasks
│       └── context_utils.py           # resolve_active_context() — SCRIPT 3
├── tests/
├── data/                              # SQLite (dev) + anexos (/app/data/attachments)
├── scripts/
│   ├── backup.sh                      # pg_dump + anexos (.tar.gz), retenção 7 dias
│   └── migrate_to_postgres.py         # cópia SQLite → PostgreSQL (opcional) — exige PYTHONPATH=/app
├── nginx/
│   └── oriens.conf                    # proxy reverso (uso futuro com domínio)
├── docker-compose.yml                 # DEV (SQLite + --reload + TZ)
├── docker-compose.prod.yml            # PROD (app + PostgreSQL + volumes pgdata/appdata + TZ)
├── Dockerfile                         # produção (sem --reload; instala tzdata, TZ=America/Sao_Paulo)
├── .dockerignore  /  .gitignore
├── .env  /  .env.example              # .env.example tem blocos DEV e PROD
├── DEPLOY.md                          # guia completo (domínio + HTTPS + Nginx + backup)
├── requirements.txt                   # + asyncpg
└── README.md
```

---

## BANCO DE DADOS (ESTADO ATUAL — PÓS SCRIPT 3)

**users:** `id, email (unique), password (bcrypt), name, created_at`

**projects:** `id, user_id, responsavel_id (nullable, FK users), context_id (nullable), name, objective, status, priority (1-3), deadline, notes, done_at, scope, tags, strategic (bool), quarter, owner, strategic_priority, proxima_acao (text), premissas (text), created_at, updated_at`
- status: `nao_iniciado | em_andamento | concluido`
- Todo projeto novo nasce com `nao_iniciado`

**tasks:** `id, user_id, responsavel_id (nullable, FK users), project_id (nullable), parent_id (nullable, self-ref), context_id (nullable), title, status, energy, is_quick_win (bool), cognitive_load, financial_impact, operational_risk, strategic_impact, task_urgency, effort, priority_score (indexed), archived (bool), deadline, tags (text), remind_at (datetime, nullable), reminder_telegram_sent (bool), reminder_acked (bool), created_at, done_at`
- status: `pending | done | blocked`
- energy: `high | medium | low` (EnergyLevel enum em `task.py`)
- `tags`: etiquetas separadas por vírgula (SCRIPT 3)
- `context_id` NULL = tarefa "Independente (todos os contextos)" — aparece em qualquer contexto

**labels:** `id, user_id (FK cascade), name, color (hex, nullable)`  *(SCRIPT 3)*
- Etiquetas predefinidas pelo usuário, gerenciadas em `/settings`

**project_timeline:** `id, project_id (FK cascade), user_id (FK cascade), event_type (string), description (string), created_at (indexed)`
- event_type: `project_created | status_changed | task_created | task_done`
- Seed automático em `_migrate_data()`: todos os projetos existentes recebem evento `project_created`
- `get_last_activity()` em `project_repo` lê daqui (fallback: `project.updated_at`)

**capture_inbox:** `id, user_id, content, processed (bool), created_at`

**notes:** `id, user_id, project_id (nullable), content, created_at`

**contexts:** `id, name, type (String(50) nullable), user_id (nullable, FK users)`  *(alterado no SCRIPT 3)*
- 4 contextos padrão (`user_id = NULL`): type `work | home_recovery | home_operational | gym`
- Contextos do usuário (`user_id` preenchido): criados/excluídos em `/settings`
- `type` deixou de ser enum fixo → string livre (preserva os padrões e permite contextos dinâmicos)

**weekly_directives:** `id, user_id, week_start (date), weekly_theme, top_1, top_2, top_3, ignore_list, major_risk, physiological_priority, created_at, updated_at`

**project_comments, project_attachments, project_milestones, project_risks, project_audit:** sem alterações.

---

## REGRAS DE NEGÓCIO

1. **Título de tarefa:** deve começar com verbo (PT ou EN). Validar em `task_service.py` → lança `TaskVerbError(title, suggestions)`. Retornar alerta inline via HTMX.
2. **Anti-overload:** score = `(projetos_em_andamento * 2) + tarefas_pendentes`. Threshold = 15. Se score > 15 → modo overload: 3 tarefas + banner de alerta.
3. **Captura sem fricção:** `POST /api/capture` exige apenas `content`. Zero outros campos obrigatórios.
4. **Energia como filtro:** Dashboard adapta visibilidade por energia da sessão:
   - `low` → modo minimal (só quick wins)
   - `medium` → modo reduced (3 tarefas prioritárias)
   - `high` → modo full (5 tarefas prioritárias)
5. **Priority score de tarefas:** calculado em `task_service._calc_score()` com 5 métricas: financial_impact, operational_risk, strategic_impact, task_urgency, effort.
6. **Auditoria de projetos:** campos auditados: `status, priority, name, deadline, objective, scope, notes`. Cada mudança grava em `project_audit`.
7. **Contexto de trabalho:** cookie `oriens_context` persiste o contexto ativo. Transição work→recovery exibe painel com itens pendentes para captura.
8. **Diretiva semanal:** upsert por `week_start` (segunda-feira). Seção "Projetos sem atualização" exibe projetos `em_andamento` ordenados por última atividade real (mais antigo primeiro).
9. **Última atividade de projeto:** lida de `project_timeline` via `ProjectTimelineRepository.get_last_activity()`. Fallback: `project.updated_at`.
10. **Status de projeto:** nasce `nao_iniciado`. Transições livres entre os 3 estados. "Concluído" define `done_at`.
11. **Cronologia automática:** eventos gravados automaticamente em `project_timeline`:
    - `project_service.create()` → `project_created`
    - `project_service.update()` ao mudar status → `status_changed`
    - `task_service.create()` com project_id → `task_created`
    - `task_service.mark_done()` com project_id → `task_done`
12. **Responsável:** `responsavel_id` (FK → users) em projetos e tarefas. Exibido no detalhe do projeto e no footer dos cards. Select dropdown condicional nos formulários (só aparece quando `users` está no contexto).
13. **Contextos dinâmicos:** deixaram de ser enum fixo. Cookie `oriens_context` agora guarda o **`context_id` (inteiro)**. `resolve_active_context()` (`app/utils/context_utils.py`) é o helper único usado por todas as rotas HTML; retorna `(context_id, active_context_obj, all_contexts)` e ainda lê cookies legados por `type`. A sidebar lista os contextos dinamicamente; a transição "Sair do trabalho" é decidida por `active_context_obj.type == "work"`.
14. **Tarefa independente de contexto:** `context_id = NULL` significa "Independente (todos os contextos)" — a tarefa aparece em qualquer contexto ativo (filtro: `context_id IS NULL OR context_id == ativo`).
15. **Etiquetas (labels):** CRUD em `/settings`. Campo `tasks.tags` (texto, vírgula). No formulário de tarefa, chips das etiquetas do usuário preenchem o campo `tags` (Alpine). Badges de contexto e tags aparecem no `task_item`.
16. **Lembretes de tarefa:** `remind_at` (data+hora, sem recorrência). Dois canais: (a) **Telegram** — loop de fundo em `main.py` (a cada 60s) chama `reminder_service.process_due_telegram()`; só envia se `TELEGRAM_BOT_TOKEN`+`TELEGRAM_CHAT_ID` estiverem no `.env`; marca `reminder_telegram_sent`. (b) **Popup no app** — `base_app.html` faz polling de `GET /api/reminders/due` (60s); `POST /api/reminders/{id}/ack` seta `reminder_acked`. Ao editar o lembrete, ambos os flags são resetados. Hora local depende de `TZ=America/Sao_Paulo`.
17. **Herança de contexto:** toda tarefa criada dentro de um projeto herda `context_id` do projeto (forçado em `api/tasks.create_task`). No `task_edit_form`, o contexto fica **somente leitura** para tarefas de projeto; editável só para tarefas avulsas.
18. **Contexto obrigatório no projeto:** `create_project` e `update_project` exigem `context_id`; o select é `required` e nunca permite valor vazio. Projetos antigos sem contexto devem recebê-lo ao serem editados.
19. **Criação de tarefa só com título** (GTD "capturar primeiro, organizar depois"): o `task_form` pede apenas o título; energia, prazo, responsável, etiquetas, quick win e lembrete são ajustados depois via "editar".

---

## UX — DARK MODE (DESIGN SYSTEM APLICADO)

Paleta Oriens (tokens Tailwind):

```javascript
'oriens-bg':         '#191919',   // base do conteúdo
'oriens-surface':    '#202020',   // cards elevados, colunas
'oriens-card':       '#1a1a1a',   // inset: inputs, badges
'oriens-card-hover': '#262626',
'oriens-border':     '#2a2a2a',   // borda sutil
'oriens-divider':    '#232323',   // divisores de lista
'oriens-primary':    '#e8edf1',   // texto principal
'oriens-secondary':  '#9a9a9a',   // labels de seção
'oriens-muted':      '#767676',   // datas, contadores
'oriens-empty':      '#565656',   // estados vazios
'oriens-accent':     '#5b8def',   // foco/ação/active
'oriens-accent-hover':'#4a7adf',
'oriens-link':       '#6fa8f5',   // links clicáveis
'oriens-btn':        '#5b8def',   // botão primário
'oriens-alert':      '#F87462',
'oriens-success':    '#4BCE97',
'oriens-warning':    '#E2B203',
```

CSS variables:
- `--bg-sidebar: #141414`, `.sidebar { background: #141414 }`
- `.nav-item:hover { background: #202020 }`

Princípios: espaço generoso (`px-12 py-10`), tipografia como hierarquia, zero ícones decorativos, zero `border-dashed`, máximo 3 níveis de informação por tela, fonte Inter.

---

## MÓDULO DE IA (IMPLEMENTADO — OPCIONAL)

Ativar com `AI_ENABLED=true` e `AI_PROVIDER=claude|openai` no `.env`.

| Provider | Modelo | Notas |
|---|---|---|
| `NullProvider` | — | Padrão quando AI_ENABLED=false |
| `ClaudeProvider` | claude-sonnet-4-6 | Usa prompt caching efêmero |
| `OpenAIProvider` | gpt-4o-mini | Sem caching |

Rotas: `POST /api/ai/break-task/{task_id}`, `/api/ai/suggest-actions/{project_id}`, `/api/ai/overload-context`

---

## CONFIGURAÇÃO

**.env — DESENVOLVIMENTO (SQLite)**
```env
DATABASE_URL=sqlite+aiosqlite:///./data/oriens.db
SECRET_KEY=troque-isso-em-producao
DEBUG=true
COOKIE_SECURE=false
AI_ENABLED=false
AI_PROVIDER=null
```

**.env — PRODUÇÃO (PostgreSQL)**
```env
DATABASE_URL=postgresql+asyncpg://oriens:SENHA@db:5432/oriens
POSTGRES_PASSWORD=SENHA          # idêntica à senha da DATABASE_URL
SECRET_KEY=<openssl rand -hex 32>
DEBUG=false
COOKIE_SECURE=false              # HTTP por IP. Vira `true` quando houver HTTPS
AI_ENABLED=false
AI_PROVIDER=null
TELEGRAM_BOT_TOKEN=              # opcional — lembretes via Telegram
TELEGRAM_CHAT_ID=               # opcional
```

> **Fuso horário:** containers usam `TZ=America/Sao_Paulo` (Dockerfile instala `tzdata`; compose define `TZ`). Necessário para os lembretes dispararem na hora local.

> ⚠️ **`COOKIE_SECURE`:** com `true`, o navegador só envia o cookie de sessão por HTTPS. Em acesso `http://IP:8000` (sem TLS) **deve ser `false`**, senão o login entra em loop. Só passe para `true` ao colocar domínio + HTTPS.

---

## ENDPOINTS

### Páginas HTML

| Método | Rota | Descrição |
|---|---|---|
| GET | `/` | Redireciona para `/dashboard` |
| GET | `/auth/login` | Página de login |
| POST | `/auth/login` | Autenticar (cookie `oriens_token`, 7 dias) |
| POST | `/auth/logout` | Limpar cookie |
| GET | `/auth/setup` | Criar primeiro usuário |
| POST | `/auth/setup` | Salvar primeiro usuário |
| GET | `/dashboard` | Dashboard (`?energy=high\|medium\|low`) |
| GET | `/projects` | Lista de projetos (kanban) |
| GET | `/projects/reports` | Relatórios |
| GET | `/projects/{id}` | Detalhe do projeto |
| GET | `/capture` | Inbox de captura |
| GET | `/process` | Processar capturas pendentes |
| GET | `/weekly` | Revisão semanal |
| POST | `/weekly` | Salvar diretiva semanal |
| GET | `/settings` | Configurações: etiquetas + contextos (SCRIPT 3) |
| GET | `/api/reminders/due` | Lembretes vencidos do usuário (popup HTMX, polling 60s) |
| POST | `/api/reminders/{id}/ack` | Confirmar/dispensar lembrete (popup) |
| GET | `/health` | Health check JSON |

### API (fragmentos HTMX)

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/tasks` | Criar tarefa (aceita `responsavel_id`) |
| PATCH | `/api/tasks/{id}/done` | Marcar concluída (grava timeline) |
| PATCH | `/api/tasks/{id}/blocked` | Marcar bloqueada |
| PATCH | `/api/tasks/{id}/pending` | Marcar pendente |
| PATCH | `/api/tasks/{id}/archive` | Arquivar |
| GET | `/api/tasks/{id}/edit` | Formulário de edição inline |
| GET | `/api/tasks/{id}/cancel-edit` | Cancelar edição |
| PATCH | `/api/tasks/{id}` | Atualizar tarefa (aceita `responsavel_id`) |
| POST | `/api/projects` | Criar projeto (aceita `responsavel_id`, grava timeline) |
| PATCH | `/api/projects/{id}` | Atualizar projeto (aceita `responsavel_id`, grava timeline) |
| POST | `/api/projects/{id}/comments` | Adicionar comentário |
| DELETE | `/api/projects/{id}/comments/{cid}` | Remover comentário |
| POST | `/api/projects/{id}/attachments` | Upload arquivo |
| GET | `/api/projects/{id}/attachments/{aid}/download` | Download |
| DELETE | `/api/projects/{id}/attachments/{aid}` | Remover arquivo |
| POST | `/api/projects/{id}/milestones` | Criar milestone |
| PATCH | `/api/projects/{id}/milestones/{mid}` | Toggle done |
| DELETE | `/api/projects/{id}/milestones/{mid}` | Remover milestone |
| POST | `/api/projects/{id}/risks` | Criar risco |
| PATCH | `/api/projects/{id}/risks/{rid}` | Atualizar risco |
| DELETE | `/api/projects/{id}/risks/{rid}` | Remover risco |
| POST | `/api/capture` | Adicionar captura |
| POST | `/api/process/{id}` | Processar captura |
| POST | `/api/ai/break-task/{id}` | IA: quebrar tarefa |
| POST | `/api/ai/suggest-actions/{id}` | IA: sugerir ações |
| POST | `/api/ai/overload-context` | IA: análise de overload |
| POST | `/api/context/switch` | Trocar contexto ativo (campo `context_id` inteiro) |
| POST | `/api/context/transition` | Transição + captura pendências (campo `context_id`) |
| POST | `/api/settings/labels` | Criar etiqueta (name, color) |
| DELETE | `/api/settings/labels/{id}` | Excluir etiqueta |
| POST | `/api/settings/contexts` | Criar contexto do usuário |
| DELETE | `/api/settings/contexts/{id}` | Excluir contexto do usuário (não apaga padrões) |

---

## FASES DE CONSTRUÇÃO

### ✅ FASE 1 — Fundação
Estrutura de pastas, models, migrations via `_ensure_columns`, Docker, config.

### ✅ FASE 2 — Auth
JWT (PyJWT), bcrypt, login/logout, setup primeiro usuário, `get_current_user`.

### ✅ FASE 3 — Dashboard e Projetos
CRUD projetos, dashboard_service, overload_detector, templates base com sidebar.

### ✅ FASE 4 — Tarefas
CRUD tarefas com regras: validação de verbo, subtarefas, archiving, priority_score.

### ✅ FASE 5 — Captura e Processamento
Inbox de captura, processamento em task/project/note/discard.

### ✅ FASE 6 — Refinamentos de UX
Filtro de energia, quick wins, modo overload/minimal/full, contextos de trabalho, diretiva semanal, campos executivos, milestones/riscos/comentários/anexos, audit trail.

### ✅ FASE 7 — Design System (Notion-like)
Paleta unificada `oriens-*`, fonte Inter, zero `border-dashed`, hierarquia tipográfica.

### ✅ FASE 8 — IA
Providers desacoplados (Claude, OpenAI, Null), ativação por `.env`.

### ✅ SCRIPT 1 — Refatoração Oriens
Remoção completa do módulo Mission; renomeação para Oriens (tokens, cookies, banco); status de projeto com 3 estados; campos `proxima_acao` e `premissas`; `get_last_activity()` baseado em atividade real.

### ✅ SCRIPT 2 — Evolução dos Projetos
- **`responsavel_id`** (FK → users) em Project e Task
- **`project_timeline`** — tabela de eventos semânticos automáticos
- Cronologia visível no detalhe do projeto (seção "Cronologia")
- `get_last_activity()` migrado para ler de `project_timeline`
- Seed automático em `_migrate_data()` para projetos existentes

### ✅ SCRIPT 3 — Contextos, Etiquetas e Configurações
- **Contexto em tarefas:** seletor de contexto no formulário de edição; badge no `task_item`; opção "Independente (todos)".
- **Contextos dinâmicos:** `contexts.type` → `String(50)` + `contexts.user_id`; cookie passa a guardar `context_id` (int); helper `resolve_active_context()` compartilhado; sidebar lista contextos dinamicamente.
- **Etiquetas:** model `Label`, `label_repo`, campo `tasks.tags`, chips no formulário.
- **Página `/settings`:** criar/excluir etiquetas e contextos (`routes/settings.py` + `routes/api/settings.py`).

### ✅ PRODUÇÃO — Preparação para deploy
- **PostgreSQL:** driver `asyncpg`; `_ensure_columns()`/`_migrate_data()` com guard só-SQLite; `init_db()` roda sempre no lifespan (corrige tabelas não criadas com `DEBUG=false`).
- **`COOKIE_SECURE`** (config) aplicado em todos os `set_cookie` (login, setup, contexto, energia).
- **Docker:** `Dockerfile` de produção (sem `--reload`); `docker-compose.yml` (dev) com `--reload`; `docker-compose.prod.yml` (app + PostgreSQL + volumes `pgdata`/`appdata`).
- **PWA:** `manifest.webmanifest`, `sw.js`, `icon.svg` + meta tags e registro do service worker em `base.html`.
- **Responsividade:** sidebar off-canvas (hambúrguer) no mobile; grids do dashboard/projetos/detalhe adaptativos.
- **Infra/docs:** `nginx/oriens.conf`, `scripts/backup.sh`, `scripts/migrate_to_postgres.py`, `.dockerignore`, `.gitignore`, `DEPLOY.md`.

### ✅ DEPLOY — Oriens online na VPS Hostinger (acesso por IP)
- Código versionado no GitHub: **github.com/djavan123/oriens** (público).
- VPS Ubuntu 24.04: Docker instalado; repo em `/opt/oriens`.
- `.env` de produção (PostgreSQL, `DEBUG=false`, `COOKIE_SECURE=false`).
- Porta exposta como `8000:8000` (acesso direto por `http://IP:8000`).
- App + PostgreSQL no ar via `docker-compose.prod.yml`; conta criada e em uso.
- **Migração dos dados antigos do SQLite foi abandonada** — começou-se com banco limpo (o `pos.db` antigo tinha schema pré-SCRIPT 1; a migração foi testada e funcionava, mas optou-se por conta nova).
- **Pendente (futuro):** domínio + HTTPS (Nginx + Certbot), quando então reverter porta para `127.0.0.1:8000:8000` e `COOKIE_SECURE=true` (ver `DEPLOY.md`); ativar cron de backup.

### ✅ SCRIPT 4 — Melhorias na tela de detalhe do projeto
- **Lembretes de tarefa** (`remind_at`, sem recorrência) → Telegram (loop de fundo em `main.py` + `services/reminder_service.py`) + popup no app (`api/reminders.py`, `partials/reminder_popup.html`, polling em `base_app.html`). Config `TELEGRAM_*`; fuso `TZ=America/Sao_Paulo` (tzdata no Dockerfile).
- **Cronologia → "Atividade Recente"** (5 últimos) + modal "Ver histórico completo" no `detail.html`. Auditoria e `project_timeline` preservados.
- **Herança automática de contexto** nas tarefas de projeto (campo travado no edit).
- **Contexto obrigatório** ao criar/editar projeto.
- **Criação de tarefa só com título** (`task_form` reduzido) — o resto edita-se depois.
- Migração PG aditiva via `_ensure_columns_postgres()` (`ADD COLUMN IF NOT EXISTS`).

---

## PRODUÇÃO E OPERAÇÃO (VPS)

**Local na VPS:** `/opt/oriens` · **Acesso atual:** `http://IP_DA_VPS:8000`

**Comandos do dia a dia** (na VPS, em `/opt/oriens`):
```bash
docker compose -f docker-compose.prod.yml ps               # status
docker compose -f docker-compose.prod.yml logs -f app      # logs
docker compose -f docker-compose.prod.yml restart          # reiniciar
git pull && docker compose -f docker-compose.prod.yml up -d --build   # atualizar
```

**Regra de ouro:** ⚠️ **nunca** use `down -v` — o `-v` apaga o volume `pgdata` (perde conta/projetos/tarefas). Os dados sobrevivem a `restart`, `up -d --build` e reboot da VPS.

**Persistência:** banco em `pgdata`; anexos em `appdata` (`/app/data/attachments`).

**Backup:** `bash scripts/backup.sh` (pg_dump + anexos, retém 7 dias). Agendar:
`0 3 * * * cd /opt/oriens && bash scripts/backup.sh >> /var/log/oriens-backup.log 2>&1`

---

## ESTATÍSTICAS DO PROJETO (ATUAL)

| Item | Quantidade |
|---|---|
| Tabelas no banco | 14 (+ `labels`) |
| Models SQLAlchemy | 14 |
| Repositories | 14 (+ `label_repo`) |
| Services | 7 (+ `reminder_service`) |
| Rotas principais | 6 arquivos (+ `settings.py`) |
| Rotas API | 7 arquivos (+ `api/settings.py`, `api/reminders.py`) |
| Endpoints totais | ~40 |
| Templates HTML | ~26 (+ `settings.html`, `reminder_popup.html`) |
| Ambiente | Dev (SQLite) + Produção (PostgreSQL na VPS) |

---
