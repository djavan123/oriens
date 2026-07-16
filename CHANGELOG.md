# CHANGELOG — Oriens

Histórico de como o sistema chegou ao estado atual. O **estado atual vive em `CLAUDE.md`**; este arquivo é a memória de decisões — útil para responder "por que isso é assim?" sem poluir o contexto que o Claude Code carrega toda sessão.

Ordem: mais antigo primeiro. Registros marcados com ✅ foram concluídos.

---

## Fundação (FASES 1–8)

- **FASE 1 — Fundação:** estrutura de pastas, models, migrations via `_ensure_columns`, Docker, config.
- **FASE 2 — Auth:** JWT (PyJWT), bcrypt, login/logout, setup do primeiro usuário, `get_current_user`.
- **FASE 3 — Dashboard e Projetos:** CRUD de projetos, `dashboard_service`, `overload_detector` (depois removido), templates base com sidebar.
- **FASE 4 — Tarefas:** CRUD com validação de verbo (depois revogada), subtarefas, archiving, `priority_score`.
- **FASE 5 — Captura e Processamento:** inbox de captura, processamento em task/project/note/discard.
- **FASE 6 — Refinamentos de UX:** filtro de energia, quick wins, modos overload/minimal/full (depois removidos), contextos de trabalho, diretiva semanal (depois removida), campos executivos, milestones/riscos/comentários/anexos, audit trail.
- **FASE 7 — Design System:** paleta unificada `oriens-*`, fonte Inter, zero `border-dashed`, hierarquia tipográfica.
- **FASE 8 — IA:** providers desacoplados (Claude, OpenAI, Null), ativação por `.env`.

---

## Refatoração e evolução (SCRIPTS 1–8)

- **SCRIPT 1 — Refatoração Oriens:** remoção do módulo Mission; renomeação para Oriens (tokens, cookies, banco); status de projeto com 3 estados; campos `proxima_acao` e `premissas`; `get_last_activity()` baseado em atividade real.
- **SCRIPT 2 — Evolução dos Projetos:** `responsavel_id` (FK → users) em Project e Task; tabela `project_timeline` de eventos automáticos; cronologia no detalhe; `get_last_activity()` migrado para ler da timeline; seed automático para projetos existentes.
- **SCRIPT 3 — Contextos, Etiquetas e Configurações:** seletor de contexto em tarefas; contextos dinâmicos (`contexts.type` → `String(50)` + `user_id`; cookie passa a guardar `context_id` inteiro; helper `resolve_active_context()`); etiquetas (model `Label`, `label_repo`, `tasks.tags`); página `/settings`.
- **PRODUÇÃO — Preparação para deploy:** driver `asyncpg`; guard só-SQLite em `_ensure_columns`/`_migrate_data`; `init_db()` sempre no lifespan; `COOKIE_SECURE` em todos os `set_cookie`; Dockerfiles dev/prod; PWA (manifest); responsividade (sidebar off-canvas); infra/docs (nginx, backup, migrate_to_postgres, DEPLOY.md).
- **DEPLOY — Oriens online na VPS:** repo em github.com/djavan123/oriens; VPS Ubuntu 24.04; `.env` de produção; acesso direto por `http://IP:8000`. Migração dos dados antigos do SQLite abandonada — começou com banco limpo.
- **SCRIPT 4 — Detalhe do projeto:** lembretes de tarefa (`remind_at`) → Telegram + popup; cronologia → "Atividade Recente"; herança automática de contexto nas tarefas de projeto; contexto obrigatório no projeto; criação de tarefa só com título.
- **SCRIPT 5 — Evolução dos Projetos:** próxima ação em destaque; arquivamento de projetos (`archived`); Marcos → Decisões (`project_decisions`); evento `decision_recorded` na timeline.
- **SCRIPT 6 — Temas + clareza visual:** 3 temas (`dark`/`light`/`warm`) via `data-theme` + tokens `--oriens-*` + ponte Tailwind; sem flash + persistência via localStorage/Alpine; sweep de legibilidade; urgência por data (`due_status`); estados vazios como convite.
- **SCRIPT 7 — Ajustes na página de Projeto:** riscos ocultos da UI (backend intacto); card de prazo; transição de conclusão; mais padding.
- **SCRIPT 8 — Importância ponderada + foco do dia:** critérios por contexto (`criterio_contexto`, máx. 3, peso + inverter) e valores por tarefa (`tarefa_criterio_valor`); `tasks.importancia`/`sem_nota`; foco do dia (`users.foco_do_dia`); dashboard de prioridades com 3 grupos, polling 30s, adiar. **Todo o subsistema de critérios foi depois desativado (SCRIPT 13) e removido (AUDITORIA).**

