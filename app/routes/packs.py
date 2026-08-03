"""Behavior pack and resource pack management + function editor."""

import base64
import json
import re

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from ..server import _ssh
from ..templates import _render

router = APIRouter()

# Only allow safe pack names and function paths (no traversal)
_SAFE_NAME = re.compile(r"^[a-zA-Z0-9_.\-]+$")
_SAFE_PATH = re.compile(r"^[a-zA-Z0-9_/.\-]+\.mcfunction$")

MC_CONTAINER = "minecraft-bedrock"
WORLD_DIR = "/data/worlds/Mundo D&D"


def _valid_pack(name: str) -> bool:
    return bool(_SAFE_NAME.match(name)) and ".." not in name


def _valid_path(path: str) -> bool:
    return bool(_SAFE_PATH.match(path)) and ".." not in path


# ── Pack listing ──────────────────────────────────────────────────────


async def _list_packs(pack_type: str) -> list[dict]:
    """List packs of a given type (behavior_packs or resource_packs)."""
    _, stdout, _ = await _ssh(
        f"docker exec {MC_CONTAINER} ls /data/{pack_type}/ 2>/dev/null"
    )
    packs = []
    for name in stdout.strip().split("\n"):
        if not name or name.startswith("vanilla") or name.startswith("chemistry"):
            continue
        _, manifest, _ = await _ssh(
            f"docker exec {MC_CONTAINER} cat /data/{pack_type}/{name}/manifest.json 2>/dev/null"
        )
        try:
            m = json.loads(manifest)
            header = m.get("header", {})
            packs.append({
                "name": name,
                "display_name": header.get("name", name),
                "description": header.get("description", ""),
                "version": ".".join(str(v) for v in header.get("version", [0, 0, 0])),
                "uuid": header.get("uuid", ""),
                "type": pack_type,
            })
        except Exception:
            packs.append({
                "name": name,
                "display_name": name,
                "description": "",
                "version": "?",
                "uuid": "",
                "type": pack_type,
            })
    return packs


async def _get_active_packs() -> list[dict]:
    """Get packs currently active in the world."""
    _, stdout, _ = await _ssh(
        f'docker exec {MC_CONTAINER} cat "{WORLD_DIR}/world_behavior_packs.json" 2>/dev/null'
    )
    try:
        return json.loads(stdout)
    except Exception:
        return []


# ── Function file operations ──────────────────────────────────────────


async def _list_functions(pack_name: str) -> list[str]:
    """List .mcfunction files of a behavior pack (relative paths)."""
    _, stdout, _ = await _ssh(
        f"docker exec {MC_CONTAINER} sh -c "
        f"'cd /data/behavior_packs/{pack_name}/functions 2>/dev/null && find . -name \"*.mcfunction\" | sed s|^\\./|| | sort'"
    )
    return [f for f in stdout.strip().split("\n") if f]


async def _read_function(pack_name: str, rel_path: str) -> str | None:
    """Read a function file content. Returns None on error."""
    ret, stdout, _ = await _ssh(
        f"docker exec {MC_CONTAINER} cat /data/behavior_packs/{pack_name}/functions/{rel_path} 2>/dev/null"
    )
    return stdout if ret == 0 and stdout else None


async def _write_function(pack_name: str, rel_path: str, content: str) -> tuple[bool, str]:
    """Write a function file to all pack locations (main, dev, world).

    Content is transferred base64-encoded to avoid shell escaping issues.
    """
    b64 = base64.b64encode(content.encode()).decode()
    locations = [
        f"/data/behavior_packs/{pack_name}/functions/{rel_path}",
        f"/data/development_behavior_packs/{pack_name}/functions/{rel_path}",
        f"{WORLD_DIR}/behavior_packs/{pack_name}/functions/{rel_path}",
    ]
    errors = []
    for loc in locations:
        # mkdir -p the parent dir, then decode base64 into the file
        cmd = (
            f"docker exec {MC_CONTAINER} sh -c "
            f"'mkdir -p $(dirname {loc}) && echo {b64} | base64 -d > {loc}'"
        )
        ret, _, stderr = await _ssh(cmd)
        if ret != 0:
            # Not all locations exist for every pack — only count as error
            # if the main behavior_packs location failed
            if loc == locations[0]:
                errors.append(stderr.strip() or "write failed")
    if errors:
        return False, errors[0]
    return True, rel_path


# ── Routes: pack listing ──────────────────────────────────────────────


@router.get("/packs", response_class=HTMLResponse)
async def packs_page(request: Request):
    behavior_packs = await _list_packs("behavior_packs")
    resource_packs = await _list_packs("resource_packs")
    active = await _get_active_packs()
    active_uuids = {p.get("pack_id", "") for p in active}

    return _render(
        request,
        "packs.html",
        {
            "active": "packs",
            "behavior_packs": behavior_packs,
            "resource_packs": resource_packs,
            "active_uuids": active_uuids,
        },
    )


# ── Routes: function editor ───────────────────────────────────────────


@router.get("/packs/{pack_name}/functions", response_class=HTMLResponse)
async def functions_list(request: Request, pack_name: str):
    if not _valid_pack(pack_name):
        return _render(request, "packs.html", {"active": "packs", "behavior_packs": [],
                                               "resource_packs": [], "active_uuids": set()})
    functions = await _list_functions(pack_name)
    return _render(
        request,
        "functions.html",
        {"active": "packs", "pack_name": pack_name, "functions": functions},
    )


@router.get("/packs/{pack_name}/edit", response_class=HTMLResponse)
async def function_edit(request: Request, pack_name: str, path: str):
    if not _valid_pack(pack_name) or not _valid_path(path):
        return _render(request, "functions.html",
                       {"active": "packs", "pack_name": pack_name, "functions": []})
    content = await _read_function(pack_name, path)
    if content is None:
        content = ""
    return _render(
        request,
        "function_edit.html",
        {
            "active": "packs",
            "pack_name": pack_name,
            "path": path,
            "content": content,
            "message": "",
        },
    )


@router.post("/packs/{pack_name}/save", response_class=HTMLResponse)
async def function_save(request: Request, pack_name: str, path: str = Form(...),
                        content: str = Form(...)):
    if not _valid_pack(pack_name) or not _valid_path(path):
        ok, msg = False, "Invalid pack or path"
    else:
        ok, msg = await _write_function(pack_name, path, content)
    return _render(
        request,
        "_save_result.html",
        {"success": ok, "message": msg, "path": path},
    )


@router.post("/packs/{pack_name}/new", response_class=HTMLResponse)
async def function_new(request: Request, pack_name: str, path: str = Form(...)):
    """Create a new empty function file."""
    # Normalize: strip leading slashes, ensure .mcfunction extension
    path = path.strip().lstrip("/")
    if not path.endswith(".mcfunction"):
        path += ".mcfunction"
    if not _valid_pack(pack_name) or not _valid_path(path):
        functions = await _list_functions(pack_name)
        return _render(request, "functions.html",
                       {"active": "packs", "pack_name": pack_name, "functions": functions})
    ok, _ = await _write_function(pack_name, path, f"## {path}\n## Uso: /function {path[:-11]}\n\n")
    functions = await _list_functions(pack_name)
    return _render(request, "functions.html",
                   {"active": "packs", "pack_name": pack_name, "functions": functions})
