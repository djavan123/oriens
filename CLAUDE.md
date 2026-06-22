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

## ESTRUTURA DE PASTAS (ESTADO ATUAL — PÓS SCRIPT 16B)

```
C:\Projetos\Sistema tarefas\
├── app/
│   ├── __init__.py
│   ├── main.py                        # FastAPI app, routers, lifespan (init_db; seed contextos + critérios) + loop de lembretes (SCRIPT 4/8)
│   ├── config.py                      # Pydantic Settings (DATABASE_URL, SECRET_KEY, AI_*, COOKIE_SECURE, TELEGRAM_*)
│   ├── database.py                    # init_db(); _ensure_columns/_migrate_data (SQLite) + _ensure_columns_postgres (PG)
│   ├── templates_env.py               # Jinja2 env global (`now`, `fmt_size`, `due_status` — SCRIPT 6; `faixa_importancia` — SCRIPT 8)
│   ├── models/
│   │   ├── __init__.py                # Exporta todos os models (+ Label, CriterioContexto, TarefaCriterioValor)
│   │   ├── user.py                    # + foco_do_dia (text, singleton) — SCRIPT 8
│   │   ├── project.py                 # + proxima_acao, premissas, responsavel_id, archived (SCRIPT 5); status: nao_iniciado/em_andamento/concluido
│   │   ├── task.py                    # EnergyLevel aqui; + responsavel_id; + tags; + importancia/sem_nota (SCRIPT 8)
│   │   ├── note.py
│   │   ├── capture.py
│   │   ├── context.py                 # type → String(50) nullable; + user_id (contextos dinâmicos)
│   │   ├── weekly_directive.py
│   │   ├── project_comment.py
│   │   ├── project_attachment.py      # anexos em DISCO: /app/data/attachments/{project_id}/
│   │   ├── project_decision.py        # Decisões (data + texto) — SCRIPT 5 (substituiu project_milestone)
│   │   ├── project_section.py         # Seção de projeto (nome, order_index) — SCRIPT 16A
│   │   ├── project_risk.py
│   │   ├── project_audit.py
│   │   ├── project_timeline.py        # TimelineEventType enum (+ decision_recorded, SCRIPT 5) + ProjectTimeline model
│   │   ├── label.py                   # Label (etiquetas por usuário) — SCRIPT 3
│   │   ├── criterio_contexto.py       # critério de importância por contexto (peso, inverter) — SCRIPT 8
│   │   └── tarefa_criterio_valor.py   # nota 0-5 da tarefa em cada critério — SCRIPT 8
│   ├── schemas/
│   ├── repositories/
│   │   ├── ... (user, project, task, note, capture, weekly, comment, attachment, decision, risk, audit, timeline)
│   │   ├── context_repo.py            # + get_all_by_user/get_by_id/create/delete (SCRIPT 3)
│   │   ├── user_repo.py               # + update_foco (SCRIPT 8)
│   │   ├── task_repo.py               # +order_index (nullslast); reorder/next/max-order; standalone_only; next/pending_count_by_project (10A/11)
│   │   ├── project_repo.py            # get_active_by_user(context_id=...) — contexto antes de prioridade (SCRIPT 11)
│   │   ├── project_timeline_repo.py   # + last_activity_by_projects (batched) — SCRIPT 10C
│   │   ├── criterio_repo.py           # CRUD/replace de critérios + seed inicial — SCRIPT 8
│   │   ├── project_section_repo.py    # CRUD de seções de projeto — SCRIPT 16A
│   │   └── label_repo.py              # CRUD de etiquetas — SCRIPT 3
│   ├── services/
│   │   ├── project_service.py         # +get_project_next_action (10A) +get_executability (10C); audit/timeline; archived (SCRIPT 5)
│   │   ├── task_service.py            # priority_score + timeline; order_index no create (10A); SEM validação de verbo (SCRIPT 12)
│   │   ├── capture_service.py         # process_as_task (aceita context_id) /project/note/discard
│   │   ├── dashboard_service.py       # +get_projects_in_focus/get_standalone_tasks/pick_now_action (11/12); get_priorities_grouped legado
│   │   ├── importancia_service.py     # calcular_importancia, faixa_importancia, parse/apply de valores — SCRIPT 8
│   │   ├── weekly_directive_service.py
│   │   ├── ai_service.py              # Protocol + ClaudeProvider + OpenAIProvider + NullProvider
│   │   └── reminder_service.py        # lembretes: send_telegram, process_due_telegram, get_due_popups — SCRIPT 4
│   ├── routes/
│   │   ├── auth.py                    # cookies com secure=COOKIE_SECURE
│   │   ├── dashboard.py               # GET /dashboard/now + /projects-focus + /standalone (11/12); PATCH /dashboard/foco; /priorities legado
│   │   ├── projects.py                # usa resolve_active_context(); list aceita ?filter=active|archived|all (SCRIPT 5); section_groups/sem_secao_tasks/responsavel_map (SCRIPT 16A)
│   │   ├── capture.py                 # resolve_active_context(); process passa criterios_by_context + contexto ativo (SCRIPT 8)
│   │   ├── weekly.py                  # usa resolve_active_context()
│   │   ├── settings.py               # GET /settings (etiquetas + contextos + critérios) — SCRIPT 3/8
│   │   └── api/
│   │       ├── tasks.py               # critérios SÓ p/ avulsas de topo (10B); tarefa de projeto devolve wrapper drag; PATCH /{id}/adiar
│   │       ├── projects.py            # + PATCH /{id}/task-order (reordena, SCRIPT 10A); responsavel/proxima_acao/archived; decisões (SCRIPT 5); seções CRUD (SCRIPT 16A)
│   │       ├── capture.py             # process: contexto obrigatório + critérios (SCRIPT 8)
│   │       ├── ai.py
│   │       ├── context.py             # cookie agora guarda context_id (int) — SCRIPT 3
│   │       ├── settings.py            # CRUD etiquetas + contextos + POST /criterios/{ctx} (replace) — SCRIPT 3/8
│   │       └── reminders.py           # GET /due (popup) + POST /{id}/ack — SCRIPT 4
│   ├── templates/
│   │   ├── base.html                  # tokens oriens-*→var(); theme.css; init de tema sem flash; x-data theme no <html> (SCRIPT 6)
│   │   ├── base_app.html              # sidebar RESPONSIVA + contextos dinâmicos + seletor de tema "Aparência" (SCRIPT 6)
│   │   ├── dashboard.html             # bloco "Agora" + Projetos em foco × Tarefas avulsas (SCRIPT 11/12)
│   │   ├── capture.html
│   │   ├── process.html               # form de tarefa: contexto obrigatório + critérios dinâmicos (SCRIPT 8)
│   │   ├── weekly.html
│   │   ├── settings.html              # etiquetas + contextos + "Critérios de importância" (SCRIPT 3/8)
│   │   ├── auth/ (login.html, setup.html)
│   │   ├── projects/
│   │   │   ├── list.html              # kanban; cards minimalistas (só nome/prioridade/contexto/prazo, sem objetivo nem progresso — SCRIPT 16B)
│   │   │   ├── detail.html            # orientado a execução: objetivo inline, tabela Asana (Tarefa/Energia/Prazo/Responsável), seções, SortableJS (SCRIPT 16A/16B)
│   │   │   └── reports.html           # coluna "Decisões" (era "Marcos") — SCRIPT 5
│   │   └── partials/
│   │       ├── task_item.html         # PARTIAL UNIFICADO de tarefa — usado por Dashboard, concluídas, overload; flags: reload_on_done, hide_actions
│   │       ├── task_with_subtasks.html # wrapper de tarefa de projeto — LEGADO, usado só pelo bloco "Agora" do Dashboard (SCRIPT 12); NÃO usar em detalhe de projeto
│   │       ├── project_task_row.html  # linha densa Asana: drag | checkbox | título | energia | prazo | responsável | ações hover; usado em detail + seções (SCRIPT 16B)
│   │       ├── dashboard_task.html     # thin wrapper → task_item com show_project/show_adiar/refresh_priorities (SCRIPT 9)
│   │       ├── capture_item.html      # item de captura — mesmo estilo visual denso (SCRIPT 9)
│   │       ├── theme_switcher.html      # 3 bolinhas dark/light/warm (Alpine `theme`) — SCRIPT 6
│   │       ├── task_form.html         # CRIAÇÃO só com título (SCRIPT 4)
│   │       ├── task_edit_form.html    # energia/prazo/resp/etiquetas/quick win/lembrete; contexto travado se for de projeto
│   │       ├── reminder_popup.html    # toasts de lembrete (SCRIPT 4)
│   │       ├── project_form.html       # criação: + "Próxima ação" + critérios quando o contexto tem (SCRIPT 5/8)
│   │       ├── project_decision.html   # item de decisão (data + texto + excluir) — SCRIPT 5
│   │       ├── criterio_selector.html  # botões 0-5 obrigatórios por critério (radios) — SCRIPT 8
│   │       ├── foco_do_dia.html        # compacto se vazio, accent se preenchido (SCRIPT 12) + _foco_form.html
│   │       ├── dashboard_now.html       # bloco "Agora": UMA ação dominante (SCRIPT 12)
│   │       ├── dashboard_projects_focus.html # coluna "Projetos em foco" + contador sem-próxima-ação (SCRIPT 11)
│   │       ├── dashboard_project_card.html   # card de projeto em foco (próxima ação/energia/prazo) (SCRIPT 11/12)
│   │       ├── dashboard_standalone.html     # coluna "Tarefas avulsas" (task_item hide_actions) (SCRIPT 11/12)
│   │       ├── dashboard_priorities.html # LEGADO (SCRIPT 8) — não usado no dashboard atual, mantido
│   │       ├── project_card.html        # card minimalista: nome + prioridade/contexto/prazo + ações hover (SCRIPT 16B — sem objetivo/próxima-ação/progresso)
│   │       ├── project_section.html     # bloco de seção: rename Alpine, delete HTMX, task-list + task_form inline (SCRIPT 16A)
│   │       └── ... (comment/attachment/risk, process, ai_result)
│   ├── static/                        # PWA: manifest.webmanifest, sw.js, icon.svg + css/theme.css (3 temas — SCRIPT 6)
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

## BANCO DE DADOS (ESTADO ATUAL — PÓS SCRIPT 5)

**users:** `id, email (unique), password (bcrypt), name, created_at, foco_do_dia (text, nullable — SCRIPT 8)`

**projects:** `id, user_id, responsavel_id (nullable, FK users), context_id (nullable), name, objective, status, priority (1-3), deadline, notes, done_at, scope, tags, strategic (bool), quarter, owner, strategic_priority, proxima_acao (text), premissas (text), archived (bool, default false), created_at, updated_at`
- status: `nao_iniciado | em_andamento | concluido`
- Todo projeto novo nasce com `nao_iniciado`
- `archived` (SCRIPT 5): true esconde da operação diária (listagem/dashboard/semanal); continua acessível por URL, editável e pesquisável

**tasks:** `id, user_id, responsavel_id (nullable, FK users), project_id (nullable), parent_id (nullable, self-ref), context_id (nullable), title, status, energy, is_quick_win (bool), cognitive_load, financial_impact, operational_risk, strategic_impact, task_urgency, effort, priority_score (indexed), importancia (float, indexed — SCRIPT 8), sem_nota (bool, default true — SCRIPT 8), order_index (int, nullable — SCRIPT 10A), archived (bool), deadline, tags (text), remind_at (datetime, nullable), reminder_telegram_sent (bool), reminder_acked (bool), created_at, done_at`
- `importancia` (0-5): calculada dos critérios do contexto. `sem_nota`=true quando o contexto não tem critérios (ou tarefa criada sem nota). **Importância NÃO se aplica a tarefas de projeto** (SCRIPT 10B): elas ficam `sem_nota` e não exibem badge.
- `order_index` (SCRIPT 10A): ordem manual das tarefas de **topo de projeto**. NULL em avulsas e subtarefas. Nova tarefa de projeto entra com `max+1` (fim). Reordenável por drag-and-drop só no detalhe (`PATCH /api/projects/{id}/task-order`).
- status: `pending | done | blocked`
- energy: `high | medium | low` (EnergyLevel enum em `task.py`)
- `tags`: etiquetas separadas por vírgula (SCRIPT 3)
- `context_id` NULL = tarefa "Independente (todos os contextos)" — aparece em qualquer contexto

**criterio_contexto:** `id, context_id (FK contexts cascade), nome, peso (int), inverter (bool)`  *(SCRIPT 8)*
- Máx. 3 por contexto (validado no backend). `inverter`=true → nota alta reduz a importância.
- Seed inicial no lifespan: Trabalho (Financeiro 4 / Diretor pediu 3 / Facilidade 3 invertido), Casa (Financeiro 1 / Saúde 1 / Bem-estar 1).

**tarefa_criterio_valor:** `id, task_id (FK cascade), criterio_id (FK cascade), valor (0-5)`  *(SCRIPT 8)* — unique (task_id, criterio_id).

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

**weekly_directives:** `id, user_id, week_start (date), weekly_theme, top_1, top_2, top_3, ignore_list, major_risk, physiological_priority, created_at, updated_at`

**project_comments, project_attachments, project_risks, project_audit:** sem alterações.

> **`project_milestones`** (Marcos) foi **removida do código** no SCRIPT 5 (model/repo/rotas/template). A tabela legada pode permanecer órfã no banco (não é dropada — operação não-destrutiva); nada mais a lê.

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
16. **Lembretes de tarefa:** `remind_at` (data+hora, sem recorrência). Dois canais: (a) **Telegram** — loop de fundo em `main.py` (a cada 60s) chama `reminder_service.process_due_telegram()`; só envia se `TELEGRAM_BOT_TOKEN`+`TELEGRAM_CHAT_ID` estiverem no `.env`; marca `reminder_telegram_sent`. (b) **Popup no app** — `base_app.html` faz polling de `GET /api/reminders/due` (60s); `POST /api/reminders/{id}/ack` seta `reminder_acked`. Ao editar o lembrete, ambos os flags são resetados. Hora local depende de `TZ=America/Sao_Paulo`.
17. **Herança de contexto:** toda tarefa criada dentro de um projeto herda `context_id` do projeto (forçado em `api/tasks.create_task`). No `task_edit_form`, o contexto fica **somente leitura** para tarefas de projeto; editável só para tarefas avulsas.
18. **Contexto obrigatório no projeto:** `create_project` e `update_project` exigem `context_id`; o select é `required` e nunca permite valor vazio. Projetos antigos sem contexto devem recebê-lo ao serem editados.
19. **Criação de tarefa só com título** (GTD "capturar primeiro, organizar depois"): o `task_form` pede apenas o título; energia, prazo, responsável, etiquetas, quick win e lembrete são ajustados depois via "editar". **Exceção (SCRIPT 8):** se o contexto da tarefa tiver critérios, o form expande com os seletores 0-5 obrigatórios.
20. **Importância ponderada (SCRIPT 8):** por contexto, até 3 critérios (`criterio_contexto`) com peso e flag `inverter`. `importancia = soma(valor_efetivo × peso) / soma(pesos)`, onde `valor_efetivo = (5 - valor)` se `inverter`. Faixas: 1-2 baixa, 3 média, 4-5 alta. Contexto sem critérios → `importancia=0, sem_nota=true`. Cálculo em `services/importancia_service.py` (`calcular_importancia`, `faixa_importancia` — global Jinja). Subtarefas não pedem critérios (ficam sem nota).
21. **Obrigatoriedade dos critérios (SCRIPT 8):** ao criar/editar tarefa de topo cujo contexto tem critérios, todos os seletores 0-5 são obrigatórios (radios `required`) — bloqueia salvar. No **Processar**, o **contexto é obrigatório** e os critérios aparecem dinâmicos conforme o contexto escolhido (`process_item.html` + Alpine; campos `crit_<id>`). Persistência e cálculo nas rotas `api/tasks` (create/update) e `api/capture` (process), via `ImportanciaService`.
22. **Foco do dia (SCRIPT 8):** `users.foco_do_dia` (singleton, sem histórico). Card no topo do Dashboard (único com borda `--oriens-accent`), edição inline (Alpine) salvando em `PATCH /dashboard/foco`.
23. **Dashboard de Prioridades (SCRIPT 8, modo normal):** componente `partials/dashboard_priorities.html` com **três grupos** — Atrasadas / Hoje / Alta importância (`importancia >= 4` e não urgente). Máx. 3 cards por grupo (+N ocultas; "+ X outras prioridades" expande via `?expand=1`). Resumo "N atrasadas · N hoje · N alta" (bolinhas). **Pills** Todos/Atrasado/Hoje/Alta (`alta` reúne toda `importancia >= 4`). Ordenação intra-grupo por `importancia` desc. **Polling 30s** (`hx-trigger="every 30s, refreshPriorities from:body"`, swap `outerHTML`) + "atualizado há Xs". Cards (`partials/dashboard_task.html`): projeto (📁), urgência (atrasado·Nd/hoje), `alta · X.X` só na faixa alta, esforço `⏱`, `⚠` se `sem_nota`, **adiar** (escolhe novo prazo, `PATCH /api/tasks/{id}/adiar`, hover). Dados via `DashboardService.get_priorities_grouped` + `task_repo.get_pending_for_dashboard`/`_urgency_rank`. Fragmento: `GET /dashboard/priorities`. Modos overload/minimal inalterados.
20. **Próxima ação (SCRIPT 5):** todo projeto deve ter uma próxima ação concreta e executável. Campo `proxima_acao` exibido **em destaque no topo** do detalhe, no card da listagem e na revisão semanal. Disponível no formulário de criação (**opcional**) e na edição. Auditado.
21. **Arquivamento de projetos (SCRIPT 5):** `projects.archived` (bool). Arquivados saem da listagem padrão, dashboard, revisão semanal e "Projetos sem atualização", mas continuam acessíveis por URL, editáveis e pesquisáveis. Filtros na listagem: `?filter=active` (padrão) | `archived` | `all`. Botão "Arquivar/Desarquivar projeto" no detalhe (`PATCH /api/projects/{id}` com `archived`). Filtro de `archived == False` aplicado em `get_all_by_user` (padrão), `get_active_by_user` e `count_active`; `get_by_id` permanece sem filtro.
22. **Decisões (SCRIPT 5):** substituem os antigos Marcos. `project_decisions` (data + texto). No detalhe, seção "Decisões" com input "Nova decisão..." + "Adicionar"; lista em ordem decrescente. Criar uma decisão grava evento `decision_recorded` na cronologia. Excluir uma decisão **não** remove o evento da timeline.

### Execução de projetos e Dashboard (SCRIPTS 10–12)

23. **Três tipos de importância:** **Projeto** = importância estratégica (`priority` 1-3 = Alta/Média/Baixa). **Tarefa de projeto** = ordem de execução (`order_index`), **não** usa importância. **Tarefa avulsa** = importância própria (critérios do contexto).
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
| GET | `/projects` | Lista de projetos (kanban); `?filter=active\|archived\|all` (SCRIPT 5) |
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
| PATCH | `/api/tasks/{id}/adiar` | Adiar: novo prazo; 204 + `HX-Trigger: refreshPriorities` (SCRIPT 8) |
| GET | `/api/tasks/{id}/edit` | Formulário de edição inline |
| GET | `/api/tasks/{id}/cancel-edit` | Cancelar edição |
| PATCH | `/api/tasks/{id}` | Atualizar tarefa (aceita `responsavel_id`) |
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
| POST | `/api/process/{id}` | Processar captura |
| POST | `/api/ai/break-task/{id}` | IA: quebrar tarefa |
| POST | `/api/ai/suggest-actions/{id}` | IA: sugerir ações |
| POST | `/api/ai/overload-context` | IA: análise de overload |
| POST | `/api/context/switch` | Trocar contexto ativo (campo `context_id` inteiro) |
| POST | `/api/context/transition` | Transição + captura pendências (campo `context_id`) |
| PATCH | `/api/projects/{id}/task-order` | Reordena tarefas de topo do projeto (JSON `{task_ids:[...]}`) — SCRIPT 10A |
| GET | `/dashboard/now` | Fragmento bloco "Agora" (uma ação dominante) — SCRIPT 12 |
| GET | `/dashboard/projects-focus` | Fragmento "Projetos em foco" — SCRIPT 11 |
| GET | `/dashboard/standalone` | Fragmento "Tarefas avulsas" (`?energy=`) — SCRIPT 11 |
| GET | `/dashboard/priorities` | LEGADO (SCRIPT 8) — fragmento de prioridades agrupadas; não usado no dashboard atual |
| PATCH | `/dashboard/foco` | Salvar foco do dia (SCRIPT 8) |
| POST | `/api/settings/criterios/{context_id}` | Substituir critérios do contexto — máx. 3 (SCRIPT 8) |
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
| Tabelas no banco | 17 (+ `project_sections` — SCRIPT 16A) |
| Models SQLAlchemy | 17 (+ `ProjectSection`) |
| Repositories | 16 (+ `project_section_repo`) |
| Services | 8 |
| Rotas principais | 6 arquivos |
| Rotas API | 7 arquivos |
| Endpoints totais | ~47 |
| Templates HTML | ~34 (+ `project_task_row.html`, `project_section.html` — SCRIPT 16A/16B) |
| Temas | 3 (`dark`/`light`/`warm`) via `static/css/theme.css` |
| Ambiente | Dev (SQLite) + Produção (PostgreSQL na VPS) |

---

## 🔭 FUTURO (PLANEJADO, NÃO IMPLEMENTADO) — Dev em PostgreSQL (paridade com produção)

> **Status:** apenas documentado. Nada abaixo foi executado. O dev continua em SQLite.
> **Motivo:** acabar com a divergência dev (SQLite) × prod (PostgreSQL) — sobretudo os
> **`Enum` nativos** do PG (`Project.status`, `Task.status/energy/cognitive_load`,
> `ProjectRisk.impact/probability/status`), que aceitam qualquer valor no SQLite mas quebram no
> PG ao adicionar um valor novo; e o **caminho de migração** (`_ensure_columns_postgres`) que hoje
> nunca é exercitado localmente.
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
- **Testes:** `tests/conftest.py` usa **SQLite in-memory** (`sqlite+aiosqlite:///:memory:`, só `create_all`).
  - Curto prazo: manter assim (rápido) — testes continuam passando.
  - Ganho de paridade só aparece se a suíte (ou ao menos um *smoke test*) rodar contra PG; opção futura: serviço PG efêmero no CI. (Obs.: o `conftest` ainda seta cookie `pos_token` — nome legado; o atual é `oriens_token` — corrigir à parte.)
- **Risco residual:** evolução de `Enum` nativo continua perigosa em prod mesmo com dev=PG — a diferença é que agora **quebraria no dev primeiro**. Mitigação futura: migrar enums voláteis para `String` + validação na aplicação.

---
