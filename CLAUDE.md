# CLAUDE.md — Oriens

Este arquivo é lido automaticamente pelo Claude Code a cada sessão. Ele descreve o **estado atual** do sistema — não o histórico de como chegou aqui. O histórico completo (fases, scripts, auditorias, fixes) vive em `CHANGELOG.md`.

**Não apagar. Não mover. Atualizar sempre que o comportamento do sistema mudar.**

---

## O QUE É O ORIENS

Sistema pessoal de tarefas e gestão de projetos, no estilo GTD, desenhado para uso individual. A unidade operacional básica é a **próxima ação** — sempre concreta o bastante para começar na hora.

**Premissa de design:** o usuário tem TDAH. Isso não é decoração — é requisito funcional. Na prática significa: uma decisão dominante por tela (o bloco "Agora"), captura sem fricção, cor e contraste usados como sinal (urgência) e não como enfeite, no máximo ~3 níveis de informação por tela, e nada que exija o usuário lembrar de algo que o sistema poderia lembrar por ele.

---

## PAPEL DO CLAUDE

Você é um Senior Python Engineer trabalhando comigo no Oriens.

- Gere código completo e funcional. Sem pseudocódigo, sem `# TODO`, sem `# implementar aqui`.
- Todo arquivo gerado deve ter o caminho completo no cabeçalho como comentário.
- Havendo mais de uma forma válida de implementar algo, escolha a mais simples e justifique em uma linha.
- Não explique o que vai fazer. Faça. Se precisar de contexto, pergunte **antes** de gerar.
- Trabalhe incrementalmente. Ao concluir um bloco de trabalho, liste o que foi entregue, o que falta e o próximo passo.
- Use o terminal quando necessário (`pip install`, `docker`, etc.).

**Filtro de decisão técnica:** toda escolha deve responder *"isso torna o sistema mais simples ou mais difícil de manter?"*. Se a resposta for "mais difícil", a escolha está errada.

---

## STACK (NÃO NEGOCIÁVEL)

| Camada | Tecnologia | Versão |
|---|---|---|
| Backend | Python | 3.12+ |
| Framework | FastAPI | 0.115.0 |
| Servidor web | Gunicorn + Uvicorn workers | gunicorn 23.0.0 / uvicorn 0.30.6 |
| Worker de fundo | Processo dedicado `app/worker.py` | lembretes + captura Telegram |
| ORM | SQLAlchemy | 2.0.35 |
| Frontend JS | HTMX | 1.9.12 (auto-hospedado em `static/vendor/`) |
| Frontend JS | Alpine.js | 3.14.1 (auto-hospedado) |
| Frontend JS | SortableJS | 1.15.2 (auto-hospedado) |
| CSS | TailwindCSS | 3.4.17, **compilado no build** (`npm run build:css`) |
| Fonte | Inter | auto-hospedada (`static/vendor/fonts/`) |
| Templates | Jinja2 | 3.1.6 |
| Auth | PyJWT + bcrypt (via passlib) | 2.9.0 + 4.2.0 |
| Banco | SQLite (dev) / PostgreSQL (prod) | aiosqlite 0.20 / asyncpg 0.29 |
| Testes | pytest + pytest-asyncio | 8.3.3 + 0.24.0 |
| IA (opcional) | Anthropic / OpenAI | 0.40.0 / 1.50.0 (pinados) |
| Deploy | Docker Compose | VPS Ubuntu 24.04 |

**Zero dependências de CDN** — HTMX, Alpine, Sortable e a fonte Inter são auto-hospedados em `app/static/vendor/`.

**O CSS é gerado no build, nunca no navegador.** `tailwind.src.css` + `tailwind.config.js` → `app/static/css/tailwind.css` (~24 KB), via estágio `node` do Dockerfile. Em dev, rode `npm run build:css` (ou `npm run watch:css`) **sempre que mexer em classe de template** — o arquivo gerado é versionado.

> Até 08/2026 o front carregava `static/vendor/tailwind.js`: o build *Play CDN* do Tailwind, 407 KB síncronos no `<head>`, que varria o DOM e gerava a folha de estilo em tempo de execução. Custava ~3 s de tela sem estilo por carga (medido: `domComplete` 938 ms, primeira pintura 4.116 ms) e recompilava tudo a cada swap do HTMX, via `MutationObserver`. Era a causa principal do sistema parecer travado. `tests/test_assets.py` impede a volta.

**Cores com opacidade:** as cores `oriens-*` do Tailwind são funções que usam `color-mix()` (ver `tailwind.config.js`). Sem isso, `bg-oriens-accent/20` e afins não geram CSS nenhum — o Tailwind não sabe abrir um `var()` em canais. Eram 24 usos silenciosamente sem efeito.

