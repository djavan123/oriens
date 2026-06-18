# app/templates_env.py
from datetime import datetime
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")
templates.env.globals["now"] = datetime.utcnow


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
