"""oci-mc-admin — Minecraft Bedrock Server Admin Panel.

FastAPI app with Jinja2 + HTMX + Tailwind CSS.
Authentication handled by Cloudflare Zero Trust (Google OAuth).
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from .auth import CloudflareAccessMiddleware
from .config import APP_TITLE

templates_dir = Path(__file__).parent / "templates"

app = FastAPI(title=APP_TITLE)
app.state.templates = Jinja2Templates(directory=str(templates_dir))


def _render(request: Request, name: str, context: dict | None = None):
    """Wrapper to avoid Jinja2 caching issues with request in context."""
    ctx = context or {}
    return app.state.templates.TemplateResponse(name, {"request": request, **ctx})

# ── Security: Cloudflare Zero Trust on ALL routes ─────────────────────

app.add_middleware(CloudflareAccessMiddleware)


# ── Custom 401/403 handlers (return JSON, not HTML) ──────────────────

@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc):
    return JSONResponse(
        status_code=401,
        content={"error": "Authentication required", "detail": str(exc.detail)},
    )


@app.exception_handler(403)
async def forbidden_handler(request: Request, exc):
    return JSONResponse(
        status_code=403,
        content={"error": "Access denied", "detail": str(exc.detail)},
    )


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


# ── Health check (excluded from auth in middleware) ───────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}
