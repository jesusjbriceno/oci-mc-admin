"""Console — send commands and view output."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from ..server import send_command

router = APIRouter()


@router.get("/console", response_class=HTMLResponse)
async def console_page(request: Request):
    return request.app.state.templates.TemplateResponse(
        "console.html",
        {"request": request, "active": "console", "output": "", "last_cmd": ""},
    )


@router.post("/console/send", response_class=HTMLResponse)
async def console_send(request: Request, command: str = Form(...)):
    ok, output = await send_command(command)
    return request.app.state.templates.TemplateResponse(
        "_console_output.html",
        {
            "request": request,
            "output": output,
            "last_cmd": command,
            "success": ok,
        },
    )
