"""Console — send commands and view output."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from ..server import send_command
from ..main import _render

router = APIRouter()


@router.get("/console", response_class=HTMLResponse)
async def console_page(request: Request):
    return _render(
        request,
        "console.html",
        {"active": "console", "output": "", "last_cmd": ""},
    )


@router.post("/console/send", response_class=HTMLResponse)
async def console_send(request: Request, command: str = Form(...)):
    ok, output = await send_command(command)
    return _render(
        request,
        "_console_output.html",
        {"output": output, "last_cmd": command, "success": ok},
    )
