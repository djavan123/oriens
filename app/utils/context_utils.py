# app/utils/context_utils.py
from typing import Optional
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.context import Context
from app.repositories.context_repo import ContextRepository


async def resolve_active_context(
    request: Request,
    db: AsyncSession,
    user_id: int,
) -> tuple[Optional[int], Optional[Context], list[Context]]:
    """Returns (context_id, active_context_obj, all_contexts).

    Cookie stores str(context_id). Legacy cookies with type strings ("work" etc.)
    are resolved by matching against Context.type for backwards compatibility.
    """
    all_contexts = await ContextRepository(db).get_all_by_user(user_id)
    cookie = request.cookies.get("oriens_context", "")

    active: Optional[Context] = None
    try:
        ctx_id = int(cookie)
        active = next((c for c in all_contexts if c.id == ctx_id), None)
    except (ValueError, TypeError):
        if cookie:
            active = next((c for c in all_contexts if c.type == cookie), None)

    return (active.id if active else None), active, all_contexts
