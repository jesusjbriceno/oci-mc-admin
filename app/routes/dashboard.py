"""Dashboard — server status and player list."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..server import get_status

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    status = await get_status()
    return request.app.state.templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "status": status, "active": "dashboard"},
    )


@router.get("/status", response_class=HTMLResponse)
async def status_fragment(request: Request):
    """HTMX partial refresh for status card."""
    status = await get_status()
    return request.app.state.templates.TemplateResponse(
        "_status_card.html",
        {"request": request, "status": status},
    )