---

## Redesign e execução de projetos (SCRIPTS 9–18)

- **SCRIPT 9 — Redesign visual de lista de tarefas:** partial unificado `task_item.html` (substitui `task_item` + `dashboard_task`); visual denso estilo Todoist; checkbox com cor de urgência; badges condicionais; flags via `{% with %}`.
- **SCRIPT 10A — Base técnica para projetos executáveis:** `tasks.order_index` (ordem manual das tarefas de topo de projeto); métodos de reorder/next/max no `task_repo`; `get_project_next_action`; endpoint `PATCH /task-order`.
- **SCRIPT 10B/10C — UI de execução + executabilidade na lista:** detalhe reorganizado em torno da execução; drag-and-drop (SortableJS); importância oculta para tarefas de projeto; `get_executability` (estado operacional por projeto: `completed | not_started | no_action | stalled | executable`).
- **SCRIPT 11 — Dashboard: projetos em foco × tarefas avulsas:** separação total projeto × avulsa; `get_projects_in_focus` / `get_standalone_tasks`; fragmentos `/dashboard/projects-focus` e `/standalone`.
- **SCRIPT 12 — Bloco "Agora", contraste e cards limpos:** bloco "Agora" (uma ação dominante); foco do dia compacto/accent; validação de verbo **desativada**; prioridade como Alta/Média/Baixa (sem P1/P2/P3); lista de projetos simplificada.
- **SCRIPT 13 — Captura rápida + criação direta + Telegram:** critérios 0-5 saíram da criação/edição (substituídos por Alta/Média/Baixa via `importancia_from_prioridade`); critérios de importância desativados (`{% if false %}`); captura direta no Dashboard; captura rápida global (atalho `c`); captura por Telegram (long polling).
- **SCRIPT 16A — Projetos orientados a tarefas (backend):** model/repo/endpoints de `project_section`; `tasks.section_id`; detalhe reestruturado em seções.
- **SCRIPT 16B — UI de projetos executáveis (templates):** `project_card.html` minimalista; `project_task_row.html` (linha densa estilo Asana); objetivo movido para a coluna principal.
- **SCRIPT 17 / 17B — Redesign de lista e detalhe de projetos:** kanban → tabela com seções colapsáveis (Alpine); detalhe full-width com 2 abas (Visão geral / Tarefas); tema dark com `--oriens-accent` branco; tokenização de cores.
- **SCRIPT 18 — Tarefas por seção + tab persistente:** regra "toda tarefa pertence a uma seção" (removidos "sem seção", blocos globais de bloqueadas/concluídas); bloqueadas/concluídas inline por seção; tab ativa persistente (localStorage).
- **DRAG & DROP — Mover tarefas entre seções + reordenar seções:** `reorder_section_tasks` e `reorder_sections`; endpoints `PATCH /section-tasks` e `/section-order`; SortableJS cross-section.
- **FIXes de projeto:** aba Tarefas (coluna "Nome", nomes de seção sem uppercase, borda esquerda removida, badge discreto, checkbox circular); alinhamento de concluídas; BUGFIX 16B (checkbox + `done_at` timezone naive UTC).
- **Correções pós-SCRIPT 18:** criação de projeto na lista (novo `project_row.html`); edição do nome no detalhe; filtro de contexto nas Listas; edição inline do título na captura; campos obrigatórios ao processar.

---

## Listas unificadas

- **Listas personalizadas + tudo como tarefa:** `/lists` virou uma área de listas de tarefas; Notas e Repositório viraram `Task` dentro de listas internas; model `TaskList` (`system_key`); `Task` ganhou `list_id`, `link_url`, `link_title`, `link_checked_at`; `title` ampliado para VARCHAR(2000); migração de dados legados (`list_migration.py`); helper de link (`link_meta.py`) com proteção SSRF.
  - **FIX — Deadlock na migração com múltiplos workers:** advisory lock unificada com o DDL de `init_db()`; `_migrate_repository_items` reordenada (SELECTs → fetch de links → INSERTs) para não segurar transação durante chamada HTTP.
- **Listas unificadas (tudo é Task comum):** eliminada qualquer diferença entre Tarefas avulsas / Notas / Repositório / personalizadas — todas usam `task_item.html` com os mesmos flags; contexto ativo filtra todas igualmente.
- **Caixa de Entrada simplificada (4 destinos):** Descartar · Tarefa de projeto · Projeto · Listas. Caixas flutuantes Alpine para escolher projeto ou lista.

---

## Prioridade Máxima

