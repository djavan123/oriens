

Iniciar

docker compose up -d



Reiniciar

docker compose restart



Parar


docker compose down

# POS — Personal Operating System

Aplicação web pessoal para organizar foco, reduzir carga cognitiva e eliminar o caos mental. Construída para uma pessoa manter, não para escalar.

---

## Setup em 5 minutos

### Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) + Docker Compose

### 1. Clonar e configurar

```bash
git clone <repo>
cd pos
cp .env.example .env
```

Edite `.env` e troque `SECRET_KEY`:

```env
SECRET_KEY=uma-chave-secreta-longa-e-aleatoria
```

### 2. Subir

```bash
docker compose up --build
```

### 3. Criar sua conta

Abra [http://localhost:8000/auth/setup](http://localhost:8000/auth/setup)  
→ Preencha nome, email e senha → Entrar

Pronto. O sistema estará disponível em [http://localhost:8000](http://localhost:8000).

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.12 + FastAPI |
| Frontend | Jinja2 + HTMX + Alpine.js + TailwindCSS CDN |
| Banco | SQLite (preparado para PostgreSQL) |
| Auth | JWT via cookie HTTP-only |
| Deploy | Docker Compose |

---

## Funcionalidades

### Dashboard
- **Filtro de energia**: clique em Alta / Média / Baixa para filtrar tarefas pelo seu estado atual — persiste por 8 horas
- **Foco**: missão mais prioritária em destaque
- **Prioridades**: top 3 tarefas pendentes
- **Quick wins**: tarefas marcadas como rápidas, com destaque visual
- **Modo overload**: quando score > 15 (projetos×2 + missões×3 + tarefas), dashboard simplifica automaticamente para 1 foco + 3 tarefas + quick wins

### Projetos
- CRUD completo, status (active/paused/done/archived), prioridade 1-3
- Troca de status diretamente no card sem reload (HTMX)

### Missões
- Máximo 3 ativas simultâneas — enforced na service layer
- Associação opcional a projetos
- Nível de energia por missão

### Tarefas
- Título **deve começar com verbo** — validação inline com sugestões clicáveis
- Marcar como feito/bloqueado/pendente via checkbox HTMX
- Filtro por nível de energia
- Flag `quick_win` para destacar no dashboard

### Captura
- `POST /api/capture` exige apenas `content` — zero categorização
- Textarea auto-resize; captura em < 3 segundos

### Processamento
- `/process` converte cada captura em: **Tarefa / Projeto / Nota / Descartar**
- Formulários inline com Alpine.js; cada captura some do DOM após processada

---

## IA (opcional)

Desabilitada por padrão. Para ativar:

```env
AI_ENABLED=true
AI_PROVIDER=claude   # ou openai
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `DATABASE_URL` | `sqlite:///./pos.db` | URL do banco |
| `SECRET_KEY` | — | Chave JWT (troque em produção) |
| `DEBUG` | `true` | Modo debug + auto-migrate |
| `AI_ENABLED` | `false` | Ativa módulo de IA |
| `AI_PROVIDER` | `null` | `claude` ou `openai` |

---

## Testes

```bash
# Dentro do container
docker compose exec app pytest

# Localmente (com ambiente Python ativo)
pip install -r requirements.txt
pytest

# Com verbosidade
pytest -v

# Cobertura específica
pytest tests/test_services.py -v
pytest tests/test_utils.py -v
```

### O que é testado

| Arquivo | Escopo |
|---------|--------|
| `test_utils.py` | Overload detector (score, threshold) · Verb validator (PT/EN, sugestões) |
| `test_services.py` | Limite de 3 missões ativas · Validação de verbo em tarefas · mark_done/blocked/pending |
| `test_routes.py` | Auth (redirect, cookie) · Dashboard (energia, overload) · Capture · Process (all 4 actions) |
| `test_repositories.py` | Filtros de energia · Isolamento por usuário · N+1 estrutural · Contadores |

---

## Estrutura

```
pos/
├── app/
│   ├── main.py              # FastAPI app + routers + exception handlers
│   ├── config.py            # Settings via pydantic-settings
│   ├── database.py          # Engine SQLite/PostgreSQL + get_db dependency
│   ├── models/              # SQLAlchemy 2.0 (user, project, mission, task, capture, note)
│   ├── repositories/        # Queries SQL — sem N+1
│   ├── services/            # Regras de negócio (limite missões, validação verbo, overload)
│   ├── routes/              # HTML (Jinja2) + API HTMX
│   ├── templates/           # Jinja2 com TailwindCSS dark mode
│   └── utils/               # auth, overload_detector, verb_validator
├── tests/
├── alembic/
├── docker-compose.yml
├── Dockerfile
└── .env.example
```

---

## Migração para PostgreSQL

Troque `DATABASE_URL` no `.env`:

```env
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/pos
```

E adicione `asyncpg` ao `requirements.txt`. Nenhuma outra mudança necessária — o código usa SQLAlchemy 2.0 agnóstico de banco.
