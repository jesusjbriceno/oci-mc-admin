"""Server logs viewer."""

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

from ..server import get_logs
from ..main import _render

router = APIRouter()


@router.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request, lines: int = Query(default=100, ge=10, le=500)):
    log_text = await get_logs(lines=lines)
    return _render(
        request,
        "logs.html",
        {"active": "logs", "log_text": log_text, "lines": lines},
    )
