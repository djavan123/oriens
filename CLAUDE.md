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
| Servidor (web) | Gunicorn + Uvicorn workers | gunicorn 23.0.0 / uvicorn 0.30.6 — AUDITORIA |
| Worker (fundo) | Processo dedicado `app/worker.py` | lembretes + captura Telegram — AUDITORIA |
| ORM | SQLAlchemy | 2.0.35 |
| Frontend JS | HTMX | 1.9.12 (auto-hospedado, `static/vendor/` — AUDITORIA, era CDN) |
| Frontend JS | Alpine.js | 3.14.1 (auto-hospedado — AUDITORIA, era CDN) |
| Frontend JS | SortableJS | 1.15.2 (auto-hospedado — AUDITORIA, era CDN) |
| CSS | TailwindCSS | auto-hospedado (`static/vendor/tailwind.js` — AUDITORIA, era CDN) |
| Fonte | Inter | auto-hospedada (`static/vendor/fonts/` — AUDITORIA, era Google Fonts) |
| Templates | Jinja2 | 3.1.6 (AUDITORIA — era 3.1.4) |
| Auth | PyJWT + bcrypt (via passlib) | 2.9.0 + 4.2.0 |
| Banco | SQLite (dev) / PostgreSQL (prod) | aiosqlite 0.20 / asyncpg 0.29 |
| Testes | pytest + pytest-asyncio | 8.3.3 + 0.24.0 |
| IA (opcional) | Anthropic / OpenAI | 0.40.0 / 1.50.0 (pinados — AUDITORIA, eram `>=`) |
| Deploy | Docker Compose (prod) | VPS Ubuntu 24.04 |

> **Banco único, dois ambientes:** o mesmo código roda em **SQLite no dev** e **PostgreSQL na produção**, controlado só pela `DATABASE_URL`.
> **Migrations:** gerenciadas via `database.py` → `init_db()` com `Base.metadata.create_all` + `_ensure_columns()` (ALTER TABLE por coluna) + `_migrate_data()` (seed e migrações de dados). **`_ensure_columns()` e `_migrate_data()` rodam apenas em SQLite** (guard por `conn.dialect.name`). Para **migrações aditivas em PostgreSQL** (prod já no ar), use `_ensure_columns_postgres()` — `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` (idempotente, dict agora **sincronizado 1:1 com `_ENSURE_COLUMNS`** — AUDITORIA), mais `_ensure_indexes()` (índices em colunas quentes) e `_seed_contexts()`. `init_db()` roda **sempre** no startup (lifespan e `app/worker.py`), inclusive com `DEBUG=false`, protegido por **`pg_advisory_xact_lock`** (AUDITORIA) para ser seguro com múltiplos processos/workers rodando `init_db` ao mesmo tempo. **Alembic não está em uso ativo.**
> **Enums:** `Task.status/energy/cognitive_load`, `Project.status`, `ProjectRisk.impact/probability/status` usam `Enum(..., native_enum=False, length=50)` (AUDITORIA — eram `Enum` nativo do Postgres, que quebrava com `ALTER TYPE` ao adicionar um valor novo). Colunas Postgres pré-existentes são convertidas de `ENUM` nativo para `VARCHAR` automaticamente e uma única vez em `_ensure_columns_postgres` (`_PG_ENUM_TO_VARCHAR`, guardado por `information_schema.columns`).

---

## MAPA DE FUNCIONALIDADES (ESTADO ATUAL — o que o sistema faz hoje)

> Esta seção descreve o **comportamento vivo** (verificado no código, não no histórico).
> O histórico de como cada coisa chegou aqui está em "FASES DE CONSTRUÇÃO", mais abaixo.

| # | Área | O que faz | Onde vive |
|---|---|---|---|
| 1 | **Auth** | Login/logout por JWT em cookie httpOnly (`oriens_token`, 7 dias); `/auth/setup` cria o primeiro usuário. Rate-limit de 5 req/min no login (nginx). | `routes/auth.py`, `utils/auth.py` |
| 2 | **Contextos** | Contexto ativo (Trabalho/Casa/…) persiste em cookie e **filtra tudo**: Dashboard, Listas, Projetos. Tarefa/projeto sem contexto aparece em todos. Contextos criáveis em Configurações. Transição "Sair do trabalho" oferece capturar pendências. | `utils/context_utils.py`, `routes/api/context.py` |
| 3 | **Dashboard** | **Foco do dia** (texto único, edição inline) · **Agora** (UMA ação dominante: próxima ação do 1º projeto executável, senão 1ª tarefa avulsa) · **Evolução** (concluídas hoje + streak de dias consecutivos) · **Projetos em foco** (ativos por prioridade, com a próxima ação de cada) · **Tarefas avulsas**. Filtro por energia (`?energy=`, cookie 8h). Blocos recarregam por evento HTMX, sem reload. | `routes/dashboard.py`, `services/dashboard_service.py`, `partials/dashboard_*.html` |
| 4 | **Captura** | Caixa de entrada sem fricção (só conteúdo). Entradas: tela `/capture`, **atalho global `c`** (modal em qualquer tela) e **Telegram** (long polling no worker). Cada item vira: Descartar · Tarefa de projeto · Projeto · Listas (4 destinos). **Lixeira** com soft-delete (expurgo automático em 15 dias) e restauração. Edição inline do texto. Paginação "carregar mais" (50). | `routes/capture.py`, `routes/api/capture.py`, `services/capture_service.py` |
| 5 | **Listas** | Uma área de listas de tarefas, uma lista por vez: **Tarefas avulsas** (padrão) + **Notas** + **Repositório** (internas) + **personalizadas** (criar/renomear/arquivar). Tudo é `Task` — a lista é só agrupamento (`list_id`). Tarefa com URL no título exibe o **título da página** em vez do link cru (buscado em background). Paginação (100). | `routes/lists.py`, `routes/api/lists.py`, `utils/link_meta.py` |
| 6 | **Projetos — lista** | Kanban de 3 colunas (Em andamento / Não iniciado / Concluído) com **drag-and-drop entre colunas** para mudar status (sem reload). Filtros: Ativos / Arquivados / Todos. | `routes/projects.py`, `projects/list.html` |
| 7 | **Projetos — detalhe** | Duas abas (aba lembrada por `localStorage`): **Visão geral** (objetivo, prazo, progresso, decisões, comentários, anexos) e **Tarefas** (seções colapsáveis, drag-and-drop de tarefas dentro/entre seções e de seções entre si, subtarefas, badge "próxima ação", bloqueadas e concluídas inline). Arquivar/desarquivar. **Cronologia** automática + auditoria de campos. | `routes/projects.py`, `projects/detail.html`, `partials/project_*.html` |
| 8 | **Tarefas (drawer)** | Clicar no título de **qualquer** tarefa abre um painel lateral — **único fluxo de edição**: metadados (energia, prazo, responsável, etiquetas, contexto, prioridade, lista, quick win, lembrete) + **Descrição** + **Subtarefas**. Autosave por campo (sem botão salvar). | `GET /api/tasks/{id}/panel`, `partials/task_detail_panel.html` |
| 9 | **Prioridade** | **Projeto:** Máxima/Alta/Média/Baixa (`priority` 0-3, ordena a listagem e o Dashboard). **Tarefa avulsa/lista:** Máxima/Alta/Média/Baixa (`importancia` 6/5/3/1). **Tarefa de projeto:** não tem prioridade — vale a **ordem manual** de execução. | `services/importancia_service.py` |
| 10 | **Lembretes** | `remind_at` por tarefa (sem recorrência). Dois canais: **popup no app** (polling 60s + confirmar) e **Telegram** (worker, lote de 100/ciclo, trata 429). Roteado ao `telegram_chat_id` do dono. | `services/reminder_service.py`, `app/worker.py` |
| 11 | **Configurações** | Tema (3 temas) · **Telegram** (chat id do usuário) · **Etiquetas** (nome + cor) · **Contextos** personalizados. | `routes/settings.py`, `settings.html` |
| 12 | **Relatórios** | Tabela por projeto: progresso, atrasadas, riscos abertos, decisões. | `/projects/reports` |
| 13 | **IA (opcional)** | Quebrar tarefa em subtarefas · sugerir próximas ações do projeto. **Dormente por padrão** (`AI_ENABLED=false`); providers Claude/OpenAI/Null. | `services/ai_service.py`, `routes/api/ai.py` |
| 14 | **Aparência / PWA** | 3 temas (`dark`/`light`/`warm`) sem reload, sem flash; sidebar responsiva (off-canvas no mobile); app **instalável** (manifest) — **sem** cache offline (service worker desligado). | `static/css/theme.css`, `base.html` |

**Filtro de energia** (vivo): `?energy=high|medium|low` no Dashboard (cookie de 8h) filtra as **tarefas avulsas** por nível de energia. Não afeta projetos.

**Riscos de projeto:** backend completo (`/api/projects/{id}/risks`, contagem usada no relatório), **sem UI** — o bloco foi removido do detalhe.

**❌ Não existe mais (mas ainda aparece em regras/fases antigas abaixo):**
- **Anti-overload / modos overload-minimal-full**: `utils/overload_detector.py` **não existe** no código. O Dashboard atual é sempre Agora + Projetos em foco + Tarefas avulsas (a regra 2 e a regra 4 de "REGRAS DE NEGÓCIO" estão obsoletas).
- **Aba Semana / revisão semanal**, **Marcos**, **importância por critérios**, **service worker/PWA offline**, **validação de verbo no título**.

---

## ESTRUTURA DE PASTAS (ESTADO ATUAL — PÓS AUDITORIA)

