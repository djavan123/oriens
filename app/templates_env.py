# app/templates_env.py
from datetime import datetime
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")
templates.env.globals["now"] = datetime.utcnow

# Versão do app para cache-busting (?v=) de estáticos e do service worker.
from app.config import get_settings  # noqa: E402

templates.env.globals["app_version"] = get_settings().APP_VERSION


def due_status(value):
    """Classifica uma data de prazo em relação a hoje.

    Retorna 'overdue' (passado), 'today' (hoje), 'future' (futuro) ou None
    quando não há data. Centraliza a comparação usada nos badges de urgência.
    """
    if not value:
        return None
    d = value.date() if hasattr(value, "date") else value
    today = datetime.utcnow().date()
    if d < today:
        return "overdue"
    if d == today:
        return "today"
    return "future"


templates.env.globals["due_status"] = due_status

from app.services.importancia_service import faixa_importancia  # noqa: E402

templates.env.globals["faixa_importancia"] = faixa_importancia


def url_domain(url):
    """Domínio de uma URL (sem 'www.'), para exibição discreta nos itens de Repositório."""
    if not url:
        return None
    from urllib.parse import urlparse
    try:
        host = urlparse(url).hostname
    except ValueError:
        return None
    if host and host.startswith("www."):
        host = host[4:]
    return host


templates.env.globals["url_domain"] = url_domain


def safe_hex(value):
    """Valida cor hex (#RRGGBB). Cores fora do padrão viram None — nunca chegam ao CSS.

    Sanitiza também na renderização porque valores antigos podem estar persistidos.
    """
    import re
    if value and re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        return value
    return None


templates.env.globals["safe_hex"] = safe_hex