**Navegação:** o menu usa `hx-boost` — o clique troca só o `<body>` por AJAX, com barra de progresso (`.nav-progress`). A troca de contexto responde `HX-Location` (re-render da mesma tela), não `HX-Refresh`.

**Banco único, dois ambientes:** o mesmo código roda em SQLite no dev e PostgreSQL na produção, controlado só pela `DATABASE_URL`.

**Migrations:** geridas por `database.py` → `init_db()`, que roda **sempre** no startup (web e worker), inclusive com `DEBUG=false`, serializado entre processos por `pg_advisory_xact_lock`. Alembic **não** está em uso — o schema real vem de:
- `Base.metadata.create_all` (tabelas novas)
- `_ensure_columns()` + `_migrate_data()` — **só SQLite** (guard por dialeto)
- `_ensure_columns_postgres()` — migrações aditivas no PG (`ADD COLUMN IF NOT EXISTS`, idempotente, sincronizado 1:1 com `_ensure_columns`), mais `_ensure_indexes()` e `_seed_contexts()`
- Toda migração é **aditiva e não-destrutiva**: nenhuma tabela é dropada, nenhum dado é perdido.

**Enums:** `Task.status/energy/cognitive_load`, `Project.status`, `ProjectRisk.impact/probability/status` usam `Enum(..., native_enum=False, length=50)` (mapeados como `VARCHAR`) — evita o problema de `ALTER TYPE` no Postgres ao introduzir um valor novo. Colunas PG que ainda sejam `ENUM` nativo são convertidas para `VARCHAR` automaticamente e uma única vez no boot.

**Datetime:** convenção única em `app/utils/time.py` → `utcnow()` (naive UTC, usado em todo lugar) e `now_local()` (só lembretes). Nunca gravar datetime tz-aware nas colunas (o PG usa `TIMESTAMP WITHOUT TIME ZONE`).

---

## O QUE O SISTEMA FAZ HOJE

