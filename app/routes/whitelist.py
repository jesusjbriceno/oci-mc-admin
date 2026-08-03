"""Whitelist management."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..server import add_to_whitelist, get_whitelist, remove_from_whitelist

router = APIRouter()


@router.get("/whitelist", response_class=HTMLResponse)
async def whitelist_page(request: Request):
    players = await get_whitelist()
    return request.app.state.templates.TemplateResponse(
        "whitelist.html",
        {"request": request, "active": "whitelist", "players": players, "message": ""},
    )


@router.post("/whitelist/add", response_class=HTMLResponse)
async def whitelist_add(request: Request, name: str = Form(...)):
    ok, msg = await add_to_whitelist(name)
    players = await get_whitelist()
    return request.app.state.templates.TemplateResponse(
        "whitelist.html",
        {
            "request": request,
            "active": "whitelist",
            "players": players,
            "message": f"✓ {name} añadido" if ok else f"✗ Error: {msg}",
        },
    )


@router.post("/whitelist/remove", response_class=HTMLResponse)
async def whitelist_remove(request: Request, name: str = Form(...)):
    ok, msg = await remove_from_whitelist(name)
    players = await get_whitelist()
    return request.app.state.templates.TemplateResponse(
        "whitelist.html",
        {
            "request": request,
            "active": "whitelist",
            "players": players,
            "message": f"✓ {name} eliminado" if ok else f"✗ Error: {msg}",
        },
    )
