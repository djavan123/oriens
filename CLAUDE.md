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
| Banco | SQLite (aiosqlite) | → PostgreSQL |
| Testes | pytest + pytest-asyncio | 8.3.3 + 0.24.0 |
| IA (opcional) | Anthropic / OpenAI | ≥0.40.0 / ≥1.50.0 |
| Deploy | Docker Compose | — |

> **Migrations:** gerenciadas via `database.py` → `init_db()` com `Base.metadata.create_all` + `_ensure_columns()` (idempotente, ALTER TABLE por coluna) + `_migrate_data()` (seed e migrações de dados). **Alembic não está em uso ativo.**

---

## ESTRUTURA DE PASTAS (ESTADO ATUAL — PÓS SCRIPT 2)

```
C:\Projetos\Sistema tarefas\
├── app/
│   ├── __init__.py
│   ├── main.py                        # FastAPI app, routers, lifespan, exception handlers
│   ├── config.py                      # Pydantic Settings (DATABASE_URL, SECRET_KEY, AI_*)
│   ├── database.py                    # Engine async, session, init_db(), get_db()
│   ├── templates_env.py               # Jinja2 env global (função `now`, `fmt_size`)
│   ├── models/
│   │   ├── __init__.py                # Exporta todos os models
│   │   ├── user.py
│   │   ├── project.py                 # + proxima_acao, premissas, responsavel_id; status: nao_iniciado/em_andamento/concluido
│   │   ├── task.py                    # EnergyLevel aqui; + responsavel_id
│   │   ├── note.py
│   │   ├── capture.py
│   │   ├── context.py
│   │   ├── weekly_directive.py
│   │   ├── project_comment.py
│   │   ├── project_attachment.py
│   │   ├── project_milestone.py
│   │   ├── project_risk.py
│   │   ├── project_audit.py
│   │   └── project_timeline.py        # TimelineEventType enum + ProjectTimeline model
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── project.py
│   │   ├── task.py
│   │   └── capture.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── user_repo.py
│   │   ├── project_repo.py            # get_last_activity() lê de project_timeline
│   │   ├── task_repo.py
│   │   ├── note_repo.py
│   │   ├── capture_repo.py
│   │   ├── context_repo.py
│   │   ├── weekly_directive_repo.py
│   │   ├── project_comment_repo.py
│   │   ├── project_attachment_repo.py
│   │   ├── project_milestone_repo.py
│   │   ├── project_risk_repo.py
│   │   ├── project_audit_repo.py
│   │   └── project_timeline_repo.py   # record(), get_by_project(), get_last_activity()
│   ├── services/
│   │   ├── __init__.py
│   │   ├── project_service.py         # audit trail + timeline (project_created, status_changed)
│   │   ├── task_service.py            # verb validation, priority_score + timeline (task_created, task_done)
│   │   ├── capture_service.py         # process_as_task/project/note/discard
│   │   ├── dashboard_service.py       # DashboardData: tasks + weekly_theme
│   │   ├── weekly_directive_service.py
│   │   └── ai_service.py              # Protocol + ClaudeProvider + OpenAIProvider + NullProvider
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── dashboard.py
│   │   ├── projects.py                # passa users, responsavel_map, timeline ao contexto
│   │   ├── capture.py
│   │   ├── weekly.py                  # projetos_sem_atualizacao por atividade real (timeline)
│   │   └── api/
│   │       ├── __init__.py
│   │       ├── tasks.py               # aceita responsavel_id
│   │       ├── projects.py            # aceita responsavel_id
│   │       ├── capture.py
│   │       ├── ai.py
│   │       └── context.py
│   ├── templates/
│   │   ├── base.html                  # tokens oriens-*, Inter, Tailwind CDN, HTMX, Alpine.js
│   │   ├── base_app.html              # sidebar "Oriens"
│   │   ├── dashboard.html
│   │   ├── capture.html
│   │   ├── process.html
│   │   ├── weekly.html                # seção "Projetos sem atualização"
│   │   ├── auth/
│   │   │   ├── login.html
│   │   │   └── setup.html
│   │   ├── projects/
│   │   │   ├── list.html
│   │   │   ├── detail.html            # proxima_acao, premissas, responsavel, seção Cronologia
│   │   │   └── reports.html
│   │   └── partials/
│   │       ├── task_item.html
│   │       ├── task_form.html         # select responsavel_id (condicional)
│   │       ├── task_edit_form.html    # select responsavel_id (condicional)
│   │       ├── task_with_subtasks.html
│   │       ├── project_card.html      # exibe primeiro nome do responsável no footer
│   │       ├── project_form.html      # select responsavel_id (condicional)
│   │       ├── project_comment.html
│   │       ├── project_attachment.html
│   │       ├── project_milestone.html
│   │       ├── project_risk.html
│   │       ├── capture_item.html
│   │       ├── process_item.html
│   │       └── ai_result.html
│   ├── static/
│   └── utils/
│       ├── __init__.py
│       ├── auth.py                    # cookie: oriens_token
│       ├── verb_validator.py
│       └── overload_detector.py       # score = (proj*2) + tasks
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_utils.py
│   ├── test_services.py
│   ├── test_routes.py
│   └── test_repositories.py
├── data/                              # oriens.db
├── scripts/
├── docker-compose.yml
├── Dockerfile
├── .env
├── requirements.txt
└── README.md
```