| Área | Comportamento | Onde vive |
|---|---|---|
| **Auth** | Login/logout por JWT em cookie httpOnly (`oriens_token`, 7 dias). `/auth/setup` cria o primeiro usuário. Rate-limit de 5 req/min no login (nginx). | `routes/auth.py`, `utils/auth.py` |
| **Contextos** | Contexto ativo (Trabalho/Casa/…) persiste em cookie (`oriens_context`, guarda `context_id` inteiro) e **filtra tudo**: Dashboard, Listas, Projetos. Item sem contexto aparece em todos. Criáveis em Configurações. A transição "Sair do trabalho" oferece capturar pendências. | `utils/context_utils.py`, `routes/api/context.py` |
| **Dashboard** | **Evolução** (concluídas hoje + streak) · **Projetos em foco** (ativos por prioridade, cada um com sua próxima ação) · **Tarefas avulsas**. Filtro por energia (`?energy=`, cookie 8h). Blocos recarregam por evento HTMX, sem reload de página. **Não há mais os blocos "Agora" e "Foco do dia"** — removidos da tela no redesign de 07/07/2026 (commit `84f02ff`); a rota `/dashboard/now`, o campo `users.foco_do_dia` e `PATCH /dashboard/foco` continuam existindo, sem UI. | `routes/dashboard.py`, `services/dashboard_service.py`, `partials/dashboard_*.html` |
| **Captura** | Caixa de entrada sem fricção (só conteúdo). Entradas: tela `/capture`, **atalho global `c`** (modal em qualquer tela; não abre por cima de outro overlay) e **Telegram** (long polling no worker). **Clicar no item abre a decisão**, e "Decidir" fica sempre visível — renomear virou ação secundária no hover. Os 4 destinos têm **atalhos 1–4**: Descartar · Tarefa de projeto · Projeto · Listas. Lixeira com soft-delete (expurgo em 15 dias) e restauração. Paginação (50). | `routes/capture.py`, `routes/api/capture.py`, `services/capture_service.py` |
| **Listas** | Uma área de listas de tarefas, uma por vez: **Tarefas avulsas** (padrão) + **Notas** + **Repositório** (internas) + **personalizadas** (criar/renomear/arquivar). Tudo é `Task`; a lista é só agrupamento (`list_id`). Tarefa com URL no título exibe o **título da página** em vez do link cru (buscado em background). Paginação (100). | `routes/lists.py`, `routes/api/lists.py`, `utils/link_meta.py` |
| **Projetos — lista** | Tabela com seções colapsáveis (Em andamento / Não iniciado / Concluído), drag-and-drop entre colunas para mudar status (sem reload). Filtros: Ativos / Arquivados / Todos. | `routes/projects.py`, `projects/list.html` |
| **Projetos — detalhe** | Duas abas (lembradas por `localStorage`): **Visão geral** (objetivo, prazo, progresso, decisões, comentários, anexos) e **Tarefas** (seções colapsáveis, drag-and-drop dentro/entre seções e de seções entre si, subtarefas, badge "próxima ação", bloqueadas e concluídas inline). Arquivar/desarquivar. Cronologia automática + auditoria de campos. | `routes/projects.py`, `projects/detail.html`, `partials/project_*.html` |
| **Tarefas (drawer)** | Clicar no título de qualquer tarefa abre um painel lateral — **único fluxo de edição**. Metadados (energia, prazo, responsável, etiquetas, contexto, prioridade, lista, quick win, lembrete) + Descrição + Subtarefas. Autosave por campo, com selo **salvando… / salvo** no cabeçalho. O `PATCH` devolve **204 + `HX-Trigger`** (`refreshProjectsFocus, refreshPriorities, refreshLists[, refreshProjectTasks]`) em vez de trocar a linha: o alvo `#task-{id}` não existe em toda tela e, quando existe, está atrás do próprio drawer. | `GET /api/tasks/{id}/panel`, `partials/task_detail_panel.html` |
| **Prioridade** | **Projeto:** Máxima/Alta/Média/Baixa (`priority` 0-3, menor = mais prioritário). **Tarefa avulsa/lista:** Máxima/Alta/Média/Baixa (`importancia` 6/5/3/1, maior = mais prioritário). **Tarefa de projeto:** não tem prioridade — vale a **ordem manual** (`order_index`) de execução. | `services/importancia_service.py` |
| **Lembretes** | `remind_at` por tarefa (sem recorrência). Dois canais: **popup no app** (polling 60s + confirmar) e **Telegram** (worker, lote de 100/ciclo, trata 429). Roteado ao `telegram_chat_id` do dono, com fallback ao chat global do `.env`. | `services/reminder_service.py`, `app/worker.py` |
| **Configurações** | Tema (3 temas) · Telegram (chat id do usuário) · Etiquetas (nome + cor) · Contextos personalizados. | `routes/settings.py`, `settings.html` |
| **Relatórios** | Tabela por projeto: progresso, atrasadas, riscos abertos, decisões. | `/projects/reports` |
| **IA (opcional)** | Quebrar tarefa em subtarefas · sugerir próximas ações do projeto. Dormente por padrão (`AI_ENABLED=false`); providers Claude/OpenAI/Null. | `services/ai_service.py`, `routes/api/ai.py` |
| **Aparência / PWA** | 3 temas (`dark`/`light`/`warm`) sem reload e sem flash; sidebar responsiva (off-canvas no mobile); app instalável (manifest). **Sem cache offline** — não há service worker. | `static/css/theme.css`, `base.html` |

**Riscos de projeto:** o backend existe (`/api/projects/{id}/risks`, contagem usada no relatório), mas **não há UI** — o bloco foi retirado do detalhe.

---

## BANCO DE DADOS

**users:** `id, email (unique), password (bcrypt), name, created_at, foco_do_dia (text, nullable), telegram_chat_id (varchar(64), nullable, indexed)`
- `telegram_chat_id`: chat do Telegram do usuário. `NULL` → usa o `TELEGRAM_CHAT_ID` global do `.env`. Editável em `/settings`.

**projects:** `id, user_id, responsavel_id (nullable, FK users), context_id (nullable), name, objective, status, priority (0-3; 0=Máxima), deadline, notes, done_at, scope, tags, strategic (bool), quarter, owner, strategic_priority, proxima_acao (text), premissas (text), archived (bool), created_at, updated_at`
- status: `nao_iniciado | em_andamento | concluido`. Todo projeto novo nasce `nao_iniciado`. "Concluído" define `done_at`.
- `archived`: esconde da operação diária (listagem/dashboard); continua acessível por URL, editável e pesquisável.

