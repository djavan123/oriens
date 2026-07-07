import json
import re
from typing import Protocol, runtime_checkable

from app.config import get_settings
from app.models.project import Project


@runtime_checkable
class AIProvider(Protocol):
    async def break_task(self, task_title: str) -> list[str]: ...
    async def suggest_next_actions(self, project: Project) -> list[str]: ...


# ── Helpers ────────────────────────────────────────────────────────────────────

def _parse_json_list(text: str) -> list[str]:
    """Extract a JSON array from AI response, tolerant of extra text."""
    text = text.strip()
    match = re.search(r'\[.*?\]', text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            return [str(s) for s in result if s]
        except json.JSONDecodeError:
            pass
    return []


# ── NullProvider ───────────────────────────────────────────────────────────────

class NullProvider:
    """Default provider when AI_ENABLED=false. Never raises, never blocks."""

    async def break_task(self, task_title: str) -> list[str]:
        return []

    async def suggest_next_actions(self, project: Project) -> list[str]:
        return []


# ── ClaudeProvider ─────────────────────────────────────────────────────────────

class ClaudeProvider:
    """Uses the Anthropic SDK with prompt caching on the system prompt."""

    MODEL = "claude-sonnet-4-6"

    def __init__(self, api_key: str):
        try:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=api_key)
        except ImportError as e:
            raise RuntimeError(
                "Package 'anthropic' is not installed. "
                "Add it to requirements.txt or run: pip install anthropic"
            ) from e

    async def break_task(self, task_title: str) -> list[str]:
        try:
            response = await self._client.messages.create(
                model=self.MODEL,
                max_tokens=512,
                system=[{
                    "type": "text",
                    "text": (
                        "You are a productivity assistant. "
                        "Break down a task into 3-5 concrete, actionable subtasks. "
                        "Return ONLY a valid JSON array of strings — no markdown, no explanation. "
                        'Example: ["Subtarefa 1", "Subtarefa 2", "Subtarefa 3"]'
                    ),
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{
                    "role": "user",
                    "content": f"Break this task into subtasks: {task_title}",
                }],
            )
            return _parse_json_list(response.content[0].text)
        except Exception:
            return []

    async def suggest_next_actions(self, project: Project) -> list[str]:
        try:
            context = f"Projeto: {project.name}"
            if project.objective:
                context += f"\nObjetivo: {project.objective}"
            if project.notes:
                context += f"\nNotas: {project.notes[:300]}"

            response = await self._client.messages.create(
                model=self.MODEL,
                max_tokens=512,
                system=[{
                    "type": "text",
                    "text": (
                        "You are a productivity assistant. "
                        "Suggest 3-5 concrete next actions for a project. "
                        "Respond in the same language as the project description. "
                        "Return ONLY a valid JSON array of strings — no markdown, no explanation."
                    ),
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{
                    "role": "user",
                    "content": f"Suggest next actions for this project:\n{context}",
                }],
            )
            return _parse_json_list(response.content[0].text)
        except Exception:
            return []


# ── OpenAIProvider ─────────────────────────────────────────────────────────────

class OpenAIProvider:
    """Uses the OpenAI SDK."""

    MODEL = "gpt-4o-mini"

    def __init__(self, api_key: str):
        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=api_key)
        except ImportError as e:
            raise RuntimeError(
                "Package 'openai' is not installed. "
                "Add it to requirements.txt or run: pip install openai"
            ) from e

    async def _chat(self, system: str, user: str, max_tokens: int = 512) -> str:
        response = await self._client.chat.completions.create(
            model=self.MODEL,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""

    async def break_task(self, task_title: str) -> list[str]:
        try:
            text = await self._chat(
                system=(
                    "You are a productivity assistant. "
                    "Break down a task into 3-5 concrete subtasks. "
                    "Return ONLY a valid JSON array of strings."
                ),
                user=f"Break this task into subtasks: {task_title}",
            )
            return _parse_json_list(text)
        except Exception:
            return []

    async def suggest_next_actions(self, project: Project) -> list[str]:
        try:
            context = f"Project: {project.name}"
            if project.objective:
                context += f"\nObjective: {project.objective}"
            text = await self._chat(
                system=(
                    "You are a productivity assistant. "
                    "Suggest 3-5 concrete next actions for a project. "
                    "Respond in the same language as the input. "
                    "Return ONLY a valid JSON array of strings."
                ),
                user=f"Suggest next actions:\n{context}",
            )
            return _parse_json_list(text)
        except Exception:
            return []


# ── Factory ────────────────────────────────────────────────────────────────────

def get_ai_provider() -> AIProvider:
    settings = get_settings()
    if not settings.AI_ENABLED:
        return NullProvider()
    provider = settings.AI_PROVIDER.lower()
    if provider == "claude":
        return ClaudeProvider(settings.ANTHROPIC_API_KEY)
    if provider == "openai":
        return OpenAIProvider(settings.OPENAI_API_KEY)
    return NullProvider()