```
C:\Projetos\Sistema tarefas\
├── app/
│   ├── __init__.py
│   ├── main.py                        # FastAPI app, routers, lifespan (init_db + seed contextos). SEM loops de fundo (ver worker.py) — AUDITORIA
│   ├── worker.py                      # NOVO (AUDITORIA): processo único p/ lembretes + captura Telegram, fora do web (permite gunicorn multi-worker)
│   ├── logging_setup.py               # NOVO (AUDITORIA): dictConfig de logging + check_production_secrets() (aborta boot com SECRET_KEY padrão em prod)
│   ├── config.py                      # Pydantic Settings (DATABASE_URL, SECRET_KEY, AI_*, COOKIE_SECURE, TELEGRAM_*)
│   ├── database.py                    # init_db() c/ pg_advisory_xact_lock; _ensure_columns/_migrate_data (SQLite) + _ensure_columns_postgres (PG, sincronizado) + _ensure_indexes + _seed_contexts + conversão enum→varchar — AUDITORIA
│   ├── templates_env.py               # Jinja2 env global (`now`, `fmt_size`, `due_status` — SCRIPT 6; `faixa_importancia` — SCRIPT 8)
│   ├── models/
│   │   ├── __init__.py                # Exporta todos os models (+ Label; CriterioContexto/TarefaCriterioValor REMOVIDOS — AUDITORIA)
│   │   ├── user.py                    # + foco_do_dia (SCRIPT 8); + telegram_chat_id (nullable, indexed) — AUDITORIA
│   │   ├── project.py                 # + proxima_acao, premissas, responsavel_id, archived (SCRIPT 5); status como Enum(native_enum=False) — AUDITORIA
│   │   ├── task.py                    # EnergyLevel aqui; + responsavel_id/tags/importancia/sem_nota; status/energy/cognitive_load Enum(native_enum=False) + índices em deadline/remind_at/status/archived/section_id — AUDITORIA
│   │   ├── note.py
│   │   ├── capture.py                 # + índice em `processed` — AUDITORIA
│   │   ├── context.py                 # type → String(50) nullable; + user_id (contextos dinâmicos)
│   │   ├── project_comment.py
│   │   ├── project_attachment.py      # anexos em DISCO: /app/data/attachments/{project_id}/
│   │   ├── project_decision.py        # Decisões (data + texto) — SCRIPT 5 (substituiu project_milestone)
│   │   ├── project_section.py         # Seção de projeto (nome, order_index) — SCRIPT 16A
│   │   ├── project_risk.py            # impact/probability/status Enum(native_enum=False) — AUDITORIA
│   │   ├── project_audit.py
│   │   ├── project_timeline.py        # TimelineEventType enum (+ decision_recorded, SCRIPT 5) + ProjectTimeline model
│   │   └── label.py                   # Label (etiquetas por usuário) — SCRIPT 3
│   │   # criterio_contexto.py / tarefa_criterio_valor.py REMOVIDOS na AUDITORIA (código morto do SCRIPT 8, desativado desde o SCRIPT 13). Tabelas legadas não são dropadas no banco.
│   │   # weekly_directive.py REMOVIDO (aba Semana excluída do projeto). Tabela weekly_directives legada não é dropada no banco.
│   ├── schemas/
│   ├── repositories/
│   │   ├── ... (user, project, task, note, capture, comment, attachment, decision, risk, audit, timeline)
│   │   ├── context_repo.py            # + get_all_by_user/get_by_id/create/delete (SCRIPT 3)
│   │   ├── user_repo.py               # + update_foco (SCRIPT 8); + get_by_telegram_chat_id/set_telegram_chat_id — AUDITORIA
│   │   ├── task_repo.py               # +order_index (nullslast); reorder/next/max-order; standalone_only; next/pending_count_by_project (10A/11); ordenação e validação de reorder deduplicadas (`_project_task_order`, `_load_reorderable_tasks`) — AUDITORIA
│   │   ├── project_repo.py            # get_active_by_user(context_id=...) — contexto antes de prioridade (SCRIPT 11)
│   │   ├── project_timeline_repo.py   # + last_activity_by_projects (batched) — SCRIPT 10C
│   │   ├── project_section_repo.py    # CRUD de seções de projeto — SCRIPT 16A
│   │   └── label_repo.py              # CRUD de etiquetas — SCRIPT 3
│   │   # criterio_repo.py REMOVIDO na AUDITORIA (junto do subsistema de critérios)
│   ├── services/
│   │   ├── project_service.py         # +get_project_next_action (10A) +get_executability (10C); audit/timeline; archived (SCRIPT 5)
│   │   ├── task_service.py            # priority_score + timeline; order_index no create (10A); SEM validação de verbo (import morto removido — AUDITORIA)
│   │   ├── capture_service.py         # process_as_task (aceita context_id) /project/note/discard
│   │   ├── dashboard_service.py       # get_projects_in_focus/get_standalone_tasks/pick_now_action (11/12); get_priorities_grouped e helpers REMOVIDOS (código morto) — AUDITORIA
│   │   ├── importancia_service.py     # SÓ `importancia_from_prioridade` + `faixa_importancia` (Máxima/Alta/Média/Baixa → 6/5/3/1). `ImportanciaService`/`calcular_importancia` REMOVIDOS (dead code) — AUDITORIA
│   │   ├── ai_service.py              # Protocol + ClaudeProvider + OpenAIProvider + NullProvider
│   │   └── reminder_service.py        # send_telegram(text, chat_id=None); process_due_telegram/process_telegram_updates roteados por users.telegram_chat_id com fallback ao .env — AUDITORIA
│   │   # weekly_directive_service.py REMOVIDO (aba Semana excluída do projeto)
│   ├── routes/
│   │   ├── auth.py                    # cookies com secure=COOKIE_SECURE
│   │   ├── dashboard.py               # GET /dashboard/now + /projects-focus + /standalone (11/12); PATCH /dashboard/foco. Rota /priorities legada REMOVIDA — AUDITORIA
│   │   ├── projects.py                # usa resolve_active_context(); list aceita ?filter=active|archived|all (SCRIPT 5); section_groups/done_by_section/blocked_by_section/responsavel_map (SCRIPT 16A/18); wiring de critérios removido — AUDITORIA
│   │   ├── capture.py                 # resolve_active_context()
│   │   ├── settings.py               # GET /settings (etiquetas + contextos); wiring de critérios removido — AUDITORIA
│   │   # weekly.py REMOVIDO (aba Semana excluída do projeto)
│   │   └── api/
│   │       ├── tasks.py               # PATCH /{id}/adiar; sem validação de verbo
│   │       ├── projects.py            # + PATCH /{id}/task-order (SCRIPT 10A); responsavel/proxima_acao/archived; decisões (SCRIPT 5); seções CRUD (SCRIPT 16A); upload de anexo com ownership+limite 20MB+allowlist — AUDITORIA
│   │       ├── capture.py
│   │       ├── ai.py
│   │       ├── context.py             # cookie agora guarda context_id (int) — SCRIPT 3
│   │       ├── settings.py            # CRUD etiquetas + contextos + POST /telegram (chat_id do usuário) — AUDITORIA. Rota /criterios REMOVIDA
│   │       └── reminders.py           # GET /due (popup) + POST /{id}/ack — SCRIPT 4
│   ├── templates/
│   │   ├── base.html                  # tokens oriens-*→var(); theme.css; init de tema sem flash; Tailwind/HTMX/Alpine/fonte Inter AUTO-HOSPEDADOS via /static/vendor (AUDITORIA — eram CDN)
│   │   ├── base_app.html              # sidebar RESPONSIVA + contextos dinâmicos + seletor de tema "Aparência" (SCRIPT 6)
│   │   ├── dashboard.html             # bloco "Agora" + Projetos em foco × Tarefas avulsas (SCRIPT 11/12)
│   │   ├── capture.html
│   │   ├── process.html
│   │   ├── settings.html              # etiquetas + contextos + seção "Telegram" (chat_id do usuário) — AUDITORIA. Seção de critérios REMOVIDA
│   │   # weekly.html REMOVIDO (aba Semana excluída do projeto)
│   │   ├── auth/ (login.html, setup.html)
│   │   ├── projects/
│   │   │   ├── list.html              # tabela com seções colapsáveis Alpine (SCRIPT 17)
│   │   │   ├── detail.html            # abas Alpine (Visão geral/Tarefas); SortableJS auto-hospedado; handlers `htmx:afterSettle` consolidados em um só — AUDITORIA
│   │   │   └── reports.html           # coluna "Decisões" (era "Marcos") — SCRIPT 5
│   │   └── partials/
│   │       ├── task_item.html         # PARTIAL UNIFICADO de tarefa — usado por Dashboard, concluídas, overload; flags: reload_on_done, hide_actions
│   │       ├── project_task_row.html  # linha densa Asana: drag | checkbox | título | energia | prazo | responsável | ações hover; usado em detail + seções (SCRIPT 16B)
│   │       ├── capture_item.html      # item de captura — mesmo estilo visual denso (SCRIPT 9)
│   │       ├── theme_switcher.html      # 3 bolinhas dark/light/warm (Alpine `theme`) — SCRIPT 6
│   │       ├── task_form.html         # CRIAÇÃO só com título (SCRIPT 4)
│   │       ├── task_edit_form.html    # energia/prazo/resp/etiquetas/quick win/lembrete; contexto travado se for de projeto
│   │       ├── reminder_popup.html    # toasts de lembrete (SCRIPT 4)
│   │       ├── project_form.html       # criação: + "Próxima ação" (SCRIPT 5)
│   │       ├── project_decision.html   # item de decisão (data + texto + excluir) — SCRIPT 5
│   │       ├── foco_do_dia.html        # compacto se vazio, accent se preenchido (SCRIPT 12) + _foco_form.html
│   │       ├── dashboard_now.html       # bloco "Agora": UMA ação dominante (SCRIPT 12)
│   │       ├── dashboard_projects_focus.html # coluna "Projetos em foco" + contador sem-próxima-ação (SCRIPT 11)
│   │       ├── dashboard_project_card.html   # card de projeto em foco (próxima ação/energia/prazo) (SCRIPT 11/12)
│   │       ├── dashboard_standalone.html     # coluna "Tarefas avulsas" (task_item hide_actions) (SCRIPT 11/12)
│   │       ├── project_card.html        # card minimalista: nome + prioridade/contexto/prazo + ações hover (SCRIPT 16B)
│   │       ├── project_section.html     # bloco de seção: rename Alpine, delete HTMX, task-list + task_form inline (SCRIPT 16A)
│   │       ├── project_row.html         # linha <tr> de projeto para list.html (retorno do POST /api/projects)
│   │       ├── capture_content_span.html # span editável de captura (retorno do PATCH /api/capture/{id})
│   │       └── ... (comment/attachment/risk, process, ai_result)
│   │   # REMOVIDOS na AUDITORIA (código morto/órfão): task_with_subtasks.html, dashboard_priorities.html,
│   │   # dashboard_task.html, criterio_selector.html.
│   ├── static/
│   │   ├── vendor/                    # NOVO (AUDITORIA): Tailwind, HTMX, Alpine, SortableJS + fonte Inter (woff2) auto-hospedados — sem CDN
│   │   # sw.js REMOVIDO — service worker desligado (ver "FIX — site servindo versão antiga"): era
│   │   # registrado em /static/sw.js SEM `scope`, logo escopo /static/ → nunca controlou as páginas
│   │   # e o "PWA offline" nunca existiu. base.html agora só desregistra o órfão e limpa os caches.
│   │   └── manifest.webmanifest, icon.svg, css/theme.css (3 temas — SCRIPT 6)
│   └── utils/
│       ├── auth.py                    # cookie: oriens_token; datetime via utils/time.utcnow() — AUDITORIA
│       ├── time.py                    # NOVO (AUDITORIA): utcnow() (naive UTC, convenção única) / now_local() (lembretes)
│       # overload_detector.py NÃO EXISTE (anti-overload removido — ver MAPA DE FUNCIONALIDADES)
│       └── context_utils.py           # resolve_active_context() — SCRIPT 3
│   # verb_validator.py REMOVIDO na AUDITORIA (import morto desde o SCRIPT 12)
├── tests/                              # SUÍTE REESCRITA na AUDITORIA (legado mission/POS removido) — ver seção TESTES
├── data/                              # SQLite (dev) + anexos (/app/data/attachments)
├── scripts/
│   ├── backup.sh                      # pg_dump + anexos (.tar.gz), retenção 7 dias
│   └── migrate_to_postgres.py         # cópia SQLite → PostgreSQL (opcional) — exige PYTHONPATH=/app
├── nginx/
│   └── oriens.conf                    # proxy reverso + `location /static/` direto + `limit_req` no /auth/login — AUDITORIA
├── docker-compose.yml                 # DEV (SQLite + --reload + TZ) + serviço `worker` — AUDITORIA
├── docker-compose.prod.yml            # PROD (app + PostgreSQL + worker + volumes pgdata/appdata + TZ + healthcheck do app) — AUDITORIA
├── Dockerfile                         # produção: gunicorn -k UvicornWorker -w 3 (era uvicorn single-process) — AUDITORIA
├── .dockerignore  /  .gitignore
├── .env  /  .env.example              # .env.example tem blocos DEV e PROD
├── DEPLOY.md                          # guia completo (domínio + HTTPS + Nginx + backup + worker + rollback) — AUDITORIA
├── requirements.txt                   # + gunicorn; python-multipart/jinja2 atualizados (CVE) — AUDITORIA
└── README.md
```

---

## BANCO DE DADOS (ESTADO ATUAL — PÓS SCRIPT 5)

**users:** `id, email (unique), password (bcrypt), name, created_at, foco_do_dia (text, nullable — SCRIPT 8), telegram_chat_id (varchar(64), nullable, indexed — AUDITORIA)`
- `telegram_chat_id`: chat do Telegram do usuário (lembretes + captura roteados por dono). `NULL` → usa o `TELEGRAM_CHAT_ID` global do `.env` (compatibilidade single-user). Editável em `/settings`.

**projects:** `id, user_id, responsavel_id (nullable, FK users), context_id (nullable), name, objective, status, priority (0-3; 0=Máxima, 1=Alta, 2=Média, 3=Baixa; menor = mais prioritário), deadline, notes, done_at, scope, tags, strategic (bool), quarter, owner, strategic_priority, proxima_acao (text), premissas (text), archived (bool, default false), created_at, updated_at`
- status: `nao_iniciado | em_andamento | concluido`
- Todo projeto novo nasce com `nao_iniciado`
- `archived` (SCRIPT 5): true esconde da operação diária (listagem/dashboard/semanal); continua acessível por URL, editável e pesquisável

**tasks:** `id, user_id, responsavel_id (nullable, FK users), project_id (nullable), parent_id (nullable, self-ref), context_id (nullable), title, status, energy, is_quick_win (bool), cognitive_load, financial_impact, operational_risk, strategic_impact, task_urgency, effort, priority_score (indexed), importancia (float, indexed — SCRIPT 8), sem_nota (bool, default true — SCRIPT 8), order_index (int, nullable — SCRIPT 10A), archived (bool), deadline, tags (text), description (text, nullable — painel/drawer), remind_at (datetime, nullable), reminder_telegram_sent (bool), reminder_acked (bool), created_at, done_at`
- `importancia` (0-5): calculada dos critérios do contexto. `sem_nota`=true quando o contexto não tem critérios (ou tarefa criada sem nota). **Importância NÃO se aplica a tarefas de projeto** (SCRIPT 10B): elas ficam `sem_nota` e não exibem badge.
- `order_index` (SCRIPT 10A): ordem manual das tarefas de **topo de projeto**. NULL em avulsas e subtarefas. Nova tarefa de projeto entra com `max+1` (fim). Reordenável por drag-and-drop só no detalhe (`PATCH /api/projects/{id}/task-order`).
- status: `pending | done | blocked`
- energy: `high | medium | low` (EnergyLevel enum em `task.py`)
- `tags`: etiquetas separadas por vírgula (SCRIPT 3)
- `context_id` NULL = tarefa "Independente (todos os contextos)" — aparece em qualquer contexto

> **`criterio_contexto` / `tarefa_criterio_valor`** (SCRIPT 8, importância ponderada por critérios) foram **removidas do código** na AUDITORIA — desativadas desde o SCRIPT 13 (substituídas por Alta/Média/Baixa) e comprovadamente sem leitor vivo (`ImportanciaService`/`calcular_importancia` nunca eram instanciados). As tabelas legadas podem permanecer órfãs no banco (não são dropadas — operação não-destrutiva); nada mais as lê ou escreve.

**labels:** `id, user_id (FK cascade), name, color (hex, nullable)`  *(SCRIPT 3)*
- Etiquetas predefinidas pelo usuário, gerenciadas em `/settings`

**project_timeline:** `id, project_id (FK cascade), user_id (FK cascade), event_type (string), description (string), created_at (indexed)`
- event_type: `project_created | status_changed | task_created | task_done | decision_recorded`
- Seed automático em `_migrate_data()`: todos os projetos existentes recebem evento `project_created`
- `get_last_activity()` em `project_repo` lê daqui (fallback: `project.updated_at`)

**project_decisions:** `id, project_id (FK cascade, indexed), user_id (FK cascade), content (text), created_at`  *(SCRIPT 5 — substituiu project_milestones)*
- Decisões relevantes do projeto (data + texto). Sem `done`/`due_date`.
- Criar uma decisão grava também um evento `decision_recorded` em `project_timeline`.
- Listadas no detalhe em ordem decrescente (mais recente no topo).

**capture_inbox:** `id, user_id, content, processed (bool), created_at`

**notes:** `id, user_id, project_id (nullable), content, created_at`

**contexts:** `id, name, type (String(50) nullable), user_id (nullable, FK users)`  *(alterado no SCRIPT 3)*
- 4 contextos padrão (`user_id = NULL`): type `work | home_recovery | home_operational | gym`
- Contextos do usuário (`user_id` preenchido): criados/excluídos em `/settings`
- `type` deixou de ser enum fixo → string livre (preserva os padrões e permite contextos dinâmicos)

**project_comments, project_attachments, project_risks, project_audit:** sem alterações.

> **`project_milestones`** (Marcos) foi **removida do código** no SCRIPT 5 (model/repo/rotas/template). A tabela legada pode permanecer órfã no banco (não é dropada — operação não-destrutiva); nada mais a lê.

> **`weekly_directives`** (aba Semana / revisão semanal) foi **removida do código** (model, repository, service, rota `/weekly`, template, link na sidebar). A tabela legada pode permanecer órfã no banco (não é dropada — operação não-destrutiva); nada mais a lê.

---

## REGRAS DE NEGÓCIO

1. ~~**Título de tarefa:** deve começar com verbo~~ — **REVOGADA pela regra 29** (SCRIPT 12: validação desativada). O helper `verb_validator.py` foi **removido** na AUDITORIA (import morto). Qualquer título não vazio é aceito.
2. ~~**Anti-overload:** score = `(projetos_em_andamento * 2) + tarefas_pendentes`, threshold 15 → modo overload~~ — **OBSOLETA**: `utils/overload_detector.py` não existe mais e o Dashboard não tem modo overload (ver MAPA DE FUNCIONALIDADES).
3. **Captura sem fricção:** `POST /api/capture` exige apenas `content`. Zero outros campos obrigatórios.
4. ~~**Energia como filtro:** modos minimal/reduced/full~~ — **OBSOLETA na forma descrita**. O que vale hoje: `?energy=high|medium|low` (cookie 8h) filtra **as tarefas avulsas** do Dashboard por energia; não há modos nem corte de quantidade.
5. **Priority score de tarefas:** calculado em `task_service._calc_score()` com 5 métricas: financial_impact, operational_risk, strategic_impact, task_urgency, effort.
6. **Auditoria de projetos:** campos auditados: `status, priority, name, deadline, objective, scope, notes, proxima_acao`. Cada mudança grava em `project_audit`.
7. **Contexto de trabalho:** cookie `oriens_context` persiste o contexto ativo. Transição work→recovery exibe painel com itens pendentes para captura.
8. **Diretiva semanal:** upsert por `week_start` (segunda-feira). Seção "Projetos sem atualização" exibe projetos `em_andamento` ordenados por última atividade real (mais antigo primeiro).
9. **Última atividade de projeto:** lida de `project_timeline` via `ProjectTimelineRepository.get_last_activity()`. Fallback: `project.updated_at`.
10. **Status de projeto:** nasce `nao_iniciado`. Transições livres entre os 3 estados. "Concluído" define `done_at`.
11. **Cronologia automática:** eventos gravados automaticamente em `project_timeline`:
    - `project_service.create()` → `project_created`
    - `project_service.update()` ao mudar status → `status_changed`
    - `task_service.create()` com project_id → `task_created`
    - `task_service.mark_done()` com project_id → `task_done`
    - `POST /api/projects/{id}/decisions` → `decision_recorded` (SCRIPT 5)