**tasks:** `id, user_id, responsavel_id (nullable, FK users), project_id (nullable), parent_id (nullable, self-ref), section_id (nullable, FK project_sections), context_id (nullable), list_id (nullable, FK task_lists), title (varchar 2000), status, energy, is_quick_win (bool), cognitive_load, financial_impact, operational_risk, strategic_impact, task_urgency, effort, priority_score (indexed), importancia (float, indexed), sem_nota (bool), order_index (int, nullable), archived (bool), deadline, tags (text), description (text, nullable), link_url, link_title, link_checked_at, remind_at (datetime, nullable), reminder_telegram_sent (bool), reminder_acked (bool), created_at, done_at`
- status: `pending | done | blocked`. energy: `high | medium | low` (`EnergyLevel` em `task.py`).
- `importancia` (0-6): **só** para tarefa avulsa de topo. Tarefa de projeto fica `sem_nota` e não exibe badge.
- `order_index`: ordem manual das tarefas de **topo de projeto**. NULL em avulsas e subtarefas. Nova tarefa de projeto entra ao fim (`max+1`).
- `section_id`: seção da tarefa dentro de um projeto (toda tarefa de projeto pertence a uma seção).
- `list_id`: lista da tarefa avulsa (NULL = lista padrão "Tarefas avulsas"). Só vale para avulsa de topo.
- `context_id` NULL = "Independente (todos os contextos)" — aparece em qualquer contexto.
- `link_url/link_title/link_checked_at`: metadados de link, resolvidos só na criação/edição (nunca na renderização).

**task_lists:** `id, user_id, name, order_index, archived, system_key (nullable), created_at, updated_at`
- `system_key ∈ {notes, repository}` marca as listas internas; `NULL` = personalizada. "Tarefas avulsas" **não** é uma linha — é `tasks.list_id IS NULL`.

**project_sections:** `id, project_id (FK cascade), name, order_index` — seções nomeadas por projeto.

**project_timeline:** `id, project_id (FK cascade), user_id (FK cascade), event_type, description, created_at (indexed)`
- event_type: `project_created | status_changed | task_created | task_done | decision_recorded`
- `get_last_activity()` lê daqui (fallback: `project.updated_at`).

**project_decisions:** `id, project_id (FK cascade, indexed), user_id (FK cascade), content (text), created_at`
- Decisões do projeto (data + texto). Criar uma decisão grava evento `decision_recorded` na timeline. Listadas em ordem decrescente.

**labels:** `id, user_id (FK cascade), name, color (hex, nullable)` — etiquetas do usuário, geridas em `/settings`.

**contexts:** `id, name, type (String(50) nullable), user_id (nullable, FK users)`
- 4 contextos padrão (`user_id = NULL`): type `work | home_recovery | home_operational | gym`.
- Contextos do usuário (`user_id` preenchido): criados/excluídos em `/settings`.

**capture_inbox:** `id, user_id, content, processed (bool, indexed), created_at`

**app_state:** `key, value` — estado do worker (ex: offset do Telegram persistido para não reprocessar mensagens após restart; heartbeat).

**project_comments, project_attachments, project_risks, project_audit:** anexos gravados em disco (`/app/data/attachments/{project_id}/`).

---

## REGRAS DE NEGÓCIO