- Quatro níveis: **Máxima > Alta > Média > Baixa**, sem novo model/tabela/enum e sem migração.
  - Projetos (`priority` inteiro, menor = mais prioritário): Máxima = 0, Alta = 1, Média = 2, Baixa = 3.
  - Tarefas avulsas/listas (`importancia` float, maior = mais prioritário): Máxima → 6.0, Alta → 5.0, Média → 3.0, Baixa → 1.0.
  - Tarefas de projeto: intocadas (ordem manual de execução).
  - Visual: vermelho reservado a atraso/urgência real; badge "Máxima" discreto.

---

## Drawer de tarefa (estilo Asana)

- Substituiu a edição inline (`task_edit_form.html`) por um **drawer lateral** que abre ao clicar no título de qualquer tarefa (Dashboard, projeto, Listas). Reúne todos os metadados + Descrição (`tasks.description`, campo novo) + Subtarefas. Autosave por campo.
- `GET /api/tasks/{id}/panel` → `task_detail_panel.html`; drawer global em `base_app.html` (fecha em Esc/✕/fora).
- Prioridade e Lista incluídos no painel (sem eles, o autosave rebaixaria toda tarefa Máxima).
- Removido o fluxo inline antigo (`task_edit_form.html`, rotas `/edit` e `/cancel-edit`) e o drawer somente-leitura órfão. O `/panel` é o único fluxo de edição.

---

## AUDITORIA — Correção de bugs, limpeza, testes e produção multi-worker

Revisão completa em 5 fases (aditivo e não-destrutivo). Cada fase, um commit isolado.

- **Fase 1 — Bugs:** datetime unificado (`utils/time.py`, corrige comparação tz-aware × naive em `overdue_by_project`); enums → `native_enum=False` (elimina risco de `ALTER TYPE` no PG; conversão automática de colunas legadas); upload de anexo seguro (ownership + limite 20MB em blocos + allowlist); logging (`logging_setup.py`, fim dos `except: pass`); guard de `SECRET_KEY` no boot.
- **Fase 2 — Código morto removido:** subsistema de importância ponderada (`criterio_contexto`/`tarefa_criterio_valor`/`criterio_repo`/`ImportanciaService`); `verb_validator.py`; rota `/dashboard/priorities` + `get_priorities_grouped`; partials órfãos (`task_with_subtasks`, `dashboard_priorities`, `dashboard_task`, `criterio_selector`).
- **Fase 3 — Simplificação:** `_ENSURE_COLUMNS_PG` sincronizado 1:1 com `_ENSURE_COLUMNS`; dedupe no `task_repo` (`_project_task_order`, `_load_reorderable_tasks`); `get_unprocessed` delega a `get_inbox`; handlers `htmx:afterSettle` consolidados.
- **Fase 4 — Produção multi-worker:** `app/worker.py` (loops saem do `main.py`); `init_db` multi-worker-safe (`pg_advisory_xact_lock`); índices em colunas quentes; pool de conexões PG; `/health` com ping real; Telegram por usuário (`users.telegram_chat_id`); front sem CDN (vendor auto-hospedado); nginx com `limit_req` no login; upgrade de dependências (CVE-2024-53981 no python-multipart, jinja2 3.1.6).
- **Fase 5 — Testes:** suíte antiga quebrada (importava `app.models.mission`, cookie `pos_token`) reescrita do zero — `conftest.py` corrigido + suíte focada, 39 testes verdes.
- **Deixado fora de propósito:** refactor dos controles injetados por JS em `detail.html`; tokenização das cores hardcoded do SCRIPT 17; troca de passlib → bcrypt direto.

---

## Produção em larga escala

Preparação para rodar em escala, em 6 commits isolados. Suíte 50 → 87 testes + smoke Playwright (13/13).

