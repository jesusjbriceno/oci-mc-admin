"""oci-mc-admin — Minecraft Bedrock Server Admin Panel.

FastAPI app with Jinja2 + HTMX + Tailwind CSS.
Authentication handled upstream by Cloudflare Zero Trust (Google OAuth).
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from .config import APP_TITLE

templates_dir = Path(__file__).parent / "templates"

app = FastAPI(title=APP_TITLE)
app.state.templates = Jinja2Templates(directory=str(templates_dir))


def _render(request: Request, name: str, context: dict | None = None):
    """Wrapper to avoid Jinja2 caching issues with request in context."""
    ctx = context or {}
    # Don't pass request in context — Jinja2 uses it as cache key
    return app.state.templates.TemplateResponse(request, name, ctx)


# ── Routes ────────────────────────────────────────────────────────────

from .routes.dashboard import router as dashboard_router
from .routes.console import router as console_router
from .routes.whitelist import router as whitelist_router
from .routes.logs import router as logs_router
from .routes.backups import router as backups_router

app.include_router(dashboard_router)
app.include_router(console_router)
app.include_router(whitelist_router)
app.include_router(logs_router)
app.include_router(backups_router)


# ── Health check ──────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}