1. **Captura sem fricção:** `POST /api/capture` exige apenas `content`. Zero outros campos obrigatórios.
2. **Título de tarefa:** qualquer texto não vazio é aceito (vazio é bloqueado na rota). Não há validação de verbo.
3. **Filtro de energia:** `?energy=high|medium|low` (cookie 8h) filtra **as tarefas avulsas** do Dashboard por nível de energia. Não afeta projetos, não corta quantidade, não há "modos".
4. **Bloco "Agora":** mostra UMA única ação dominante — a próxima ação do 1º projeto executável em foco; se não houver, a 1ª tarefa avulsa. Concluir a ação recarrega os blocos via eventos HTMX.
5. **Próxima ação operacional de um projeto:** 1ª tarefa pendente em ordem manual → fallback `project.proxima_acao` → se não houver nenhuma, o projeto **não é executável**. Energia é informativa e não reordena projetos.
6. **Estado operacional do projeto:** `completed | not_started | no_action | stalled | executable` (em `get_executability`; `stalled` = em andamento sem atividade ≥7 dias). Exibido na lista como próxima ação ou "Precisa de revisão" (discreto, nunca vermelho).
7. **Dashboard separa projeto × avulsa:** nunca mistura tarefa de projeto com tarefa avulsa. Projetos em foco = ativos não-arquivados por prioridade, só os com próxima ação (o resto vira contador "sem próxima ação"). Ambos respeitam o contexto ativo (contexto antes de prioridade).
8. **Três tipos de prioridade/importância:** Projeto = importância estratégica (`priority` 0-3). Tarefa de projeto = ordem de execução (`order_index`), sem importância. Tarefa avulsa = importância própria (Máxima/Alta/Média/Baixa → `importancia` 6/5/3/1).
9. **Ordem manual de tarefas de projeto:** reordenável por drag-and-drop só no detalhe do projeto (`PATCH /api/projects/{id}/section-tasks` move/reordena dentro de ou entre seções; `PATCH /api/projects/{id}/section-order` reordena seções). Valida ownership e pertencimento; rejeita avulsas/subtarefas.
10. **Toda tarefa de projeto pertence a uma seção.** Não há bloco "sem seção".
11. **Status de projeto:** transições livres entre os 3 estados.
12. **Cronologia automática** grava em `project_timeline`: criar projeto (`project_created`), mudar status (`status_changed`), criar tarefa com project_id (`task_created`), concluir tarefa com project_id (`task_done`), criar decisão (`decision_recorded`).
13. **Auditoria de projetos:** mudanças em `status, priority, name, deadline, objective, scope, notes, proxima_acao` gravam em `project_audit`.
14. **Contexto obrigatório no projeto:** `create`/`update` exigem `context_id` (select `required`).
15. **Herança de contexto:** toda tarefa criada dentro de um projeto herda o `context_id` do projeto; o campo fica somente-leitura no drawer para tarefas de projeto.
16. **Contexto obrigatório na tarefa avulsa de topo** (com ou sem lista). Tarefa dentro de lista dispensa contexto e fica sem nota (importância só para avulsa de topo).
17. **Tarefa independente de contexto:** `context_id = NULL` aparece em qualquer contexto ativo (filtro: `context_id IS NULL OR context_id == ativo`).
18. **Responsável:** `responsavel_id` (FK → users) em projetos e tarefas. Select condicional (só quando há mais de um usuário no contexto).
19. **Etiquetas:** CRUD em `/settings`. Campo `tasks.tags` (texto, vírgula). Chips no drawer preenchem o campo; badges de contexto e tags no `task_item`.
20. **Lembretes:** `remind_at` (sem recorrência). Telegram via worker (60s, roteado ao dono, fallback ao global); popup no app via polling de `GET /api/reminders/due` (60s) + `POST /api/reminders/{id}/ack`. Editar o lembrete reseta ambos os flags. Hora local depende de `TZ=America/Sao_Paulo`.
21. **Detecção de link:** tarefa avulsa de topo com URL no título recebe `link_url`/`link_title` (buscado em background, nunca na renderização). O helper `utils/link_meta.py` bloqueia SSRF (localhost, IPs privados/reservados, valida cada redirect por DNS antes do request) e nunca levanta exceção — falha ⇒ `None`.
22. **Ownership em tudo:** toda operação valida que o recurso pertence ao usuário logado; acesso de terceiro retorna 404, nunca 200 silencioso. Inclui `POST /api/context/switch` e `/transition`, que até 08/2026 não exigiam sessão nem validavam dono.

---

## TEMAS (DESIGN SYSTEM)

Três temas (`dark` padrão, `light`, `warm`), trocáveis sem reload.

- **Fonte da verdade:** `app/static/css/theme.css` define os tokens `--oriens-*` por `:root[data-theme="dark|light|warm"]` (+ fallback dark em `:root:not([data-theme])`).
- **Ponte com Tailwind:** o `tailwind.config` em `base.html` mapeia cada cor `oriens-*` para `var(--oriens-*)`. Toda classe utilitária (`bg-oriens-*`, `text-oriens-*`, `border-oriens-*`) re-tematiza automaticamente. **Nunca** hardcode cor nos templates — use sempre os tokens.
- **Sem flash:** script inline no topo do `<head>` (antes do Tailwind) seta `data-theme` a partir do `localStorage('oriens-theme')`. O `<html>` tem `x-data`/`x-init` (Alpine) que persiste e reaplica. Seletor: `partials/theme_switcher.html`.
- Tokens de urgência: `oriens-urgent` (atrasado), `oriens-today` (hoje), `oriens-ok`. Badge por data via `due_status(value)` (global Jinja em `templates_env.py`): atrasado/hoje ganham badge; futuro só mostra a data.

**Princípios visuais (função, não enfeite):** cor e contraste são sinal de urgência, não decoração. Espaço generoso, tipografia como hierarquia, zero ícones decorativos, zero `border-dashed`, no máximo ~3 níveis de informação por tela, fonte Inter. Nenhum tema pode deixar texto ilegível. Estados vazios são **convite** (ex: "sem objetivo/decisão" viram links accent que abrem o campo).