12. **Responsável:** `responsavel_id` (FK → users) em projetos e tarefas. Exibido no detalhe do projeto e no footer dos cards. Select dropdown condicional nos formulários (só aparece quando `users` está no contexto).
13. **Contextos dinâmicos:** deixaram de ser enum fixo. Cookie `oriens_context` agora guarda o **`context_id` (inteiro)**. `resolve_active_context()` (`app/utils/context_utils.py`) é o helper único usado por todas as rotas HTML; retorna `(context_id, active_context_obj, all_contexts)` e ainda lê cookies legados por `type`. A sidebar lista os contextos dinamicamente; a transição "Sair do trabalho" é decidida por `active_context_obj.type == "work"`.
14. **Tarefa independente de contexto:** `context_id = NULL` significa "Independente (todos os contextos)" — a tarefa aparece em qualquer contexto ativo (filtro: `context_id IS NULL OR context_id == ativo`).
15. **Etiquetas (labels):** CRUD em `/settings`. Campo `tasks.tags` (texto, vírgula). No formulário de tarefa, chips das etiquetas do usuário preenchem o campo `tags` (Alpine). Badges de contexto e tags aparecem no `task_item`.
16. **Lembretes de tarefa:** `remind_at` (data+hora, sem recorrência). Dois canais: (a) **Telegram** — loop de fundo em **`app/worker.py`** (processo separado do web desde a AUDITORIA; era `main.py`) a cada 60s chama `reminder_service.process_due_telegram()`; envia ao `telegram_chat_id` do **dono da tarefa**, com fallback ao `TELEGRAM_BOT_TOKEN`+`TELEGRAM_CHAT_ID` globais do `.env` (AUDITORIA — Telegram por usuário); marca `reminder_telegram_sent`. (b) **Popup no app** — `base_app.html` faz polling de `GET /api/reminders/due` (60s); `POST /api/reminders/{id}/ack` seta `reminder_acked`. Ao editar o lembrete, ambos os flags são resetados. Hora local depende de `TZ=America/Sao_Paulo`.
17. **Herança de contexto:** toda tarefa criada dentro de um projeto herda `context_id` do projeto (forçado em `api/tasks.create_task`). No `task_edit_form`, o contexto fica **somente leitura** para tarefas de projeto; editável só para tarefas avulsas.
18. **Contexto obrigatório no projeto:** `create_project` e `update_project` exigem `context_id`; o select é `required` e nunca permite valor vazio. Projetos antigos sem contexto devem recebê-lo ao serem editados.
19. **Criação de tarefa só com título** (GTD "capturar primeiro, organizar depois"): o `task_form` pede apenas o título; energia, prazo, responsável, etiquetas, quick win e lembrete são ajustados depois via "editar". **Exceção (SCRIPT 8):** se o contexto da tarefa tiver critérios, o form expande com os seletores 0-5 obrigatórios.
20. ~~**Importância ponderada (SCRIPT 8):** critérios por contexto com peso/inverter~~ — **REMOVIDA na AUDITORIA**. Desativada desde o SCRIPT 13 (substituída pela regra 20-bis, Alta/Média/Baixa); código morto (`ImportanciaService`, `calcular_importancia`, model `criterio_contexto`/`tarefa_criterio_valor`, rota de critérios) apagado por não ter nenhum leitor vivo. Só sobrevivem `importancia_from_prioridade` e `faixa_importancia` em `services/importancia_service.py`.
21. ~~**Obrigatoriedade dos critérios (SCRIPT 8)**~~ — **REMOVIDA na AUDITORIA** junto da regra 20 (mesmo motivo).
22. **Foco do dia (SCRIPT 8):** `users.foco_do_dia` (singleton, sem histórico). Card no topo do Dashboard (único com borda `--oriens-accent`), edição inline (Alpine) salvando em `PATCH /dashboard/foco`.
23. **Dashboard de Prioridades (SCRIPT 8, modo normal):** componente `partials/dashboard_priorities.html` com **três grupos** — Atrasadas / Hoje / Alta importância (`importancia >= 4` e não urgente). Máx. 3 cards por grupo (+N ocultas; "+ X outras prioridades" expande via `?expand=1`). Resumo "N atrasadas · N hoje · N alta" (bolinhas). **Pills** Todos/Atrasado/Hoje/Alta (`alta` reúne toda `importancia >= 4`). Ordenação intra-grupo por `importancia` desc. **Polling 30s** (`hx-trigger="every 30s, refreshPriorities from:body"`, swap `outerHTML`) + "atualizado há Xs". Cards (`partials/dashboard_task.html`): projeto (📁), urgência (atrasado·Nd/hoje), `alta · X.X` só na faixa alta, esforço `⏱`, `⚠` se `sem_nota`, **adiar** (escolhe novo prazo, `PATCH /api/tasks/{id}/adiar`, hover). Dados via `DashboardService.get_priorities_grouped` + `task_repo.get_pending_for_dashboard`/`_urgency_rank`. Fragmento: `GET /dashboard/priorities`. Modos overload/minimal inalterados.
20. **Próxima ação (SCRIPT 5):** todo projeto deve ter uma próxima ação concreta e executável. Campo `proxima_acao` exibido **em destaque no topo** do detalhe, no card da listagem e na revisão semanal. Disponível no formulário de criação (**opcional**) e na edição. Auditado.
21. **Arquivamento de projetos (SCRIPT 5):** `projects.archived` (bool). Arquivados saem da listagem padrão, dashboard, revisão semanal e "Projetos sem atualização", mas continuam acessíveis por URL, editáveis e pesquisáveis. Filtros na listagem: `?filter=active` (padrão) | `archived` | `all`. Botão "Arquivar/Desarquivar projeto" no detalhe (`PATCH /api/projects/{id}` com `archived`). Filtro de `archived == False` aplicado em `get_all_by_user` (padrão), `get_active_by_user` e `count_active`; `get_by_id` permanece sem filtro.
22. **Decisões (SCRIPT 5):** substituem os antigos Marcos. `project_decisions` (data + texto). No detalhe, seção "Decisões" com input "Nova decisão..." + "Adicionar"; lista em ordem decrescente. Criar uma decisão grava evento `decision_recorded` na cronologia. Excluir uma decisão **não** remove o evento da timeline.

### Execução de projetos e Dashboard (SCRIPTS 10–12)

23. **Três tipos de importância:** **Projeto** = importância estratégica (`priority` 0-3 = Máxima/Alta/Média/Baixa; menor = mais prioritário). **Tarefa de projeto** = ordem de execução (`order_index`), **não** usa importância. **Tarefa avulsa** = importância própria (Máxima/Alta/Média/Baixa → `importancia` 6/5/3/1).
24. **Próxima ação operacional de um projeto:** 1ª tarefa pendente em ordem manual → fallback `project.proxima_acao` → se não houver nenhum, projeto **não é executável**. Energia é informativa e **não** reordena projetos nem tarefas de projeto.
25. **Ordem manual (SCRIPT 10A):** `tasks.order_index` só vale para tarefas de topo de projeto. Reordenável por drag-and-drop (SortableJS) **apenas no detalhe do projeto**; persiste via `PATCH /api/projects/{id}/task-order` (valida ownership/pertencimento, rejeita avulsas/subtarefas). Nova tarefa de projeto vai ao fim.
26. **Estado operacional do projeto (SCRIPT 10C):** `completed | not_started | no_action | stalled | executable` (em `get_executability`; `stalled` = em andamento sem atividade ≥7 dias). Exibido na lista como próxima ação ou "Precisa de revisão" (discreto, nunca vermelho).
27. **Dashboard separa projeto × avulsa (SCRIPT 11):** nunca mistura tarefa de projeto com avulsa. **Projetos em foco** = ativos não-arquivados ordenados por prioridade, só os com próxima ação (resto vira contador "sem próxima ação"). **Tarefas avulsas** (`project_id` nulo) mantêm importância/energia/urgência. Ambos respeitam o contexto ativo (contexto antes de prioridade).
28. **Bloco "Agora" (SCRIPT 12):** mostra UMA única ação dominante — próxima ação do 1º projeto executável em foco → senão 1ª tarefa avulsa. Concluir a ação recarrega via eventos `refreshProjectsFocus`/`refreshPriorities` (timeline preservada). Sem lista, sem drag-and-drop no Dashboard.
29. **Sem validação de verbo (SCRIPT 12):** títulos de tarefa aceitam qualquer texto não vazio. O helper `validate_starts_with_verb` foi **mantido** mas não é mais chamado em `task_service`. Bloqueio de título vazio permanece na rota.

---

## UX — TEMAS (DESIGN SYSTEM APLICADO)

**Três temas** (`dark` padrão, `light`, `warm`), trocáveis sem reload. (SCRIPT 6)

- **Fonte da verdade:** `app/static/css/theme.css` define os tokens `--oriens-*` por
  `:root[data-theme="dark|light|warm"]` (+ bloco `:root:not([data-theme])` como fallback dark).
- **Ponte com Tailwind:** o `tailwind.config` em `base.html` mapeia cada cor `oriens-*` para
  `var(--oriens-*)`. Assim **toda** classe utilitária (`bg-oriens-*`, `text-oriens-*`,
  `border-oriens-*`) re-tematiza automaticamente — **não** redefina cores hardcoded nos templates;
  use sempre os tokens.
- **Aliases legados:** `theme.css` mantém `--bg-app`, `--bg-sidebar`, `--text-primary`, `--accent`,
  `--border-default`, etc. apontando para os `--oriens-*` (usados por `.card/.sidebar/.btn-primary`
  e por `style="…var(--…)…"` inline). Não recriar um segundo sistema de tema.
- **Sem flash:** script inline no topo do `<head>` (antes do Tailwind) seta `data-theme` a partir
  do `localStorage('oriens-theme')`. O `<html>` tem `x-data="{ theme }"`/`x-init` (Alpine) que
  persiste e reaplica em `$watch`. Seletor: `partials/theme_switcher.html` (3 bolinhas), incluído
  na sidebar (`base_app.html`) e em Configurações → "Aparência".

Tokens semânticos de urgência: `oriens-urgent` (atrasado), `oriens-today` (hoje), `oriens-ok`.
`oriens-accent-text` = texto sobre `accent`/botões. `oriens-sidebar` = fundo da sidebar.

Paleta (resumo — valores completos em `app/static/css/theme.css`):

| token | dark | light | warm |
|---|---|---|---|
| `--oriens-bg` | `#15151A` | `#FAF9F6` | `#1A1815` |
| `--oriens-surface` | `#21212B` | `#FFFFFF` | `#2A2622` |
| `--oriens-primary` (texto) | `#F2F1ED` | `#1F1E1B` | `#F0EBE3` |
| `--oriens-accent` | `#7F77DD` | `#534AB7` | `#D85A30` |
| `--oriens-urgent` / `--oriens-today` / `--oriens-ok` | `#E24B4A`/`#EF9F27`/`#5DCAA5` | `#A32D2D`/`#854F0B`/`#0F6E56` | `#E24B4A`/`#EF9F27`/`#1D9E75` |

Princípios: cor/contraste são **função** (usuário com TDAH), não enfeite. Espaço generoso
(`px-12 py-10`), tipografia como hierarquia, zero ícones decorativos, zero `border-dashed`,
máximo 3 níveis de informação por tela, fonte Inter. **Nenhum tema pode deixar texto ilegível.**

**Badge de urgência por data:** `due_status(value)` (global Jinja em `templates_env.py`) →
`overdue|today|future|None`. Usado em `task_item.html` e `project_card.html`: atrasado → badge
`oriens-urgent`; hoje → badge `oriens-today`; futuro → só a data (sem badge).

**Estados vazios = convite:** no detalhe do projeto, "sem objetivo/risco/decisão" são links em
`oriens-accent` que abrem o campo (objetivo dispara `$dispatch('abrir-edicao')` → form de
metadados; risco → `adding=true`; decisão → foca `#decision-input`).

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
| GET | `/projects` | Lista de projetos (tabela + seções colapsáveis); `?filter=active\|archived\|all` (SCRIPT 5/17) |
| GET | `/projects/reports` | Relatórios |
| GET | `/projects/{id}` | Detalhe do projeto |
| GET | `/capture` | Inbox de captura |
| GET | `/process` | Processar capturas pendentes |
| GET | `/settings` | Configurações: etiquetas + contextos (SCRIPT 3) |
| GET | `/api/reminders/due` | Lembretes vencidos do usuário (popup HTMX, polling 60s) |
| POST | `/api/reminders/{id}/ack` | Confirmar/dispensar lembrete (popup) |
| GET | `/health` | Health check JSON — inclui `SELECT 1` no banco; 503 se o DB não responder (AUDITORIA) |