- **Fase 1 — Segurança:** SSRF corrigido em `link_meta.py` (DNS resolvido e todos os IPs validados; redirects seguidos manualmente com validação a cada hop); XSS armazenado corrigido nas etiquetas (`label_item.html` com autoescape; cor validada `#RRGGBB`); nginx dentro do compose de prod (rate-limit, gzip, headers de segurança, `/static/` direto).
- **Fase 2 — Performance/banco:** paginação "carregar mais" (Caixa de Entrada, Lixeira, Listas); guard-rails de `limit`; concluídas do projeto limitadas às 50 mais recentes; N+1 do reports eliminado (`count_by_projects` com GROUP BY); índices compostos; pool do PG parametrizado (`DB_POOL_SIZE`/`DB_MAX_OVERFLOW`); nº de workers via `WEB_CONCURRENCY`.
- **Fase 3 — Boot blindado + worker resiliente:** `lock_timeout`/`statement_timeout` no `init_db`; `scripts/run_migrations.py` isolado; offset do Telegram persistido em `app_state` (sem reprocessar após restart); backoff exponencial; heartbeat + healthcheck do worker; lote de 100 lembretes/ciclo + trata 429; `fetch_link_title` via BackgroundTasks.
- **Fase 4 — Observabilidade + ownership:** middleware de request logging (`LOG_JSON=true` → JSON); `test_ownership.py` (pegou 2 brechas reais: DELETE de decisão e resolve/discard/restore de captura retornavam 200 para não-dono → corrigidos para 404).
- **Fase 5 — UX/frontend:** DOM surgery de `detail.html` migrada para markup Alpine (fim do leak de listener por linha); drag-drop com tratamento de erro; kanban sem reload; BUGFIX `$el.reset()` → `this.reset()` (6 templates); cores do SCRIPT 17 tokenizadas; cache-busting por build (`APP_VERSION` + `?v=`).
- **Fase 6 — Código morto removido:** `process.html`, `process_item.html`, `repo_item.html`, `project_card.html` (órfão); endpoints `POST/DELETE /api/repository`; ramos `action=note/repository`; `note_repo.py`/`repository_repo.py`; bloco de riscos em `detail.html`; **`alembic/` + `alembic.ini` + dep `alembic`** (abandonados). Models `Note`/`RepositoryItem` + `list_migration` mantidos por um ciclo com `# TODO remover`.

---

## FIX — Site servindo versão antiga (cache) + service worker desligado

Após o deploy de larga escala, o app mostrava CSS/JS antigos até um Ctrl+F5. Causa raiz medida com `curl` (não suposta):

1. HTML sem nenhum header de cache — navegador reusava HTML antigo apontando para assets sem `?v=`.
2. Regressão do próprio deploy: `location /static/` do nginx aplicava `expires 30d immutable` a qualquer URL sob `/static/`, inclusive sem `?v=` → asset antigo congelado 30 dias (e `Cache-Control` duplicado).
3. O service worker **nunca controlou as páginas**: registrado em `/static/sw.js` sem `scope` → escopo `/static/` → o handler de `fetch` jamais rodou. O "PWA offline" documentado era ficção desde o primeiro commit.

**Correções:**
- Middleware `cache_control` em `main.py`: `no-store` em tudo que não é `/static/`; `/static/` → `no-cache`. Mata também o bug clássico do HTMX cacheando fragmentos.
- Nginx com cache por `map $arg_v`: `?v=<sha>` → `immutable` de 1 ano; sem `?v=` → `no-cache`. `expires off` + um único `add_header always`.
- **Service worker desligado:** `sw.js` removido; `base.html` só desregistra SWs órfãos e limpa caches legados; `/static/sw.js` → 404. App segue instalável (manifest), sem cache offline.
- Guard de `APP_VERSION` no boot (aborta se `DEBUG=false` e `APP_VERSION` for o fallback).
- `test_cache_headers.py` (7 testes) trava os invariantes. Suíte: 94 verdes.

**Limite honesto:** uma resposta já gravada no navegador como `immutable, max-age=30d` não pode ser invalidada pelo servidor — o HTML novo só deixa de apontar para ela. Um único `Ctrl+Shift+R` após esse deploy deixa o estado determinístico; a partir daí os deploys chegam sozinhos.

---

## Planejado, não implementado — Dev em PostgreSQL (paridade com produção)

Apenas documentado; nada executado. O dev continua em SQLite.

O motivador original — os `Enum` nativos do PG que quebravam com `ALTER TYPE` — **já foi mitigado** pela AUDITORIA (`native_enum=False` em todos os enums + conversão automática). O risco residual é menor: só a divergência de dialeto em si e o fato de `_ensure_columns_postgres`/`_ensure_indexes` não serem exercitados localmente no dia a dia.

**Objetivos inegociáveis se um dia for feito:** VPS intacta; PostgreSQL só para dev; `docker-compose.prod.yml` e deploy inalterados; rollback trivial para SQLite.

**Esboço:** novo `docker-compose.dev.yml` (Postgres + app, volumes próprios `pgdata_dev`/`appdata_dev` — nunca os de prod); `.env` de dev com `DATABASE_URL` apontando ao PG do container e `POSTGRES_PASSWORD` de dev; `docker-compose.yml` atual mantido como rollback SQLite; `config.py` mantém default SQLite por segurança. Testes seguem em SQLite in-memory; paridade real só apareceria rodando a suíte (ou um smoke) contra PG — opção futura de serviço PG efêmero no CI.
---
