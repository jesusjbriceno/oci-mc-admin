"""Shared template rendering helper."""

from fastapi import Request
from fastapi.templating import Jinja2Templates
from pathlib import Path

templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


def _render(request: Request, name: str, context: dict | None = None):
    """Render template with request context."""
    ctx = context or {}
    return templates.TemplateResponse(request, name, ctx)