### API (fragmentos HTMX)

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/tasks` | Criar tarefa (aceita `responsavel_id`) |
| PATCH | `/api/tasks/{id}/done` | Marcar concluída (grava timeline) |
| PATCH | `/api/tasks/{id}/blocked` | Marcar bloqueada |
| PATCH | `/api/tasks/{id}/pending` | Marcar pendente |
| PATCH | `/api/tasks/{id}/archive` | Arquivar |
| PATCH | `/api/tasks/{id}/adiar` | Adiar: novo prazo; 204 + `HX-Trigger: refreshPriorities` (SCRIPT 8) |
| GET | `/api/tasks/{id}/panel` | Painel de detalhe da tarefa (drawer): metadados editáveis + Descrição + Subtarefas. Único fluxo de edição |
| PATCH | `/api/tasks/{id}` | Atualizar tarefa (aceita `responsavel_id`, `description`) |
| POST | `/api/projects` | Criar projeto (aceita `responsavel_id`, `proxima_acao`, grava timeline) |
| PATCH | `/api/projects/{id}` | Atualizar projeto (aceita `responsavel_id`, `proxima_acao`, `archived`, grava timeline) |
| POST | `/api/projects/{id}/comments` | Adicionar comentário |
| DELETE | `/api/projects/{id}/comments/{cid}` | Remover comentário |
| POST | `/api/projects/{id}/attachments` | Upload arquivo |
| GET | `/api/projects/{id}/attachments/{aid}/download` | Download |
| DELETE | `/api/projects/{id}/attachments/{aid}` | Remover arquivo |
| POST | `/api/projects/{id}/decisions` | Criar decisão (grava timeline `decision_recorded`) |
| DELETE | `/api/projects/{id}/decisions/{did}` | Remover decisão |
| POST | `/api/projects/{id}/risks` | Criar risco |
| PATCH | `/api/projects/{id}/risks/{rid}` | Atualizar risco |
| DELETE | `/api/projects/{id}/risks/{rid}` | Remover risco |
| POST | `/api/capture` | Adicionar captura |
| PATCH | `/api/capture/{id}` | Atualizar conteúdo de captura (edição inline) |
| POST | `/api/process/{id}` | Processar captura |
| POST | `/api/ai/break-task/{id}` | IA: quebrar tarefa |
| POST | `/api/ai/suggest-actions/{id}` | IA: sugerir ações |
| POST | `/api/ai/overload-context` | IA: análise de overload |
| POST | `/api/context/switch` | Trocar contexto ativo (campo `context_id` inteiro) |
| POST | `/api/context/transition` | Transição + captura pendências (campo `context_id`) |
| PATCH | `/api/projects/{id}/task-order` | Reordena tarefas de topo do projeto (JSON `{task_ids:[...]}`) — SCRIPT 10A (legado, sem seção) |
| PATCH | `/api/projects/{id}/section-tasks` | Move e reordena tarefas dentro de ou entre seções (JSON `{section_id: null\|int, task_ids:[...]}`) |
| PATCH | `/api/projects/{id}/section-order` | Reordena seções de um projeto (JSON `{section_ids:[...]}`) |
| GET | `/dashboard/now` | Fragmento bloco "Agora" (uma ação dominante) — SCRIPT 12 |
| GET | `/dashboard/projects-focus` | Fragmento "Projetos em foco" — SCRIPT 11 |
| GET | `/dashboard/standalone` | Fragmento "Tarefas avulsas" (`?energy=`) — SCRIPT 11 |
| PATCH | `/dashboard/foco` | Salvar foco do dia (SCRIPT 8) |
| POST | `/api/settings/labels` | Criar etiqueta (name, color) |
| DELETE | `/api/settings/labels/{id}` | Excluir etiqueta |
| POST | `/api/settings/contexts` | Criar contexto do usuário |
| DELETE | `/api/settings/contexts/{id}` | Excluir contexto do usuário (não apaga padrões) |
| POST | `/api/settings/telegram` | Salvar `telegram_chat_id` do usuário (AUDITORIA) |

> **Removidos na AUDITORIA:** `GET /dashboard/priorities` (legado, código morto — dashboard atual usa `/dashboard/now` + `/dashboard/projects-focus` + `/dashboard/standalone`) e `POST /api/settings/criterios/{context_id}` (subsistema de critérios removido).
>
> **Removidos (aba Semana):** `GET /weekly` e `POST /weekly` — feature de revisão semanal excluída do projeto (model, repository, service, rota, template e link na sidebar removidos; tabela `weekly_directives` permanece órfã no banco, não-destrutivo).

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
- **PWA:** `manifest.webmanifest`, `icon.svg` + meta tags (app instalável). O `sw.js`/registro do service worker foi **removido** — nunca funcionou (escopo `/static/`); ver "FIX — site servindo versão antiga".
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

### ✅ SCRIPT 5 — Evolução dos Projetos
- **Próxima ação em destaque:** bloco no topo do detalhe; campo (opcional) no formulário de criação; mantida no card e na revisão semanal; passou a ser auditada.
- **Arquivamento de projetos:** `projects.archived` (bool). Esconde da operação diária (listagem/dashboard/semanal/"sem atualização"); continua acessível por URL, editável e pesquisável. Filtros `?filter=active|archived|all` na listagem; botão arquivar/desarquivar no detalhe. Filtro `archived == False` em `get_all_by_user`/`get_active_by_user`/`count_active`.
- **Marcos → Decisões:** removidos model/repo/rotas/template de milestones; novo `project_decisions` (data + texto), `project_decision_repo`, `partials/project_decision.html`, seção "Decisões" no detalhe e coluna "Decisões" no relatório.
- **Cronologia:** criar uma decisão grava evento `decision_recorded` em `project_timeline` (novo valor no enum `TimelineEventType`).
- Migração PG aditiva: `archived` em `_ENSURE_COLUMNS_PG["projects"]`; SQLite em `_ENSURE_COLUMNS["projects"]`. Tabela `project_milestones` legada não é dropada (não-destrutivo).

### ✅ SCRIPT 6 — Temas + clareza visual
- **3 temas** (`dark`/`light`/`warm`) via `data-theme` no `<html>`: `app/static/css/theme.css` define os tokens `--oriens-*`; o `tailwind.config` aponta cada `oriens-*` para `var(--oriens-*)` → app inteiro re-tematiza sem editar tela a tela. Aliases legados (`--bg-app`, `--accent`, …) preservados.
- **Sem flash + persistência:** script inline no `<head>` aplica `data-theme` do `localStorage`; `x-data`/`x-init` (Alpine) no `<html>` persiste e reaplica. Seletor `partials/theme_switcher.html` na sidebar e em Configurações → "Aparência".
- **Sweep de legibilidade:** `text-[#f2f2f2]`→`text-oriens-primary`, `hover:text-[#8fc1ff]`→`hover:opacity-80`, e estilos inline da sidebar/kanban → `var(--oriens-*)` (nenhum tema deixa texto ilegível).
- **Urgência por data:** global Jinja `due_status()` em `task_item.html` e `project_card.html` (badge atrasado/hoje; futuro só data). Tokens `oriens-urgent/today/ok`.
- **Barra de progresso:** já existia (reusa `progress_by_project`); trilho em `oriens-card-hover` + legenda "X de Y tarefas concluídas".
- **Estados vazios como convite:** objetivo/risco/decisão vazios viram link em `oriens-accent` que abre o campo (Alpine `$dispatch('abrir-edicao')` / `adding=true` / foco em `#decision-input`).

### ✅ SCRIPT 7 — Ajustes na página de Projeto
- Riscos **ocultos** da UI (`{% if false %}`, backend intacto); "Atividade Recente" só com link de histórico; card de **Prazo** na coluna direita (reusa `project.deadline`, dias restantes coloridos); Status em uma linha; campo de criar tarefa compacto; subtarefa por ícone "+"; **transição de conclusão** (`.task-completing` fade+strike) antes de sair da lista; cards de tarefa com mais padding.

### ✅ SCRIPT 8 — Importância ponderada + foco do dia
- **Critérios por contexto** (`criterio_contexto`, máx. 3, peso + `inverter`) e **valores por tarefa** (`tarefa_criterio_valor`); `tasks.importancia`/`sem_nota`. Cálculo + faixas em `services/importancia_service.py`; seed inicial no lifespan (`criterio_repo.seed_defaults`).
- **Config em `/settings`:** seção "Critérios de importância" (1 card por contexto, linhas dinâmicas Alpine, "Salvar critérios" → `POST /api/settings/criterios/{id}` faz replace).
- **Obrigatoriedade:** seletor 0-5 (`partials/criterio_selector.html`, radios `required`) na criação/edição de tarefa de topo com contexto que tem critérios; no **Processar**, contexto obrigatório + critérios dinâmicos por contexto. Persistência/validação em `api/tasks` e `api/capture` via `ImportanciaService`.
- **Foco do dia:** `users.foco_do_dia` (singleton) editável no topo do Dashboard (`partials/foco_do_dia.html`, `PATCH /dashboard/foco`).
- **Dashboard (Prioridades):** três grupos (Atrasadas/Hoje/Alta), máx. 3/grupo (+expandir), resumo com bolinhas, pills de filtro (Todos/Atrasado/Hoje/Alta), cards ricos (projeto, urgência, `alta · X.X`, esforço `⏱`, `⚠` sem nota, **adiar**), ordenação intra-grupo por importância e **polling 30s** sem reload (`partials/dashboard_priorities.html` + `dashboard_task.html`, `GET /dashboard/priorities`, `PATCH /api/tasks/{id}/adiar`).
- Migração aditiva: SQLite (`_ENSURE_COLUMNS` tasks/users) + PG (`_ENSURE_COLUMNS_PG` tasks/users); tabelas novas via `create_all`.

### ✅ SCRIPT 9 — Redesign visual de lista de tarefas
- **Partial unificado `task_item.html`:** substitui tanto o antigo `task_item.html` (projeto/dashboard-overload) quanto o `dashboard_task.html` (dashboard-prioridades). Um único componente renderiza tarefas em todos os contextos.
- **Visual denso (estilo Todoist):** itens sem card individual; separador `border-b border-oriens-divider`; sem `mb-2` entre itens; hover com `bg-oriens-card-hover rounded-md transition-colors`; ações aparecem com `opacity-0 → opacity-100 duration-150`.
- **Checkbox com cor de urgência:** borda assume `border-oriens-urgent` (atrasado) ou `border-oriens-today` (hoje) — calculada via `due_status` no topo do partial. Concluído: check `text-oriens-success` com `bg-oriens-success/20`.
- **Badges condicionais** (só rendem quando o dado existe): projeto `📁` (11px muted), urgência (atrasado·Nd / hoje, fundo translúcido), importância `alta · X.X` (`text-oriens-accent bg-oriens-accent/10`, só faixa alta), `⚠` sem nota, esforço `⏱` (11px muted), quick win, contexto, tags, lembrete 🔔.
- **Flags via `{% with %}`** (composição sem código duplicado):
  - `allow_subtask` — botão "+" de subtarefa (usado em `task_with_subtasks.html`)
  - `show_importancia` — mostra badge de importância (projeto e dashboard)
  - `show_project` + `project_map` — badge 📁 com nome do projeto (dashboard)
  - `show_adiar` — botão "adiar" no hover + campo de data Alpine (dashboard)
  - `refresh_priorities` — ao concluir, dispara `htmx.trigger(body,'refreshPriorities')` em vez de remover DOM após 450ms
- **`dashboard_task.html`** virou thin wrapper (3 linhas) que chama `task_item.html` com `show_project=true, show_importancia=true, show_adiar=true, refresh_priorities=true`. A rota e o `dashboard_priorities.html` não mudam.
- **`capture_item.html`** atualizado para o mesmo estilo visual (border-b, hover bg, data em 11px) — mantém modelo `CaptureInbox`, sem checkbox.
- **`process_item.html`** — cabeçalho (texto/data) alinhado visualmente (`leading-snug`, data `text-[11px]`).
- **Containers** trocados de `px-4` para `px-1 py-1` onde itens entravam (`dashboard.html` overload/minimal/quick-wins/bloqueios, `dashboard_priorities.html` inner div). Tarefas concluídas no `detail.html` ganharam wrapper `bg-oriens-card rounded-lg px-1 py-1`.
- **Sem migrações de schema** — mudança puramente de templates.

### ✅ SCRIPT 10A — Base técnica para projetos executáveis
- **`tasks.order_index`** (Integer, nullable): ordem manual das tarefas de **topo de projeto**. NULL em tarefas avulsas e subtarefas (que ignoram o campo). Migração aditiva em SQLite (`_ENSURE_COLUMNS`) e PG (`_ENSURE_COLUMNS_PG`); inicialização idempotente das tarefas existentes (0,1,2… por `id` asc dentro de cada projeto) em `_migrate_data` (SQLite) e `_ensure_columns_postgres` (PG, `ROW_NUMBER`).
- **`task_repo`:** `get_all_by_user(project_id=...)` ordena por `nullslast(order_index)`; novos métodos `get_project_next_task`, `get_max_order_index`, `reorder_project_tasks` (valida ownership + pertencimento ao projeto + rejeita avulsas/subtarefas).
- **`task_service.create`:** tarefa de topo de projeto nasce com `order_index = max+1` (append ao fim).
- **`project_service.get_project_next_action`:** 1ª tarefa pendente em ordem manual → fallback `project.proxima_acao` → não executável. Importância de tarefa de projeto **não** é usada na execução.
- **Endpoint** `PATCH /api/projects/{id}/task-order` (JSON `{task_ids:[...]}`): persiste `order_index`.

### ✅ SCRIPT 10B/10C — UI de execução do projeto + executabilidade na lista
- **Detalhe do projeto reorganizado em torno da execução:** Cabeçalho (nome/status/prioridade/contexto/arquivar) → **Próxima Ação operacional** → **Tarefas do Projeto** (no topo) → Detalhes/edição → Decisões → Atividade → Anexos.
- **Drag-and-drop** (SortableJS via CDN, só no `detail.html`): alça `.drag-handle` em `task_with_subtasks.html` (wrapper `.project-task-row[data-task-id]`); `onEnd` faz `fetch` PATCH `task-order`. Ordem manual persistida; concluídas recolhidas.
- **Importância/critérios ocultos para tarefas de projeto:** `task_form` incluído com `criterios=[]`; `task_with_subtasks` sem `show_importancia`; `api/tasks` (create/update/edit_form) **não** exige nem calcula critérios quando `project_id` presente. Avulsas mantêm tudo.
- **Conclusão de tarefa de projeto recarrega a página** (flag `reload_on_done` em `task_item`) → próxima ação/ordem atualizadas.
- **Lista de projetos:** `project_service.get_executability` (batched) → estado operacional por projeto (`completed | not_started | no_action | stalled | executable`) + próxima ação + pendentes + última atividade (`project_timeline_repo.last_activity_by_projects`, `task_repo.next_pending_tasks_by_project`/`pending_count_by_project`). `project_card` passou a exibir estado/próxima ação.

### ✅ SCRIPT 11 — Dashboard: projetos em foco × tarefas avulsas
- **Separação total** projeto × avulsa no Dashboard. Duas colunas: **Projetos em foco** (principal, `lg:col-span-2`) e **Tarefas avulsas** (apoio).
- **`dashboard_service.get_projects_in_focus`:** projetos ativos não-arquivados ordenados por **prioridade**, cada um com a próxima ação operacional; projetos sem próxima ação só são contados (`without_next_count`, contador discreto). Respeita contexto (`project_repo.get_active_by_user(context_id=...)`, contexto antes de prioridade).
- **`dashboard_service.get_standalone_tasks`:** tarefas avulsas (`get_priority_pending(standalone_only=True)`); mantêm importância/energia/urgência/quick win; energia continua influenciando a ordem.
- **Fragmentos** `GET /dashboard/projects-focus` e `GET /dashboard/standalone` (recarregam em `refreshProjectsFocus`/`refreshPriorities`). Próxima ação de projeto concluível pelo Dashboard (timeline preservada). Sem lista de tarefas de projeto, sem importância de tarefa de projeto, sem drag-and-drop. Componentes antigos (`dashboard_priorities.html`, `/dashboard/priorities`) preservados mas não usados.

### ✅ SCRIPT 12 — Polimento: bloco "Agora", contraste e cards limpos
- **Bloco "Agora"** (`partials/dashboard_now.html` + `DashboardService.pick_now_action` + `GET /dashboard/now`): **uma única** ação dominante — próxima ação do 1º projeto executável em foco → senão, 1ª tarefa avulsa. Mostra título, origem (projeto/"Tarefa avulsa"), contexto, energia, concluir (se tarefa), "abrir projeto" (se de projeto). Auto-recarrega em `refreshProjectsFocus`/`refreshPriorities`.
- **Foco do dia:** vazio = compacto ("Definir foco do dia", sem caixa accent); preenchido = card accent. Form extraído para `partials/_foco_form.html`.
- **Dashboard:** data+energia em cabeçalho compacto; colunas viram apoio; card de projeto e avulsas mais limpos (`hide_actions` em `task_item` → avulsas só com checkbox/título/contexto/prazo/importância).
- **Título de tarefa:** validação de verbo **desativada** (`task_service` não chama mais `validate_starts_with_verb`; helper mantido). Qualquer título não vazio é aceito; vazio ainda bloqueado na rota. Removido o texto "Só o título…".
- **Prioridade como Alta/Média/Baixa** (sem P1/P2/P3) no detalhe, cards e selects (`detail`, `project_form`, `process_item`). Primeira tarefa pendente do projeto destacada como "Próxima ação" (flag `is_next`).
- **Lista de projetos simplificada:** nome, objetivo, próxima ação **ou** "Precisa de revisão" (discreto, não vermelho), progresso único ("X de Y concluídas"), prioridade/contexto/prazo. Vermelho só para atraso/urgência. Kanban mais leve, estados vazios padronizados (`oriens-secondary`).
- **Sem migração / sem novo módulo ou entidade.**

### ✅ SCRIPT 13 — Captura rápida + Criação direta + Captura por Telegram
- **Criação direta de tarefa avulsa simplificada:** os critérios 0-5 por contexto (SCRIPT 8)
  saíram da criação/edição/processamento de tarefa avulsa, substituídos por um seletor
  **Alta/Média/Baixa**. Mapeado no campo existente `tasks.importancia` via
  `importancia_service.importancia_from_prioridade` (Alta→5, Média→3, Baixa→1, `sem_nota=False`)
  — **sem migração**. Contexto passou a ser **obrigatório** na tarefa avulsa de topo
  (`api/tasks.create_task`/`update_task` e `task_form.html`/`task_edit_form.html`); a herança de
  contexto da tarefa de projeto não mudou. O badge de importância (`task_item.html`) mostra só
  "Alta" (sem decimal). Processar inbox idem (`process_item.html` + `api/capture.process_capture`
  + `capture_service.process_as_task(importancia=...)`).
- **Critérios de importância desativados:** seção em `settings.html` envolvida em `{% if false %}`
  (backend, rotas e tabelas `criterio_contexto`/`tarefa_criterio_valor` intactos — não-destrutivo);
  `CriterioContextoRepository.seed_defaults()` não é mais chamado no lifespan. `criterio_selector.html`
  ficou órfão (mantido). `ImportanciaService`/`calcular_importancia` permanecem para uso futuro.
- **Captura direta de tarefa avulsa no Dashboard:** `task_form.html` incluído na coluna "Tarefas
  avulsas" (`dashboard_standalone.html`), com contexto (default = contexto ativo, via
  `active_context_id`) + Alta/Média/Baixa; ao salvar dispara `refreshPriorities`.