| token | dark | light | warm |
|---|---|---|---|
| `--oriens-bg` | `#15151A` | `#FAF9F6` | `#1A1815` |
| `--oriens-surface` | `#21212B` | `#FFFFFF` | `#2A2622` |
| `--oriens-primary` (texto) | `#F2F1ED` | `#1F1E1B` | `#F0EBE3` |
| `--oriens-accent` (realce) | `#FFFFFF` | `#534AB7` | `#D85A30` |
| `--oriens-btn` / `--oriens-btn-text` (botão) | `#7067D9`/`#FFFFFF` | `#534AB7`/`#FFFFFF` | `#CA4F26`/`#FFFFFF` |
| `--oriens-urgent`/`today`/`ok` | `#E24B4A`/`#EF9F27`/`#5DCAA5` | `#A32D2D`/`#854F0B`/`#0F6E56` | `#E24B4A`/`#EF9F27`/`#1D9E75` |

**Um único botão primário.** `.btn-primary`, `.capture-btn` e `.pj-btn-primary` usam o mesmo par `--oriens-btn` / `--oriens-btn-text`. Antes eram três cores concorrentes na mesma tela: roxo na sidebar, branco nos modais e azul `#4573d2` (fora de tema) no detalhe do projeto.

⚠️ **`--oriens-accent` é fundo de realce, não cor de botão.** No tema dark ele é branco; usá-lo como fundo de botão com `--oriens-accent-text` por cima dava contraste 1,07:1 — texto invisível. Para ação primária, use sempre `--oriens-btn`.

**`--oriens-btn` passa em 4,5:1 (WCAG AA, texto normal) com `--oriens-btn-text` nos 3 temas** — 4,53 no dark, 6,93 no light, 4,51 no warm. Os valores do dark e do warm foram escurecidos a partir de `#7F77DD`/`#D85A30` (que davam 3,76 e 3,87), preservando matiz e saturação. `--oriens-accent` **não** mudou, então o realce e a identidade de cada tema seguem iguais. `tests/test_assets.py` calcula a razão a partir do próprio `theme.css` e falha se algum tema cair abaixo de 4,5 — ou se um `--oriens-btn-hover` ficar mais claro que o repouso.

---

## MÓDULO DE IA (OPCIONAL, DORMENTE POR PADRÃO)

Ativar com `AI_ENABLED=true` e `AI_PROVIDER=claude|openai` no `.env`.

| Provider | Modelo | Notas |
|---|---|---|
| `NullProvider` | — | Padrão quando `AI_ENABLED=false` |
| `ClaudeProvider` | claude-sonnet-4-6 | Usa prompt caching efêmero |
| `OpenAIProvider` | gpt-4o-mini | Sem caching |

Rotas: `POST /api/ai/break-task/{task_id}`, `/api/ai/suggest-actions/{project_id}`.

---

## CONFIGURAÇÃO (.env)

**Desenvolvimento (SQLite):**
```env
DATABASE_URL=sqlite+aiosqlite:///./data/oriens.db
SECRET_KEY=troque-isso-em-producao
DEBUG=true
COOKIE_SECURE=false
AI_ENABLED=false
AI_PROVIDER=null
```

**Produção (PostgreSQL):**
```env
DATABASE_URL=postgresql+asyncpg://oriens:SENHA@db:5432/oriens
POSTGRES_PASSWORD=SENHA          # idêntica à senha da DATABASE_URL
SECRET_KEY=<openssl rand -hex 32>
DEBUG=false
COOKIE_SECURE=false              # HTTP por IP. Vira true só quando houver HTTPS
AI_ENABLED=false
AI_PROVIDER=null
TELEGRAM_BOT_TOKEN=              # opcional
TELEGRAM_CHAT_ID=                # opcional (fallback global)
APP_VERSION=<git short SHA>      # cache-busting dos estáticos (via build-arg)
# opcionais: DB_POOL_SIZE=5, DB_MAX_OVERFLOW=5, LOG_JSON=false, WEB_CONCURRENCY=3
```

**Guards de boot (só com `DEBUG=false`):** o app aborta se `SECRET_KEY` for o valor padrão do repo, ou se `APP_VERSION` for o fallback (`dev`/`prod`) — sem SHA real, dois builds compartilhariam `?v=` e congelariam assets antigos por um ano.

**Fuso horário:** containers usam `TZ=America/Sao_Paulo` (Dockerfile instala `tzdata`). Necessário para os lembretes dispararem na hora local.

**`COOKIE_SECURE`:** com `true`, o navegador só envia o cookie por HTTPS. Em acesso `http://IP:8000` (sem TLS) **deve ser `false`**, senão o login entra em loop.

---

## ENDPOINTS

