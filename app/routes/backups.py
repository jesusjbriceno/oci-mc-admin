"""Backup management."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..server import create_backup, list_backups
from ..main import _render

router = APIRouter()


@router.get("/backups", response_class=HTMLResponse)
async def backups_page(request: Request):
    backups = await list_backups()
    return _render(
        request, "backups.html", {"active": "backups", "backups": backups, "message": ""}
    )


@router.post("/backups/create")
async def backups_create(request: Request):
    ok, msg = await create_backup()
    backups = await list_backups()
    return _render(
        request,
        "backups.html",
        {
            "active": "backups",
            "backups": backups,
            "message": f"✓ Backup creado: {msg}" if ok else f"✗ Error: {msg}",
        },
    )