- **Captura rápida global:** botão "Capturar" na sidebar + modal Alpine de campo único
  (`base_app.html`) que posta em `POST /api/capture`; atalho de teclado **`c`** (ignorado quando
  o foco está em input/textarea/select/contenteditable), `Esc` fecha, Ctrl/⌘+Enter envia.
- **Captura por Telegram (long polling):** `reminder_service.process_telegram_updates(db, offset)`
  consulta `getUpdates` (sem HTTPS/webhook), aceita **apenas mensagens do `TELEGRAM_CHAT_ID`**,
  cria captura para o usuário dono (`UserRepository.get_first()`) e responde "✓ Capturado".
  Loop de fundo `_telegram_capture_loop()` no lifespan (`main.py`), ao lado do de lembretes
  (premissa: 1 worker uvicorn). No-op se `TELEGRAM_*` vazios. Reusa `send_telegram` e `httpx`.
- **Sem migração de schema. Sem novo model/tabela.**

### ✅ SCRIPT 16A — Projetos orientados a tarefas (backend + estrutura)
- **`project_section` model/repo/endpoints:** seções nomeadas por projeto (order_index, cascade delete). Endpoints: `POST/PATCH/DELETE /api/projects/{id}/sections/{sid}`. Rename retorna o `<span id="section-name-{id}">` via HTMX outerHTML.
- **`tasks.section_id`** (FK → project_sections, nullable): tarefas de projeto podem ser associadas a uma seção. Migração aditiva SQLite + PG.
- **`detail.html` reestruturado (16A):** `#project-sections` (seções renderizadas via Jinja) + `#sem-secao-container` (tarefas sem seção). SortableJS inicializado em todos os `.section-task-list`. Formulário de edição simplificado (só Status/Prioridade/Contexto/Responsável). `proxima_acao` textual removida do backend de criação/edição (projeto é purely task-driven).
- **`routes/projects.py`:** constrói `section_groups` (lista de tuples `(section, tasks)`) e `sem_secao_tasks`; passa `responsavel_map` e `subtasks` ao template.
- **`routes/weekly.py`:** usa `pending_count_by_project` para exibir projetos `em_andamento` sem tarefas pendentes como "Projetos sem próxima ação" (`projetos_sem_proxima_acao`).
- **`weekly.html`:** seção renomeada de "sem atualização" para "Projetos sem próxima ação"; usa `projetos_sem_proxima_acao`.
- **Sem alteração de Dashboard, Captura, Listas ou regras de importância.**

### ✅ SCRIPT 16B — UI de Projetos Executáveis (somente templates)
- **`partials/project_card.html`:** card minimalista — acento de status, nome, rodapé com prioridade · contexto · prazo + ações hover (pausar/iniciar/concluir/reabrir). Removidos: objetivo, próxima ação textual, barra de progresso.
- **`partials/project_task_row.html`** (novo): linha densa estilo Asana para tarefas de projeto no detalhe e nas seções. Colunas desktop: drag(w-5) | checkbox(w-5) | Título(flex-1) | Energia(w-20) | Prazo(w-24) | Responsável(w-20) | ações hover. "↗ Próxima ação" acima do título quando `is_next`. Lembrete: `⏱ dd/mm hh:mm` (sem sino). Ações hover: bloquear/desbloquear · editar · arquivar · +sub. Subtarefas indentadas (`ml-10 border-l`). Substitui `task_with_subtasks.html` no contexto de projeto; **`task_with_subtasks.html` preservado** (usado pelo bloco "Agora" do Dashboard).
- **`partials/project_section.html`:** atualizado para usar `project_task_row.html`; `is_next` calculado por `task.id == next_action.task.id`.
- **`projects/detail.html`:** bloco "Próxima ação operacional" removido do topo; objetivo movido do sidebar para coluna principal (texto compacto + "Editar" inline ou "+ definir objetivo" como convite accent); cabeçalho de colunas discreto (Tarefa · Energia · Prazo · Responsável, `hidden md:flex`); `sem_secao_tasks` renderiza com `project_task_row.html`; objetivo removido do sidebar (mantidos: prazo, comentários, auditoria).
- **Sem alteração de banco, backend, rotas, serviços, Dashboard, Captura ou Listas.**

### ✅ SCRIPT 17 — Redesign: lista e detalhe de projetos (somente templates)
- **`projects/list.html`:** kanban de 3 colunas substituído por tabela `table-layout:fixed` com seções colapsáveis via Alpine.js (`x-data="{open:true}"` por `<tbody>`). Ordem de seções: Em andamento → Não iniciado → Concluído. Colunas: drag(24px) · Nome(auto) · Prioridade(90px) · Contexto(100px) · Prazo(110px) · Ações(80px). Chips de status (fundo colorido semântico) e prioridade (Alta/Média/Baixa com paleta própria). Prazo urgente em `#e08050`. Drag handle e botões de ação (`opacity:0→1`) visíveis apenas no hover. Projetos concluídos: `opacity:0.45` + nome riscado. Filtros (Ativos/Arquivados/Todos) viram tabs com sublinhado `#4573d2` na ativa. Botões HTMX Pausar/Iniciar/Concluir/Reabrir idênticos ao `project_card.html`. JS de resize de colunas via `.resizable-th`. Cores hardcoded em `<style>` local (paleta: `#1d1f21` fundo · `#25282a` card · `#404244` borda · `#4573d2` accent).
- **`projects/detail.html`:** layout de 2 colunas (main + aside) substituído por full-width `max-width:960px; padding:32px 40px; margin:0`. Sidebar (prazo/comentários/anexos) **removida**. Header: breadcrumb + h1 + botões Arquivar/Editar (chips de status/prioridade/contexto/prazo removidos — ver SCRIPT 17B). Formulário de edição (Alpine `x-show="editing"`, HTMX) preservado. Duas abas Alpine (`x-data="{editing:false, tab:'overview'}"`, sublinhado `#4573d2` na ativa): **Visão geral** — grid 2 colunas com cards `pj-card`; Objetivo (full-width, editável inline), Prazo (número grande + dias + Editar HTMX), Progresso (% grande + barra 6px), Decisões (full-width, input + lista HTMX), Comentários (full-width, textarea + lista HTMX), Anexos (full-width, upload HTMX). **Tarefas** — barra 3px de progresso + contador `X/Y·%` + cabeçalho de tabela com `.resizable-th` + estrutura existente de seções/`sem_secao_tasks`/bloqueadas/concluídas preservada; SortableJS idêntico. IA e riscos (`{% if false %}`) preservados.
- **Paleta local preservada (ambos os templates):** accent `#4573d2` (tab underline, btn "Novo projeto", hover nome, links de ação) · prazo urgente `#e08050` · hoje `#EF9F27` · sucesso `#5DCAA5`. Chips semânticos: Alta `bg:#3a1b1b text:#e07070` · Média `bg:#2e2010 text:#d4a040` · Baixa `bg:#1b3020 text:#50b880` · Em andamento `bg:#1b3a2a text:#4caf82 border:#2a5a3a` · Neutro `bg:#2a2d2f text:#9a9da0 border:#404244`. Todas as demais cores agora usam tokens `--oriens-*` (ver SCRIPT 17B).
- **Sem migração de schema. Sem alteração de backend, rotas, serviços ou outros templates.**

### ✅ SCRIPT 17B — Tema dark + tipografia + tokens (somente templates + theme.css)
- **`app/static/css/theme.css`:** `--oriens-accent` trocado de `#7F77DD` para `#ffffff` e `--oriens-accent-hover` para `#e0e0e0` nos blocos `[data-theme="dark"]` e `:root:not([data-theme])` (fallback). `--oriens-btn: #7F77DD` preservado. Temas `light` e `warm` **não alterados**. Impacto automático: botão "Capturar", tab ativa, progress bar, checkbox, badge "próxima ação" passam a usar branco no dark.
- **`base_app.html`:** sidebar usa exclusivamente tokens — "Sair do trabalho →" (`color: var(--text-secondary)`) e contexto ativo no picker (`color: var(--text-primary)`, `background: var(--bg-surface)`).
- **`projects/detail.html`:** linha de badges (status · prioridade · contexto · prazo · arquivado · responsável) **removida** do header. Tipografia: breadcrumb `12px/var(--oriens-secondary)`, h1 `18px/600/var(--oriens-primary)`. Cards Prazo e Progresso: número grande `24px/600` (era 28–36px/700), unidade `13px/400/var(--oriens-secondary)`. Bloco `<style>` completamente tokenizado: `.pj-card` usa `var(--oriens-surface)/var(--oriens-border)`; botões, labels, inputs, selects e `.tasks-th` usam tokens. Inline styles substituídos por tokens em todo o template: textareas (objetivo, comentário), separadores bloqueadas/concluídas, tracks de progresso, labels "Sem seção"/"Bloqueadas", textos vazios, wrapper concluídas.
- **`projects/list.html`:** bloco `<style>` completamente tokenizado — `.proj-table th`, `.proj-row td`, `.proj-row:hover td`, `.drag-handle`, `.proj-section-hdr td`, `.proj-btn` e variantes usam tokens. `.proj-section-hdr td` ganhou `padding-top: 24px` (mais respiro). Inline styles substituídos: h1, "Relatório →", tabs (divider + cores ativa/inativa), border do container, contadores de seção, nomes de projeto, contextos, prazos, "—" e empty states.
- **Preservados como hardcoded:** `#4573d2` (accent local de tabela), chips semânticos de prioridade/status, `#e08050/#EF9F27/#5DCAA5` (urgência/sucesso).
- **Sem migração de schema. Sem alteração de backend, rotas, serviços ou outros templates.**

### ✅ FIX — Aba Tarefas do detalhe de projeto (somente `projects/detail.html`)
- **Coluna "Tarefa" → "Nome"** no `<thead>`.
- **Nomes de seção sem uppercase:** CSS override em `detail.html` sobre o partial `project_section.html` — `[id^="section-name-"]` recebe `text-transform:none`, `14px/600/oriens-primary`, `letter-spacing:0`. Labels inline "Sem seção" / "Bloqueadas" / "Concluídas" também ajustadas (`14px/600`, sem `text-transform:uppercase/letter-spacing`).
- **Borda esquerda colorida removida:** CSS `.project-task-row.border-l-2 { border-left: none !important }` — elimina o acento roxo/branco na linha da próxima ação.
- **Badge "↗ Próxima ação" discreto:** CSS override em `.project-task-row .font-bold.uppercase` → `oriens-secondary`, `font-weight:400`, `text-transform:none`, `11px`.
- **Checkbox circular:** CSS `.project-task-row .w-4.h-4 { border-radius: 50% }`.
- **Hover de linha mais sutil:** CSS `.project-task-row:hover { background: rgba(255,255,255,0.03) }` substitui o `oriens-card-hover` padrão.
- **Espaço entre seções:** CSS `#project-sections > .mb-5 + .mb-5 { padding-top: 28px }`.
- **"+ Adicionar tarefa" em vez de input fixo (sem seção):** Alpine `x-data="{ showTaskForm: false }"` — mostra texto clicável por padrão; revela o `task_form.html` existente no clique e foca o input.
- **"+ Adicionar tarefa" nas seções (via JS):** script ao final de `detail.html` localiza `form[id^="task-form-section-"]`, oculta o form e injeta trigger clicável; ao submit HTMX bem-sucedido, volta para o trigger.
- **Botão `···` nas linhas de tarefa (via JS):** script injeta `.pj-ellipsis-btn` em cada `.project-task-row` e desabilita o `group-hover:opacity-100` do Tailwind no painel de ações via inline style; clique em `···` abre/fecha o painel existente (HTMX intacto); clique fora fecha.
- **Sem migração de schema. Sem alteração de backend, rotas, serviços ou outros templates.**

### ✅ BUGFIX 16B — Correções pós-SCRIPT 16B (checkbox + done_at)
- **Checkbox `project_task_row.html`:** alinhado com o padrão comprovado de `task_item.html` — `hx-on:click` adiciona `task-completing` imediatamente; `hx-on::after-request` usa chaves `{ }` (exigido pelo HTMX 1.9.12) + `window.location.reload()` quando `reload_on_done`. Botão "desfazer" (done→pending) trocado de `hx-swap="outerHTML"` para `hx-swap="none"` + reload (evitava substituir a row por `task_item.html` incorretamente). Mesmo padrão aplicado nos checkboxes de subtarefa.
- **`api/tasks.create_task`:** para tarefas de projeto, retorna `project_task_row.html` (era `task_with_subtasks.html`) — evita inconsistência visual entre tarefas existentes e recém-criadas no detalhe.
- **`done_at` timezone (PostgreSQL):** `datetime.now(timezone.utc)` (timezone-aware) causava `asyncpg.DataError` ao gravar em `TIMESTAMP WITHOUT TIME ZONE`. Corrigido para `datetime.utcnow()` (naive UTC) nos três locais: `task_service.mark_done`, `project_service.update` (conclusão de projeto), `task_repo.update`. Padrão agora consistente com o restante da codebase.

### ✅ DRAG & DROP — Mover tarefas entre seções + reordenar seções
- **Backend (repositórios):** `task_repo.reorder_section_tasks(project_id, user_id, section_id, task_ids)` — atribui `section_id` **e** `order_index` em uma operação (cobre reordenação interna e mover entre seções); `project_section_repo.reorder_sections(project_id, section_ids)` — reordena seções por `order_index`. Ambos validam ownership/pertencimento e retornam `bool`.
- **Backend (endpoints):** `PATCH /api/projects/{id}/section-tasks` (JSON `{section_id: null|int, task_ids: [...]}`) e `PATCH /api/projects/{id}/section-order` (JSON `{section_ids: [...]}`) em `routes/api/projects.py`. O endpoint antigo `PATCH /api/projects/{id}/task-order` é preservado (compatibilidade).
- **Frontend `partials/project_section.html`:** outer div ganhou `class="section-row"` e `data-section-id`; cabeçalho ganhou `.section-drag-handle` (⠿, visível no hover do grupo); task list ganhou `data-section-id`.
- **Frontend `projects/detail.html`:** `#task-list-pending` ganhou `data-section-id="null"`; script SortableJS reescrito — tarefas usam `group: {name:'project-tasks'}` para cross-section, `onEnd` chama `/section-tasks` (origem e destino quando há troca de seção); nova função `initSectionSortable` cria Sortable sobre `#project-sections` com handle `.section-drag-handle` e draggable `.section-row`, chama `/section-order`.
- **Sem migração de schema** — todos os campos (`order_index`, `section_id`) já existiam.

### ✅ SCRIPT 18 — Tarefas por seção + tab persistente no detalhe de projeto
- **Regra "toda tarefa pertence a uma seção":** removidos `#sem-secao-container` (bloco "Sem seção" + task_form avulso), bloco global "Bloqueadas" e bloco global "Concluídas" da aba Tarefas de `projects/detail.html`.
- **Bloqueadas e concluídas inline na seção:** `routes/projects.py` (`project_detail`) agora constrói `done_by_section` e `blocked_by_section` (dicts `{section_id: [tasks]}`) além do `tasks_by_section` já existente (pending). Ambos passados ao template. `project_section.html` renderiza, após as pendentes: bloqueadas da seção (sem drag) e concluídas da seção (inline, sem drag, `opacity-40`/riscado) — sem sub-grupo separado.
- **Sem reload ao concluir tarefa:** `reload_on_done` removido das chamadas de `project_task_row.html` em `project_section.html`; conclusão de tarefa usa o comportamento padrão (`setTimeout remove após 450ms`), sem `window.location.reload()`.
- **Tab ativo persistente:** `projects/detail.html` — `x-data` lê `localStorage.getItem('oriens-pj-tab') || 'overview'`; `x-init` com `$watch('tab', ...)` persiste no `localStorage`. Ao navegar entre Visão geral e Tarefas, a aba é lembrada.
- **Sem migração de schema. Sem novo endpoint.**