### Páginas HTML
| Método | Rota | Descrição |
|---|---|---|
| GET | `/` | Redireciona para `/dashboard` |
| GET/POST | `/auth/login` · `/auth/logout` · `/auth/setup` | Autenticação |
| GET | `/dashboard` | Dashboard (`?energy=high\|medium\|low`) |
| GET | `/projects` | Lista de projetos (`?filter=active\|archived\|all`) |
| GET | `/projects/reports` | Relatórios |
| GET | `/projects/{id}` | Detalhe do projeto |
| GET | `/capture` | Caixa de entrada |
| GET | `/lists` | Listas (`?list={id}`) |
| GET | `/settings` | Configurações |
| GET | `/health` | Health check (inclui `SELECT 1` no banco; 503 se o DB cair) |

### API (fragmentos HTMX)
| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/tasks` | Criar tarefa |
| PATCH | `/api/tasks/{id}/done` · `/blocked` · `/pending` · `/archive` | Mudar estado |
| PATCH | `/api/tasks/{id}/adiar` | Adiar (novo prazo) |
| GET | `/api/tasks/{id}/panel` | Drawer de edição (único fluxo de edição) |
| PATCH | `/api/tasks/{id}` | Atualizar tarefa |
| POST/PATCH | `/api/projects` · `/api/projects/{id}` | Criar/atualizar projeto |
| POST/DELETE | `/api/projects/{id}/comments[/{cid}]` | Comentários |
| POST/GET/DELETE | `/api/projects/{id}/attachments[/{aid}][/download]` | Anexos |
| POST/DELETE | `/api/projects/{id}/decisions[/{did}]` | Decisões |
| POST/PATCH/DELETE | `/api/projects/{id}/risks[/{rid}]` | Riscos (sem UI) |
| POST/PATCH/DELETE | `/api/projects/{id}/sections[/{sid}]` | Seções |
| PATCH | `/api/projects/{id}/section-tasks` | Mover/reordenar tarefas em/entre seções |
| PATCH | `/api/projects/{id}/section-order` | Reordenar seções |
| POST/PATCH | `/api/capture` · `/api/capture/{id}` | Criar/editar captura |
| POST | `/api/process/{id}` | Processar captura |
| POST/PATCH/DELETE | `/api/lists[/{id}]` | Listas personalizadas |
| POST | `/api/context/switch` · `/api/context/transition` | Trocar contexto / transição |
| GET | `/dashboard/now` · `/projects-focus` · `/standalone` | Fragmentos do dashboard |
| PATCH | `/dashboard/foco` | Salvar foco do dia |
| GET/POST | `/api/reminders/due` · `/api/reminders/{id}/ack` | Lembretes (popup) |
| POST/DELETE | `/api/settings/labels[/{id}]` | Etiquetas |
| POST/DELETE | `/api/settings/contexts[/{id}]` | Contextos |
| POST | `/api/settings/telegram` | Salvar `telegram_chat_id` do usuário |
| POST | `/api/ai/break-task/{id}` · `/suggest-actions/{id}` | IA (se ativa) |

---

## ESTRUTURA DE PASTAS

```
oriens/
├── app/
│   ├── main.py                 # FastAPI app, routers, lifespan (init_db + migração de listas). SEM loops de fundo.
│   ├── worker.py               # Processo dedicado: lembretes + captura Telegram (fora do web).
│   ├── logging_setup.py        # dictConfig + guards de boot (SECRET_KEY, APP_VERSION).
│   ├── config.py               # Pydantic Settings.
│   ├── database.py             # init_db() c/ advisory lock; migrações SQLite + PG; índices; seed.
│   ├── templates_env.py        # Jinja2 env global (now, fmt_size, due_status, faixa_importancia, url_domain, safe_hex).
│   ├── models/                 # SQLAlchemy: user, project, task, task_list, project_section, project_decision,
│   │                           #   project_timeline, project_comment/attachment/risk/audit, label, capture, context, app_state.
│   ├── schemas/
│   ├── repositories/           # Um por entidade. Queries sem N+1 (batched onde há listagem).
│   ├── services/               # project, task, capture, dashboard, importancia, reminder, ai,
│   │                           #   list_migration, link_title.
│   ├── routes/
│   │   ├── auth, dashboard, projects, capture, lists, settings   # páginas HTML
│   │   └── api/                # tasks, projects, capture, lists, ai, context, settings, reminders
│   ├── templates/
│   │   ├── base.html, base_app.html, dashboard.html, capture.html, lists.html, settings.html
│   │   ├── auth/ (login, setup)
│   │   ├── projects/ (list, detail, reports)
│   │   └── partials/           # task_item, project_task_row, project_section, dashboard_*, task_detail_panel, etc.
│   ├── static/
│   │   ├── vendor/             # Tailwind, HTMX, Alpine, SortableJS, fonte Inter (auto-hospedados, sem CDN)
│   │   ├── css/theme.css       # tokens dos 3 temas
│   │   └── manifest.webmanifest, icon.svg   # PWA instalável (sem service worker)
│   └── utils/
│       ├── auth.py, time.py, context_utils.py, link_meta.py
├── tests/
├── data/                       # SQLite (dev) + anexos (/app/data/attachments)
├── scripts/                    # backup.sh, migrate_to_postgres.py, run_migrations.py, worker_health.py
├── nginx/                      # oriens-ip.conf, oriens-docker.conf
├── docker-compose.yml          # DEV (SQLite + --reload + worker)
├── docker-compose.prod.yml     # PROD (db + app + worker + nginx + volumes)
├── Dockerfile                  # gunicorn -k UvicornWorker (nº de workers via WEB_CONCURRENCY)
├── DEPLOY.md, CHANGELOG.md, README.md
├── requirements.txt
└── .env / .env.example
```

---

## PRODUÇÃO E OPERAÇÃO (VPS)

**VPS:** Contabo (`vmi3445799`, Ubuntu 24.04) · **Acesso:** `http://169.58.30.41` (HTTP por IP, sem domínio) · **Local na VPS:** `/opt/oriens` · **Repo:** github.com/djavan123/oriens

