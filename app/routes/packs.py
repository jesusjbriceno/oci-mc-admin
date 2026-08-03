"""Behavior pack and resource pack management."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..server import _ssh
from ..templates import _render

router = APIRouter()


async def _list_packs(pack_type: str) -> list[dict]:
    """List packs of a given type (behavior_packs or resource_packs)."""
    _, stdout, _ = await _ssh(
        f"docker exec minecraft-bedrock ls /data/{pack_type}/ 2>/dev/null"
    )
    packs = []
    for name in stdout.strip().split("\n"):
        if not name or name.startswith("vanilla") or name.startswith("chemistry"):
            continue
        # Get manifest if it exists
        _, manifest, _ = await _ssh(
            f"docker exec minecraft-bedrock cat /data/{pack_type}/{name}/manifest.json 2>/dev/null"
        )
        import json

        try:
            m = json.loads(manifest)
            header = m.get("header", {})
            packs.append({
                "name": name,
                "display_name": header.get("name", name),
                "description": header.get("description", ""),
                "version": ".".join(str(v) for v in header.get("version", [0, 0, 0])),
                "uuid": header.get("uuid", ""),
            })
        except Exception:
            packs.append({
                "name": name,
                "display_name": name,
                "description": "",
                "version": "?",
                "uuid": "",
            })
    return packs


async def _get_active_packs() -> list[dict]:
    """Get packs currently active in the world."""
    _, stdout, _ = await _ssh(
        'docker exec minecraft-bedrock cat "/data/worlds/Mundo D&D/world_behavior_packs.json" 2>/dev/null'
    )
    import json

    try:
        return json.loads(stdout)
    except Exception:
        return []


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
            "message": "",
        },
    )