### ✅ CORREÇÕES PÓS-SCRIPT 18 — Bugfixes e melhorias de UX

#### Criação de projeto na lista (`/projects`)
- **Bug:** formulário "Novo projeto" travava — `hx-target="#projects-active"` não existia na `list.html` e o backend retornava `project_card.html` (div card) em vez de uma `<tr>`.
- **Correção:** adicionado `id="projects-active"` na `<tbody>` de "Em andamento" em `list.html`; `hx-swap` corrigido para `beforeend`; criado `partials/project_row.html` (nova `<tr>` no estilo da tabela); `POST /api/projects` agora retorna `project_row.html` com o nome do contexto (`ContextRepository.get_by_id`).

#### Edição do nome do projeto no detalhe (`/projects/{id}`)
- **Melhoria:** campo `name` adicionado no topo do formulário de edição Alpine (`x-show="editing"`) em `projects/detail.html`. O endpoint `PATCH /api/projects/{id}` já aceitava `name` — só faltava expor o campo.

#### Aba Listas — filtro de contexto (`/lists`)
- **Bug:** `get_standalone_tasks()` não filtrava por contexto — todas as tarefas avulsas apareciam independentemente do contexto ativo.
- **Correção:** `task_repo.get_standalone_tasks(user_id, context_id=None)` agora aceita `context_id` e aplica `_apply_context()` (mesmo padrão dos outros métodos do repo); `routes/lists.py` captura o `context_id` de `resolve_active_context()` e o passa ao método.

#### Caixa de Entrada — edição inline do título (`/capture`)
- **Melhoria:** conteúdo de cada captura agora é editável inline com clique direto no texto (Alpine `editing` state + form HTMX oculto). Enter salva via `PATCH /api/capture/{id}` (novo endpoint); Esc cancela. Novo método `CaptureRepository.update_content()` e novo partial `partials/capture_content_span.html` (retorno do PATCH com o span atualizado).

#### Caixa de Entrada — campos obrigatórios ao processar (`/capture` → "Decidir" → Tarefa)
- **Melhoria:** `Energia` e `Importância` no formulário de processamento de tarefa agora têm `required` e placeholder "Selecionar…" sem valor pré-selecionado — o browser bloqueia o submit se não forem preenchidos. `Contexto` já era `required`. Sem alteração de backend.

### ✅ AUDITORIA — Correção de bugs, limpeza, testes e preparo para produção multi-worker

Revisão completa do projeto em 5 fases (branch `refactor/producao-limpeza-bugs`, mergeada em `main`), cobrindo bugs reais, código morto, complexidade desnecessária, suíte de testes quebrada e lacunas de produção em escala. Cada fase foi um commit isolado; tudo aditivo e não-destrutivo (nenhuma tabela dropada, nenhum dado perdido).

**Fase 1 — Bugs:**
- **Datetime unificado** (`app/utils/time.py`, novo): `utcnow()` (naive UTC, convenção única) / `now_local()` (só para lembretes). Corrige o bug real em `task_repo.overdue_by_project` — comparava `datetime.now(timezone.utc)` (tz-aware) com `Task.deadline` (coluna naive), quebrando a contagem de "atrasadas" no Postgres.
- **`Enum` nativo → `Enum(..., native_enum=False, length=50)`** em `Task.status/energy/cognitive_load`, `Project.status`, `ProjectRisk.impact/probability/status`. Elimina o risco de `ALTER TYPE` no Postgres ao introduzir um novo valor (documentado como risco futuro na seção "FUTURO" abaixo — agora mitigado). Colunas Postgres pré-existentes são convertidas de `ENUM` nativo para `VARCHAR` automaticamente (`_PG_ENUM_TO_VARCHAR` em `database.py`).
- **Upload de anexo seguro** (`api/projects.upload_attachment`): valida ownership do projeto (antes, qualquer usuário autenticado escrevia em `/attachments/{project_id}/` de qualquer projeto), limite de 20MB lido em blocos (antes, `await file.read()` carregava o arquivo inteiro em memória) e allowlist de extensão.
- **Logging** (`app/logging_setup.py`, novo): `dictConfig` + troca dos `except Exception: pass` (loops de fundo, migrações) por `logger.exception(...)` — falhas deixam de ser invisíveis.
- **Guard de `SECRET_KEY`:** `check_production_secrets()` aborta o boot se `DEBUG=false` e `SECRET_KEY` ainda for o valor padrão do repo — impede subir em produção com uma chave JWT forjável.

**Fase 2 — Remoção de código morto:** subsistema de importância ponderada (`criterio_contexto`/`tarefa_criterio_valor`/`criterio_repo`/`ImportanciaService`, desativado desde o SCRIPT 13 e sem leitor vivo), `verb_validator.py` (import morto desde o SCRIPT 12), rota `/dashboard/priorities` + `get_priorities_grouped` (dashboard atual não a usa desde o SCRIPT 11), partials órfãos (`task_with_subtasks.html`, `dashboard_priorities.html`, `dashboard_task.html`, `criterio_selector.html`).

**Fase 5 — Testes:** a suíte antiga estava quebrada (importava `app.models.mission`, módulo removido no SCRIPT 1; cookie `pos_token` legado; título "POS"). Reescrita do zero: `tests/conftest.py` corrigido (cookie `oriens_token`, `StaticPool` para SQLite in-memory) + suíte nova focada (auth/http, dashboard, projetos+seções+executabilidade, tarefas, captura, importância, lembretes, telegram) — **39 testes**, todos verdes.

**Fase 3 — Simplificação:** `_ENSURE_COLUMNS_PG` sincronizado 1:1 com `_ENSURE_COLUMNS` (o dict do Postgres omitia várias colunas que o SQLite já adicionava — risco real de schema divergente num Postgres pré-existente); dedupe no `task_repo` (escada de ordenação de tarefas de projeto repetida 3× → `_project_task_order()`; validação de reorder duplicada → `_load_reorderable_tasks()`); `CaptureRepository.get_unprocessed` agora delega a `get_inbox` (eram idênticas); os dois handlers `htmx:afterSettle` de `detail.html` consolidados em um só.

**Fase 4 — Produção multi-worker/multi-usuário:**
- **`app/worker.py`** (novo): os loops de lembrete/Telegram saíram do `main.py` para um processo dedicado — o web (`gunicorn -k UvicornWorker -w 3`, era `uvicorn` single-process) pode escalar sem duplicar envios/updates.
- **`init_db` multi-worker-safe:** `pg_advisory_xact_lock` serializa migração/seed entre processos/workers; seed de contextos passou a rodar dentro do `init_db` (`_seed_contexts`).
- **Índices** em colunas quentes: `tasks.deadline/remind_at/status/archived/section_id`, `capture_inbox.processed`.
- **Pool de conexões** (Postgres): `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`, `pool_recycle=1800`.
- **`/health` com ping real** no banco (503 se cair); `healthcheck` do serviço `app` no `docker-compose.prod.yml`.
- **Telegram por usuário:** `users.telegram_chat_id` (nullable). Captura e lembretes roteados ao dono do chat; fallback ao `TELEGRAM_CHAT_ID` global do `.env` preserva o comportamento single-user existente sem exigir configuração. UI em `/settings` → seção "Telegram".
- **Front sem CDN:** Tailwind, HTMX, Alpine.js, SortableJS e a fonte Inter auto-hospedados em `app/static/vendor/` (mesmos bytes das versões usadas — sem mudança visual). ~~`sw.js` (v2) pré-cacheia e cacheia-no-fetch → PWA funciona offline de verdade~~ — **falso**: o SW nunca teve escopo `/`, nunca controlou as páginas; foi **removido** (ver "FIX — site servindo versão antiga").
- **nginx:** `limit_req` no `/auth/login` (5 req/min por IP) + `location /static/` servindo os arquivos direto (tira o Python do caminho dos assets).
- **Dependências:** `python-multipart` 0.0.12→0.0.18 (corrige CVE-2024-53981), `jinja2` 3.1.4→3.1.6, `anthropic`/`openai` pinados (eram `>=`), `gunicorn` adicionado.

**Deixado de propósito fora do escopo** (risco maior ou exige validação visual/humana): refactor profundo dos controles injetados por JS em `detail.html` (trigger "+ Adicionar tarefa", botão `···`, chevron — hoje via DOM surgery, migrar para markup puro fica para um passo futuro validado em navegador); tokenização das cores hardcoded do SCRIPT 17 (`#4573d2` etc.); troca de `passlib`→`bcrypt` direto (evita só um warning cosmético no boot, mexe no hashing de senha).

**Impacto no deploy:** o próximo `git pull && docker compose -f docker-compose.prod.yml up -d --build` na VPS passa a subir **3 serviços** (`db`, `app` com gunicorn, `worker`) em vez de 2. Ver `DEPLOY.md` para o procedimento e o rollback.

### ✅ SCRIPT — Listas personalizadas + tudo como tarefa

`/lists` deixou de misturar 3 entidades (tarefas avulsas + Notas + Repositório) e virou **uma área de listas de tarefas**, uma lista por vez, com menu interno à esquerda e a lista ativa à direita. **Notas e Repositório agora são Tasks** dentro de listas internas; o usuário pode criar/renomear/arquivar **listas personalizadas** e mover tarefas entre listas. Links no título de uma tarefa passam a exibir o **título da página/vídeo** em vez da URL crua. **Projetos continuam totalmente separados.** Aditivo e não-destrutivo (tabelas `notes`/`repository_items` legadas preservadas; nada é dropado).

- **Modelo `TaskList`** (`app/models/task_list.py`): `id, user_id, name, order_index, archived, system_key (nullable), created_at, updated_at`. `system_key ∈ {notes, repository}` marca listas internas; `NULL` = lista personalizada. A lista padrão "Tarefas avulsas" **não** é uma linha — é `tasks.list_id IS NULL`.
- **`Task` ganhou** `list_id` (FK → task_lists, `ondelete=SET NULL`, nullable), `link_url`, `link_title`, `link_checked_at`. `title` ampliado de `VARCHAR(255)` → `VARCHAR(2000)` (comporta notas longas migradas). `list_id` só vale para tarefa avulsa de topo (projeto/subtarefa ⇒ `NULL`).
- **Migração de schema** (`database.py`): colunas novas em `_ENSURE_COLUMNS`/`_ENSURE_COLUMNS_PG`; no PG, `ALTER TABLE tasks ALTER COLUMN title TYPE VARCHAR(2000)` (guardado por `information_schema`); índice `ix_tasks_list_id`.
- **`TaskListRepository`** (`app/repositories/task_list_repo.py`): `get_active_by_user`, `get_by_id`, `get_system_list`, `ensure_system_lists` (idempotente, cria Notas/Repositório se faltarem, não recria arquivadas), `create`, `update_name` (recusa vazio; **bloqueia renomear lista interna**), `archive` (marca `archived=true` e **move as tarefas da lista para `list_id=NULL`** — não apaga).
- **`TaskRepository`:** `get_standalone_tasks` → **`get_standalone_by_list(user_id, list_id, context_id)`** (`list_id=None` = lista padrão avulsas); `count_standalone_default`, `count_by_list`. **`get_priority_pending(standalone_only=True)` passou a exigir também `list_id IS NULL`** → Notas/Repositório/personalizadas **não vazam** para o Dashboard/bloco "Agora".
- **Migração de dados** (`app/services/list_migration.py`, chamada no lifespan do `main.py` após `init_db()`): para cada usuário garante as listas internas e converte **notas avulsas** e **itens de repositório** antigos em Tasks (lista notes/repository), preservando `created_at`. Idempotente (dedupe por `user_id+list_id+title+created_at`); **não apaga** os registros originais. Itens de repositório que são link recebem `link_url`/`link_title`/`link_checked_at`. Guardado por `pg_advisory_xact_lock` distinto (multi-worker).
- **Helper de link** (`app/utils/link_meta.py`): `extract_url` (só `http/https`; bloqueia `localhost`, IP privado/loopback/reservado, `file://`), `fetch_link_title` (og:title → `<title>`, timeout 5s, segue redirect **revalidando o host final** contra SSRF, lê no máx. ~200KB, só `text/html`, **nunca levanta** — falha ⇒ `None`), `prepare_task_link_metadata` (normaliza/limita a 300). Busca só na criação/edição, **nunca na renderização**.
- **API de tarefas** (`routes/api/tasks.py`): `create_task`/`update_task` aceitam `list_id` (`""`/`default`/`null` ⇒ padrão; valor ⇒ valida ownership). Tarefa dentro de lista dispensa contexto e fica **sem nota** (importância só para avulsa de topo **sem** lista). Metadados de link resolvidos ao criar/editar (só quando o título muda no update). `edit_form` expõe o seletor **Lista** (Tarefas avulsas / Notas / Repositório / personalizadas) só para tarefa avulsa de topo. `_task_row_response` renderiza `task_item.html` com `clamp_title` (notas) ou `show_link` (repositório) conforme a lista.
- **Endpoints de lista** (`routes/api/lists.py`): `POST /api/lists` (cria; `HX-Redirect` p/ `/lists?list={id}`), `PATCH /api/lists/{id}` (renomeia; 400 em vazio/lista interna), `DELETE /api/lists/{id}` (arquiva; `HX-Redirect` p/ `/lists`). Rotas legadas `POST/DELETE /api/repository` **mantidas** (não usadas por `/lists`).
- **Tela** (`routes/lists.py` + `templates/lists.html`): navegação por link (`?list=`), uma lista renderizada por vez (server-side); menu com contadores, ações de hover (editar/arquivar) em listas personalizadas e "+ Nova lista" (input inline Alpine). `partials/list_task_form.html` (criação por lista; contexto+importância só na padrão). Item de repositório: `link_title` como link (`target="_blank"`) + domínio discreto (`url_domain`, novo global Jinja em `templates_env.py`); nota truncada em 2 linhas (`line-clamp-2`).
- **Caixa de Entrada:** `process_as_note`/`process_as_repository` **inalterados** (ainda gravam nas tabelas legadas); a migração de boot os reconcilia como Task no próximo restart (idempotente). Fora do escopo deste script.
- **Sem alteração** de Dashboard, Projetos ou Configurações. 33 testes verdes.

#### FIX — Deadlock na migração de listas com múltiplos workers do gunicorn (pós-deploy)

Produção com 3 workers gunicorn rodando o lifespan em paralelo expôs um **deadlock real** no primeiro deploy: `migrate_notes_and_repository_to_tasks` mantinha uma transação aberta durante `fetch_link_title` (chamada HTTP), colidindo com outro worker fazendo `ALTER TABLE tasks ALTER COLUMN title TYPE VARCHAR(2000)`. A migração **completou com sucesso** mesmo assim (retries idempotentes), mas o risco de recorrência ficava latente a cada novo item de repositório + deploy futuro.