**Serviços:** `db` (PostgreSQL) + `app` (web, gunicorn, workers via `WEB_CONCURRENCY`) + `worker` (lembretes + Telegram, com heartbeat) + `nginx` (porta 80: rate-limit no login, gzip, estáticos com cache). Se o `worker` cair, lembretes/Telegram param, mas o resto do app funciona.

**Comandos do dia a dia** (em `/opt/oriens`):
```bash
docker compose -f docker-compose.prod.yml ps                    # status
docker compose -f docker-compose.prod.yml logs -f app worker    # logs
docker compose -f docker-compose.prod.yml restart               # reiniciar
# atualizar (APP_VERSION = cache-busting):
git pull && APP_VERSION=$(git rev-parse --short HEAD) docker compose -f docker-compose.prod.yml up -d --build
```

**⚠️ Regra de ouro:** **nunca** use `down -v` — o `-v` apaga o volume `pgdata` (perde tudo). Os dados sobrevivem a `restart`, `up -d --build` e reboot.

**Antes de cada deploy:** guardar o commit atual para rollback trivial (`git rev-parse HEAD | tee .last_good_commit`). O código é compatível para trás (migração é aditiva) — rollback é `git checkout` + `up -d --build`.

**Persistência:** banco em `pgdata`; anexos em `appdata`. **Backup:** `bash scripts/backup.sh` (pg_dump + anexos, retém 7 dias). **Cron ativo** no root da VPS: `0 3 * * * cd /opt/oriens && bash scripts/backup.sh >> /var/log/oriens-backup.log 2>&1`.

> A retenção do `backup.sh` é `find -name 'oriens_*.gz' -mtime +7 -delete`. Backup que precise sobreviver a isso **não pode se chamar `oriens_*.gz`** — é por isso que o snapshot da migração está como `backups/SNAPSHOT-pre-migracao-hostinger_*`.

**Pendente (futuro):** domínio + HTTPS (Nginx + Certbot); ao ativar, reverter a porta para `127.0.0.1:8000:8000` e `COOKIE_SECURE=true` (ver `DEPLOY.md`).

---

## DÍVIDA TÉCNICA CONHECIDA

Itens que o sistema carrega mas ainda não foram limpos. Nada aqui quebra nada hoje; é a lista de faxina para uma próxima sessão de revisão de código.

- **Tabelas legadas órfãs no banco** (nunca dropadas por segurança — migração é sempre não-destrutiva): `criterio_contexto`, `tarefa_criterio_valor`, `project_milestones`, `weekly_directives`, `notes`, `repository_items`. Nenhuma tem leitor vivo no código. Dropar exige um passo destrutivo consciente (com backup antes).
- **Models `Note` e `RepositoryItem`** + o serviço `list_migration` seguem no código marcados para remoção, mantidos por um ciclo de segurança enquanto a migração de dados legados se estabiliza. Quando não houver mais nada a reconciliar, remover.
- **Endpoints legados** `POST/DELETE /api/repository` existem mas não são usados pela UI atual.
- **Riscos de projeto:** backend completo, sem UI. Decidir se ganha interface ou se o backend também sai.
- **Sugestão de processo:** ao começar uma faxina, cruzar esta lista com o código real (`grep` pelos nomes) antes de remover — confirmar que segue sem leitor vivo.