---

## BANCO DE DADOS (ESTADO ATUAL — PÓS SCRIPT 2)

**users:** `id, email (unique), password (bcrypt), name, created_at`

**projects:** `id, user_id, responsavel_id (nullable, FK users), context_id (nullable), name, objective, status, priority (1-3), deadline, notes, done_at, scope, tags, strategic (bool), quarter, owner, strategic_priority, proxima_acao (text), premissas (text), created_at, updated_at`
- status: `nao_iniciado | em_andamento | concluido`
- Todo projeto novo nasce com `nao_iniciado`

**tasks:** `id, user_id, responsavel_id (nullable, FK users), project_id (nullable), parent_id (nullable, self-ref), context_id (nullable), title, status, energy, is_quick_win (bool), cognitive_load, financial_impact, operational_risk, strategic_impact, task_urgency, effort, priority_score (indexed), archived (bool), deadline, created_at, done_at`
- status: `pending | done | blocked`
- energy: `high | medium | low` (EnergyLevel enum em `task.py`)

**project_timeline:** `id, project_id (FK cascade), user_id (FK cascade), event_type (string), description (string), created_at (indexed)`
- event_type: `project_created | status_changed | task_created | task_done`
- Seed automático em `_migrate_data()`: todos os projetos existentes recebem evento `project_created`
- `get_last_activity()` em `project_repo` lê daqui (fallback: `project.updated_at`)

**capture_inbox:** `id, user_id, content, processed (bool), created_at`

**notes:** `id, user_id, project_id (nullable), content, created_at`

**contexts:** `id, name, type`
- type: `work | home_recovery | home_operational | gym`

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

**.env**
```env
DATABASE_URL=sqlite+aiosqlite:///./data/oriens.db
SECRET_KEY=troque-isso-em-producao
AI_ENABLED=false
AI_PROVIDER=null
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
DEBUG=true
```

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
| POST | `/api/context/switch` | Trocar contexto ativo |
| POST | `/api/context/transition` | Transição + captura pendências |

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

---

## ESTATÍSTICAS DO PROJETO (ATUAL)

| Item | Quantidade |
|---|---|
| Tabelas no banco | 13 |
| Models SQLAlchemy | 13 |
| Repositories | 13 |
| Services | 6 |
| Rotas principais | 5 arquivos |
| Rotas API | 5 arquivos |
| Endpoints totais | ~32 |
| Templates HTML | ~24 |

---