- **`app/services/list_migration.py`:** a advisory lock própria (`825739301`) foi trocada pela **mesma** `_MIGRATION_LOCK_KEY` (`825739201`) usada pelo DDL de `init_db()` — serializa migração de schema e de dados entre todos os workers.
- **`_migrate_repository_items`:** reordenada em 3 passos — (1) resolve o que falta migrar só com SELECTs (sem I/O de rede), (2) busca todos os `fetch_link_title` (rede) **antes** de montar qualquer `Task`, (3) monta os `db.add(...)` e faz um único commit — elimina INSERTs pendentes/locks na transação durante a chamada HTTP lenta.
- Validado com segundo deploy na VPS: boot sem nenhum erro, contagens de dados idênticas (zero duplicatas).

### FIX — Alinhamento das tarefas concluídas na aba Tarefas do projeto

Tarefas concluídas (e bloqueadas) de uma seção eram renderizadas em `partials/project_section.html` **fora** do `<div class="section-task-list pl-2">` que envolve as pendentes — perdiam o recuo esquerdo e quebravam o alinhamento das colunas (drag/checkbox/nome/energia/prazo/responsável) em relação às pendentes acima.

- **Correção cirúrgica:** o loop de "Concluídas da seção" passou a renderizar dentro de um `<div class="pl-2">` (mesma classe do container de pendentes) — sem tocar em `project_task_row.html`, que **já** usa uma única estrutura de linha para todo status (`pending`/`blocked`/`done`), variando só classes visuais (`opacity-40`, título riscado, checkbox preenchido). Nenhuma bifurcação estrutural existia para remover.
- **Bloqueadas** não foram tocadas (mesmo padrão, fora do escopo pedido).
- Sem alteração de backend, rotas, Dashboard, Listas ou listagem de Projetos. 33 testes verdes.

### ✅ SCRIPT — Listas unificadas (tudo é Task comum)

Eliminada qualquer diferença entre **Tarefas avulsas, Notas, Repositório e listas personalizadas** em `/lists`: tudo é uma `Task` comum, a lista (`list_id`) é **só agrupamento**. Sem novo model/tabela/rota; nada de dados apagados (tabelas legadas `notes`/`repository_items` preservadas).

- **`templates/lists.html`:** renderização de item unificada — todas as listas usam `partials/task_item.html` com os mesmos flags (`show_importancia=True, show_link=True`). Removida a bifurcação por `active_kind` (`clamp_title`/`show_link`/`show_importancia` por tipo). Destaque do menu lateral usa `active_list_id` (não mais `active_kind`).
- **`routes/lists.py`:** removida a variável `active_kind` e os títulos/placeholders especiais ("Nova nota"/"Nova referência") — derivam só do nome da lista. **O contexto ativo filtra todas as listas igualmente** (antes só a lista padrão respeitava o contexto).
- **`partials/list_task_form.html`:** mesmo formulário para todas as listas (título + contexto obrigatório + importância). Removido o `{% if not active_list_id %}`.
- **`routes/api/tasks.py`:** contexto obrigatório e importância atribuída para **qualquer** tarefa avulsa de topo (removido o caso especial `is_in_list` em `create_task`/`update_task`). Em `_task_row_response`, o item avulso sempre renderiza com os mesmos flags (removido o lookup de `system_key` notes/repository).
- **`services/capture_service.py`:** `process_as_note`/`process_as_repository` passaram a **criar Task** nas listas internas Notas/Repositório (via `_system_list_id` + `process_as_task`), com detecção de link global. Não gravam mais em `Note`/`RepositoryItem`.
- **Detecção de link é global à Task** (não da lista): qualquer tarefa avulsa de topo com URL no título recebe `link_url`/`link_title`; o **display** do link (`show_link`) agora vale para todas as listas.

### ✅ SCRIPT — Caixa de Entrada simplificada (4 destinos)

A tela "Decidir como" (`partials/capture_decide.html`) mostra **apenas 4 ações**, na ordem: **Descartar · Tarefa de projeto · Projeto · Listas**. Removidos os destinos diretos "Tarefa avulsa", "Nota" e "Repositório" — tudo vira Task (o `list_id` define a lista; Notas/Repositório/avulsas são só listas).

- **Caixas flutuantes (Alpine)** pequenas para "Tarefa de projeto" (lista projetos ativos, linha simples → cria Task com `project_id`, contexto herdado, sem `list_id`) e "Listas" (Tarefas avulsas + Notas + Repositório + personalizadas → cria Task na lista escolhida, `list_id` NULL = avulsas). Fecham ao escolher (o item é trocado no swap), ao clicar fora (`@click.outside`) e com Esc (`@keydown.escape.window`); tokens `oriens-surface/border/primary/secondary/card-hover`, sem ícones, sem cor nova.
- **"Projeto"** mantém o formulário inline; **"Descartar"** mantém o post direto. Sem reload completo (swap do próprio item).
- **`routes/api/capture.py`:** `decide_capture` busca as listas e um `default_context_id` (ativo → 1º disponível) para o clique único. `process_capture` ganhou `list_id` (valida ownership; só tarefa de topo não-projeto) e o repassa a `process_as_task`.
- **`services/capture_service.py`:** `process_as_task` aceita `list_id` e resolve link (global à Task). Nenhuma captura nova grava em tabela legada de notas/repositório. Endpoints legados preservados (fora de uso pela UI).

### ✅ SCRIPT — Prioridade Máxima (projetos + tarefas avulsas/listas)

Quatro níveis de prioridade: **Máxima > Alta > Média > Baixa**, acima de Alta em ordenação, selects e exibição. **Sem novo model/tabela/enum e sem migração** (os campos existentes comportam o novo valor).

- **Projetos** (`projects.priority`, inteiro, **menor = mais prioritário**, ordenado `priority.asc()`): **Máxima = 0**, Alta = 1, Média = 2, Baixa = 3. Validações em `project_service.create`/`update` e `schemas/project.py` passaram de `(1,2,3)` → `(0,1,2,3)`. Ordenação (listagem/detalhe/Dashboard via `get_active_by_user`) coloca Máxima primeiro automaticamente. `priority_label` `{0:'Máxima',...}` em `detail.html`, `project_card.html`, `project_kanban_card.html`. Selects de prioridade ganharam "Máxima" (`project_form`, `detail`, `capture_decide`, `process_item`).
- **Tarefas avulsas/listas** (`tasks.importancia`, float, **maior = mais prioritário**, ordenado `importancia.desc()` e `_priority_sort_key`): `importancia_from_prioridade` mapeia **`maxima`→6.0**, `alta`→5.0, `media`→3.0, `baixa`→1.0. `faixa_importancia` ganhou a banda `maxima` (≥5.5); `alta` continua 4–5. Selects ganharam "Máxima" (`list_task_form`, `task_form`, `task_edit_form`, `process_item`). Exibição: badge "Máxima" discreto em `task_item.html` (`bg-oriens-accent/15`, `font-semibold` — um passo acima de "Alta", **sem vermelho**), meta em `dashboard_standalone_task.html`, label em `task_detail_drawer.html`.
- **Tarefas de projeto:** intocadas — sem prioridade própria, sem seletor, **ordem manual de execução preservada**. A Máxima aplica-se ao projeto, não às tarefas internas.
- **Visual:** vermelho segue reservado a atraso/urgência real. Testes: 3 novos em `test_importancia.py` (Máxima=6.0, Máxima>Alta, faixa 6.0→maxima). Suíte: **36 testes verdes**.

---

### ✅ SCRIPT — Painel de detalhe da tarefa (drawer estilo Asana)

Substitui a edição **inline** (`task_edit_form.html`, aberta por `/edit` trocando o `outerHTML` da linha) por um **drawer lateral** que abre ao clicar no título de qualquer tarefa, em qualquer lista (Dashboard, detalhe de projeto, Listas). O drawer reúne todos os metadados do form inline **+ Descrição** (campo novo) **+ Subtarefas**. Autosave: cada `change` num campo dispara o PATCH, sem botão salvar.

- **`tasks.description`** (text, nullable): migração aditiva em `_ENSURE_COLUMNS` (SQLite) e `_ENSURE_COLUMNS_PG` (PG, sincronizados 1:1); campo `Text` em `models/task.py`. `update_task` aceita `description` (guardado por `is not None` — um PATCH sem o campo **não** apaga a descrição existente).
- **`GET /api/tasks/{id}/panel`** → `partials/task_detail_panel.html`: mesmo contexto que o `/edit` montava (contexts, labels, users, `prioridade`, `is_standalone_top`, listas) + subtarefas via `TaskRepository.get_children_map`.
- **Drawer global** em `base_app.html`: `taskDrawerOpen` no `x-data` da raiz; painel `fixed` à direita, carregado por HTMX em `#task-drawer-content`; fecha em `Esc`, `✕` e clique fora.
- **Gatilho** (título → `<button hx-get=.../panel @click="taskDrawerOpen=true">`) em `task_item.html`, `project_task_row.html`, **`dashboard_standalone_task.html`** e **`dashboard_project_card.html`** (estes dois têm markup próprio, fora do `task_item` — necessários para cobrir o Dashboard). Botão "editar" removido dos dois primeiros. O branch `<a>` de link externo (Repositório) **não** foi tocado.
- **Prioridade e Lista no painel** (paridade com o form inline): sem eles, o autosave rebaixaria toda tarefa Máxima para Média (o `prioridade` recalcula `importancia` em `update_task`). Travado por teste (`test_panel_patch_preserves_maxima`).
- **Removido:** `partials/task_detail_drawer.html` + rota `GET /{id}/detail` (drawer somente-leitura, **nunca** referenciado — código morto). **A referência a `task_detail_drawer.html` no bloco "Prioridade Máxima" acima ficou obsoleta.**
- **Fluxo inline antigo removido** (após validar o drawer em prod): `task_edit_form.html`, rotas `GET /{id}/edit` e `/cancel-edit`. O botão "editar" da subtarefa (`project_subtask_row.html`) também passou a abrir o drawer; o título da subtarefa virou gatilho do `/panel`. O `/panel` é o único fluxo de edição de tarefa.
- Verificação: **48 testes** verdes + drive end-to-end no navegador (Playwright): abrir/fechar (Esc/✕/fora), autosave de descrição+energia com persistência, Máxima não rebaixada, contexto "herdado" em tarefa de projeto (sem Lista/Importância), subtarefa via drawer, temas dark/light. Sem novo model/tabela.

---

### ✅ SCRIPT — Produção em larga escala (branch `refactor/producao-larga-escala`)

Preparação completa para rodar liso em escala, em 6 commits isolados (aditivo, não-destrutivo, nada dropado). Suíte foi de 50 → **87 testes** verdes + smoke end-to-end no navegador (Playwright, 13/13).

**Fase 1 — Segurança:**
- **SSRF corrigido em `utils/link_meta.py`:** hostname é resolvido via DNS e TODOS os IPs validados (antes só IP literal era bloqueado — domínio resolvendo p/ 169.254.169.254 passava); redirects seguidos **manualmente** (máx. 3) com validação de URL+DNS a cada hop ANTES do request (eliminou o TOCTOU da revalidação pós-redirect). Contrato "nunca levanta, retorna None" preservado.
- **XSS armazenado corrigido nas etiquetas:** `_label_html` (f-string crua) → `partials/label_item.html` (autoescape Jinja), usado no POST e em `settings.html`; cor validada como `#RRGGBB` (inválida → `DEFAULT_LABEL_COLOR`) e sanitizada também na renderização (global Jinja `safe_hex` — cores maliciosas podem já estar persistidas).
- **Nginx DENTRO do compose de prod** (`nginx/oriens-docker.conf` + serviço `nginx:1.27-alpine` na porta 80): rate-limit no login, gzip, headers de segurança, `/static/` direto do disco. **Cutover em 2 deploys** (porta 8000 pública mantida no 1º; fechar p/ `127.0.0.1:8000:8000` no 2º) — ver DEPLOY.md.

**Fase 2 — Performance/banco:**
- **Paginação "carregar mais"** (HTMX, `?offset=`, busca page+1 p/ `has_more`; fragmento via header `HX-Request`): Caixa de Entrada e Lixeira (50/página; contador via COUNT real) e Listas (100/página). Partials novos: `capture_page/trash_page/list_tasks_page.html`.
- **Guard-rails sem UI:** `task_repo.get_all_by_user` `limit=500`; `project_repo.get_all_by_user/get_active_by_user` `limit=200`.
- **Detalhe do projeto:** concluídas buscadas à parte, limitadas às **50 mais recentes** (`get_project_done_tasks`; pendentes/bloqueadas via `exclude_done=True`); nota "Mostrando as 50..." quando cortado (flag `done_capped`).
- **N+1 do reports eliminado:** `ProjectDecisionRepository.count_by_projects` + `ProjectRiskRepository.count_open_by_projects` (GROUP BY) — de `2+2N` p/ 4 queries.
- **Índices compostos:** `tasks(user_id,status,archived)`, `tasks(user_id,project_id,parent_id)`, `capture_inbox(user_id,processed)`.
- **Pool do PG parametrizado:** `DB_POOL_SIZE=5`/`DB_MAX_OVERFLOW=5` por processo (teto 40 conexões < `max_connections=100`; era até 120). `Dockerfile` sem `-w 3` — nº de workers via `WEB_CONCURRENCY` (default 3, ajustável sem rebuild).

**Fase 3 — Boot blindado + worker resiliente:**
- **`init_db`:** `SET LOCAL lock_timeout=5s / statement_timeout=120s` (só PG) após o advisory lock — boot que não pega lock **falha rápido** e o `restart: always` re-tenta (em vez de congelar o site); guards `SELECT..LIMIT 1` antes dos UPDATEs de `order_index`; log de duração. **`scripts/run_migrations.py`** roda `init_db()` isolado p/ migrações pesadas antes do cutover de container.
- **`list_migration`:** saída rápida por COUNT das tabelas legadas + cap de 20 `fetch_link_title` por boot.
- **Worker:** offset do Telegram persistido na tabela nova **`app_state`** (key/value — restart não reprocessa mensagens → sem capturas duplicadas); backoff exponencial até 300s nos 2 loops; **heartbeat** em `app_state` + healthcheck do serviço `worker` no compose (`scripts/worker_health.py`, falha se >5min).
- **`reminder_service`:** lote de 100 lembretes/ciclo + throttle entre envios; `send_telegram` trata 429 (retry_after, 1 retry) e loga status != 200.
- **`fetch_link_title` fora do request handler:** create/update de tarefa e processar captura gravam `link_url` na hora e buscam o título via **BackgroundTasks** (`services/link_title_service.py`).

**Fase 4 — Observabilidade + ownership:**
- Middleware de request logging (`método rota status latência`, logger `oriens.access`, pula /health e /static); `LOG_JSON=true` → uma linha JSON por evento (`JsonFormatter` stdlib).
- **`tests/test_ownership.py`:** usuário B atacando recursos de A → 4xx e dado intacto. Pegou 2 brechas reais (DELETE de decisão e resolve/discard/restore de captura retornavam 200 silencioso p/ não-dono) — corrigidas p/ 404.

