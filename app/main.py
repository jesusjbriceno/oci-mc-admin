"""oci-mc-admin — Minecraft Bedrock Server Admin Panel.

FastAPI app with Jinja2 + HTMX + Tailwind CSS.
Authentication handled upstream by Cloudflare Zero Trust (Google OAuth).
"""

from fastapi import FastAPI

from .config import APP_TITLE

app = FastAPI(title=APP_TITLE)


# ── Routes ────────────────────────────────────────────────────────────

from .routes.dashboard import router as dashboard_router
from .routes.console import router as console_router
from .routes.whitelist import router as whitelist_router
from .routes.logs import router as logs_router
from .routes.backups import router as backups_router
from .routes.help import router as help_router

app.include_router(dashboard_router)
app.include_router(console_router)
app.include_router(whitelist_router)
app.include_router(logs_router)
app.include_router(backups_router)
app.include_router(help_router)


# ── Health check ──────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}
