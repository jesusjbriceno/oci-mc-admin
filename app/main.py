"""oci-mc-admin — Minecraft Bedrock Server Admin Panel.

FastAPI app with Jinja2 + HTMX + Tailwind CSS.
Authentication handled by Cloudflare Zero Trust (Google OAuth).
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from .config import APP_TITLE

templates_dir = Path(__file__).parent / "templates"

app = FastAPI(title=APP_TITLE)
app.state.templates = Jinja2Templates(directory=str(templates_dir))

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


@app.get("/health")
async def health():
    return {"status": "ok"}