**Fase 5 — UX/frontend:**
- **DOM surgery de `detail.html` (setupSectionForms/Collapse/Ellipsis) migrado p/ markup Alpine** em `project_section.html`, `project_tasks_panel.html` e `project_task_row.html` (trigger "Adicionar tarefa...", chevron `open`, botão `···` com `@click.outside`) — eliminou o leak de listener global por linha a cada re-render. Só o init do Sortable permanece em JS (idempotente, re-init em `htmx:afterSettle`).
- **Drag-drop com tratamento de erro:** falha no PATCH → aviso + `refreshProjectTasks` (re-render do banco = reversão). **Kanban de /projects sem reload:** drop dispara `refreshProjectsList` e o kanban se re-renderiza via `hx-select` na própria página. Branch `reload_on_done` removido (nenhum chamador).
- **BUGFIX (achado no smoke):** `hx-on::after-request` usava `$el.reset()`, mas htmx não define `$el` — o reset dos forms falhava silenciosamente com erro JS em todo submit. → `this.reset()` em 6 templates.
- **Cores hardcoded do SCRIPT 17 tokenizadas:** `--oriens-table-accent/success/warn/today` em `theme.css` (`:root`, mesmo valor nos 3 temas — **zero mudança visual**, preserva o 17B).
- **Cache-busting por build:** `APP_VERSION` (config + `ARG` no Dockerfile + build-arg no compose com git SHA) e `?v=` em todos os assets — **deploy de CSS/JS chega ao cliente sem bump manual**. ⚠️ O cache do nginx aplicado aqui (30d immutable **sem checar `?v=`**) causou o bug corrigido em "FIX — site servindo versão antiga" logo abaixo.

**Fase 6 — Código morto removido:** `process.html`, `partials/process_item.html`, `partials/repo_item.html`, `partials/project_card.html` (órfão; `PATCH /api/projects/{id}` agora responde vazio — todos os chamadores usam `hx-swap="none"`), endpoints `POST/DELETE /api/repository`, ramos `action=note/repository` + `process_as_note/process_as_repository` (Caixa de Entrada só tem 4 destinos desde o script "4 destinos"), `note_repo.py`/`repository_repo.py`, bloco `{% if false %}` de riscos em `detail.html` (backend de riscos mantido — reports usa `count_open`), **`alembic/` + `alembic.ini` + dep `alembic`** (abandonados; schema real vem de `_ensure_columns`). Models `Note`/`RepositoryItem` + `list_migration` mantidos por 1 ciclo com `# TODO remover`.

> **Config novas (.env, todas opcionais):** `DB_POOL_SIZE=5`, `DB_MAX_OVERFLOW=5`, `LOG_JSON=false`, `APP_VERSION` (via build-arg). **Deploy recomendado:** `APP_VERSION=$(git rev-parse --short HEAD) docker compose -f docker-compose.prod.yml up -d --build`.

### ✅ FIX — Site servindo versão antiga (cache do navegador) + service worker desligado

Após o deploy do script de larga escala, o app continuava mostrando **CSS/JS/comportamento antigos até um Ctrl+F5**. Causa raiz (medida com `curl` na VPS, não suposta):

1. **HTML sem nenhum header de cache** — `GET /auth/login` voltava `200` só com `Vary`; sem `Cache-Control`, `ETag` ou `Last-Modified`. O navegador reusava HTML antigo, que referencia assets **sem** `?v=`.
2. **Regressão do próprio script de larga escala:** o `location /static/` do nginx aplicava `expires 30d` + `immutable` a **qualquer** URL sob `/static/`, **inclusive sem `?v=`** → o asset antigo em URL estável ficava **congelado 30 dias** no navegador (e o `Cache-Control` saía **duplicado**: um do `expires`, outro do `add_header`).
3. **O service worker nunca controlou as páginas:** `base.html` registrava `/static/sw.js` **sem `scope`** → escopo `/static/` → o `fetch` handler jamais rodou em `/dashboard` etc. O "PWA offline de verdade" documentado era **ficção** (assim desde o primeiro commit).

**Correções:**
- **`app/main.py` — middleware `cache_control`:** `Cache-Control: no-store, no-cache, must-revalidate, max-age=0` em tudo que **não** é `/static/` (HTML, fragmentos HTMX, API, redirects de auth); `/static/` servido pelo app (dev) → `no-cache` (revalida por ETag). Rota que define a própria política tem precedência (escotilha via `if "cache-control" in response.headers`). Mata também o bug clássico do HTMX (browser cacheando resposta de `hx-get` e servindo o fragmento numa navegação normal). Efeito colateral **desejado**: `no-store` tira a página do bfcache — o botão voltar passa a buscar HTML fresco.
- **nginx (`oriens-ip.conf` **e** `oriens-docker.conf`) — cache por `map $arg_v`:** `?v=<sha>` → `public, max-age=31536000, immutable`; **sem** `?v=` → `no-cache`. `expires off` + **um único** `add_header ... always` elimina o header duplicado. (`map`, não `if` — `add_header` dentro de `if` tem herança traiçoeira no nginx.)
- **Service worker DESLIGADO:** `app/static/sw.js` **removido**; `base.html` não registra mais nada — só **desregistra os SWs órfãos** (`getRegistrations()`) e **apaga os caches legados** (`oriens-static-*`) nos navegadores dos usuários. `location = /static/sw.js` responde **404 com `no-store`** — e um 404 no script é o que faz o navegador descartar o registro antigo sozinho. O app **segue instalável** (manifest), agora sem cache offline.
- **Guard de `APP_VERSION`** (`logging_setup.check_asset_version`, chamado só no lifespan do web): aborta o boot se `DEBUG=false` e `APP_VERSION` for o fallback (`dev`/`prod`). É o que torna o `immutable` seguro — sem SHA, dois builds compartilhariam `?v=prod` e congelariam o asset antigo por um ano. Mesmo padrão do guard de `SECRET_KEY`.
- **`tests/test_cache_headers.py`** (7 testes) trava os invariantes: `no-store` em HTML/fragmento/redirect, `/static` nunca `immutable` pelo app, `/static/sw.js` → 404, e o guard de `APP_VERSION`. Suíte: **94 verdes**.

> **Limite honesto:** uma resposta **já gravada** no navegador como `immutable, max-age=30d` **não pode ser invalidada pelo servidor** — nenhum header futuro a desaloja. O HTML novo simplesmente deixa de apontar para ela. Por isso **um único `Ctrl+Shift+R` após este deploy** deixa o estado determinístico; a partir daí os deploys chegam sozinhos.

---

## PRODUÇÃO E OPERAÇÃO (VPS)

**Local na VPS:** `/opt/oriens` · **Acesso atual:** `http://IP_DA_VPS:8000`

**Serviços (pós-larga-escala):** `db` (PostgreSQL) + `app` (web, gunicorn — nº de workers via `WEB_CONCURRENCY`, default 3) + `worker` (processo único: lembretes + captura Telegram, com healthcheck por heartbeat) + `nginx` (porta 80: rate-limit no login, gzip, estáticos com cache 30d). Os loops de fundo **não** rodam dentro do `app` — se o `worker` cair, lembretes/Telegram param mas o resto funciona.

**Comandos do dia a dia** (na VPS, em `/opt/oriens`):
```bash
docker compose -f docker-compose.prod.yml ps                    # status (db, app, worker, nginx)
docker compose -f docker-compose.prod.yml logs -f app worker    # logs
docker compose -f docker-compose.prod.yml restart                # reiniciar
# atualizar (APP_VERSION = cache-busting dos estáticos/PWA):
git pull && APP_VERSION=$(git rev-parse --short HEAD) docker compose -f docker-compose.prod.yml up -d --build
```

**Regra de ouro:** ⚠️ **nunca** use `down -v` — o `-v` apaga o volume `pgdata` (perde conta/projetos/tarefas). Os dados sobrevivem a `restart`, `up -d --build` e reboot da VPS.

**Antes de cada deploy:** confira `.env` → `SECRET_KEY` **não pode** ser o valor padrão do repo com `DEBUG=false` (o app aborta o boot desde a AUDITORIA — guard proposital).

**Rollback rápido** (código é compatível para trás — migração é aditiva):
```bash
git rev-parse HEAD | tee .last_good_commit    # ANTES de cada deploy, guarda o estado atual
# se o novo deploy não subir como esperado:
git checkout "$(cat .last_good_commit)"
docker compose -f docker-compose.prod.yml up -d --build --remove-orphans   # remove o `worker` se voltar a código pré-AUDITORIA
```

**Persistência:** banco em `pgdata`; anexos em `appdata` (`/app/data/attachments`).

**Backup:** `bash scripts/backup.sh` (pg_dump + anexos, retém 7 dias). Agendar:
`0 3 * * * cd /opt/oriens && bash scripts/backup.sh >> /var/log/oriens-backup.log 2>&1`

---

## ESTATÍSTICAS DO PROJETO (ATUAL — PÓS AUDITORIA)

| Item | Quantidade |
|---|---|
| Tabelas no banco | 17 (+ `project_sections`; `criterio_contexto`/`tarefa_criterio_valor` removidas do código, tabelas legadas não dropadas) |
| Models SQLAlchemy | 15 (2 a menos que antes — critérios removidos) |
| Repositories | 15 (`criterio_repo` removido) |
| Services | 8 |
| Rotas principais | 6 arquivos |
| Rotas API | 7 arquivos |
| Endpoints totais | ~46 (`/dashboard/priorities` e `/api/settings/criterios` removidos; `/api/settings/telegram` adicionado) |
| Templates HTML | ~30 (4 partials órfãos removidos: `task_with_subtasks`, `dashboard_priorities`, `dashboard_task`, `criterio_selector`) |
| Temas | 3 (`dark`/`light`/`warm`) via `static/css/theme.css` |
| Testes | 87 (suíte reescrita na AUDITORIA + segurança/paginação/worker/ownership no script de larga escala) |
| Processos em produção | 3 serviços app (`app` multi-worker + `worker` único + `nginx`) |
| Dependências CDN | 0 (Tailwind/HTMX/Alpine/Sortable/Inter auto-hospedados) — era 5 |
| Ambiente | Dev (SQLite) + Produção (PostgreSQL na VPS) |

---

## 🔭 FUTURO (PLANEJADO, NÃO IMPLEMENTADO) — Dev em PostgreSQL (paridade com produção)

> **Status:** apenas documentado. Nada abaixo foi executado. O dev continua em SQLite.
> **Atualização (AUDITORIA):** o principal motivador original — os **`Enum` nativos** do PG que
> quebravam com `ALTER TYPE` ao adicionar um valor novo — **já foi mitigado**: todos os enums
> (`Project.status`, `Task.status/energy/cognitive_load`, `ProjectRisk.impact/probability/status`)
> agora usam `Enum(..., native_enum=False)` (mapeados como `VARCHAR`), e uma migração converte
> colunas Postgres pré-existentes automaticamente. O risco residual que sobra deste plano é bem
> menor: só a divergência de *dialeto* em si (funções SQL específicas, tipos de data) e o fato do
> caminho `_ensure_columns_postgres`/`_ensure_indexes` ainda não ser exercitado localmente no dia a
> dia. Este plano continua válido como forma de fechar essa lacuna, mas deixou de ser urgente.
>
> **Objetivos inegociáveis deste plano:** VPS intacta · PostgreSQL **só** para dev ·
> `docker-compose.prod.yml` e deploy **inalterados** · rollback trivial para SQLite.

### 1. Arquivos alterados/criados
- **Novo:** `docker-compose.dev.yml` (Postgres + app para dev). Volumes próprios `pgdata_dev`/`appdata_dev` — **nunca** os de prod.
- **Mantido como rollback:** `docker-compose.yml` (dev SQLite atual) permanece no repo, intocado.
- **`.env` (dev):** trocar `DATABASE_URL` para PG + adicionar `POSTGRES_PASSWORD` (senha de dev, diferente da prod).
- **`.env.example`:** passar a ter 3 blocos — DEV-SQLite (rollback), DEV-PostgreSQL (novo), PROD (inalterado).
- **NÃO muda:** `config.py` (default segue SQLite, por segurança), `database.py` (o caminho PG já existe), `requirements.txt` (`asyncpg` já presente), `docker-compose.prod.yml`, `.env` da VPS.
- **Opcional (follow-up separado):** `tests/conftest.py` (ver item 6) e, mais tarde, encolher o ramo SQLite do `database.py` / trocar `Enum` nativo por `String`.

### 2. `docker-compose.dev.yml` (rascunho de referência)
```yaml
# docker-compose.dev.yml — DESENVOLVIMENTO em PostgreSQL (paridade com prod)
# Subir:  docker compose -f docker-compose.dev.yml up -d --build
# NUNCA usar os volumes de produção. Aqui são *_dev e isolados.
services:
  db:
    image: postgres:16-alpine          # mesma major da prod
    restart: unless-stopped
    environment:
      POSTGRES_USER: oriens
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: oriens
    ports:
      - "5432:5432"                     # expõe p/ rodar o app no host (py uvicorn) se quiser
    volumes:
      - pgdata_dev:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U oriens -d oriens"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    env_file: .env
    environment:
      TZ: America/Sao_Paulo
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - .:/app                          # hot reload
      - appdata_dev:/app/data           # anexos do dev
    ports:
      - "8000:8000"

volumes:
  pgdata_dev:
  appdata_dev:
```

### 3. Ajustes de `.env` (dev)
```env
# DEV — PostgreSQL (app em container → host do banco = nome do serviço "db")
DATABASE_URL=postgresql+asyncpg://oriens:devpass@db:5432/oriens
POSTGRES_PASSWORD=devpass
SECRET_KEY=dev-key
DEBUG=true
COOKIE_SECURE=false
AI_ENABLED=false
AI_PROVIDER=null
```
- Rodando o app **no host** (`py -m uvicorn`) contra o PG do container: trocar host por
  `@localhost:5432` (precisa do `ports: 5432:5432` acima).
- A senha de dev é independente da de prod; a `.env` da VPS **não** é tocada.

### 4. Procedimento de migração (no PC, quando autorizado)
1. Garantir árvore git limpa (commitar o que estiver pendente) e Docker rodando.
2. Criar `docker-compose.dev.yml`; ajustar `.env` (dev) e `.env.example`.
3. `docker compose -f docker-compose.dev.yml up -d --build`.
4. No startup, `init_db()` roda `create_all` + `_ensure_columns_postgres()` → schema completo no PG de dev (os ramos SQLite ficam inertes pelo guard de dialeto).
5. Banco nasce **vazio**: recriar 1º usuário em `/auth/setup` (sem migrar dados do SQLite — coerente com a decisão de produção). *Se um dia quiser copiar dados, existe `scripts/migrate_to_postgres.py` — mas o recomendado é começar limpo.*
6. Smoke test: login, dashboard, criar projeto/tarefa, temas, concluir tarefa, decisões, arquivar.

### 5. Plano de rollback (para SQLite)
- **Imediato:** voltar `DATABASE_URL` do `.env` para `sqlite+aiosqlite:///./data/oriens.db` e rodar pelo `docker-compose.yml` antigo (ou `py -m uvicorn`). O arquivo `data/oriens.db` continua intacto — nada foi perdido.
- **Descartar o PG de dev:** `docker compose -f docker-compose.dev.yml down -v` (o `-v` aqui é **seguro**, são volumes `*_dev`; **jamais** rodar `-v` no compose de prod).
- **Git:** a mudança é aditiva (novo compose + `.env`); `git revert`/`checkout` desfaz sem afetar prod.

### 6. Impactos em testes e deploy
- **Deploy: ZERO impacto.** Prod usa `docker-compose.prod.yml` + `.env` da VPS, nenhum dos dois muda. `git pull && docker compose -f docker-compose.prod.yml up -d --build` segue idêntico. O `docker-compose.dev.yml` nunca é referenciado em prod.
- **Testes:** `tests/conftest.py` usa **SQLite in-memory** (`sqlite+aiosqlite:///:memory:`, `StaticPool`, cookie `oriens_token` corrigido na AUDITORIA).
  - Curto prazo: manter assim (rápido) — 39 testes passando.
  - Ganho de paridade só aparece se a suíte (ou ao menos um *smoke test*) rodar contra PG; opção futura: serviço PG efêmero no CI.
- **Risco residual:** já reduzido pela AUDITORIA (`native_enum=False` em todos os enums) — deixou de ser o principal motivador deste plano (ver nota no topo desta seção).

---
