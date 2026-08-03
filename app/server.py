"""Minecraft Bedrock server client — communicates via SSH to the VPS host.

Uses ``docker exec --privileged <container> send-command <cmd>`` since Bedrock
has no RCON.  Parses log output for command results.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from .config import (
    MC_SERVER_HOST,
    MC_SSH_USER,
    MC_SSH_KEY,
    MC_SSH_PORT,
    MC_CONTAINER,
    MC_DATA_DIR,
)

logger = logging.getLogger(__name__)

_SEND_CMD_BASE = f"docker exec --privileged {MC_CONTAINER} send-command"
_SSH_BASE = [
    "ssh",
    "-o", "StrictHostKeyChecking=accept-new",
    "-o", "ConnectTimeout=10",
    "-i", MC_SSH_KEY,
    "-p", str(MC_SSH_PORT),
    f"{MC_SSH_USER}@{MC_SERVER_HOST}",
]


async def _ssh(cmd: str, timeout: int = 15) -> tuple[int, str, str]:
    """Run a command on the VPS via SSH. Returns (returncode, stdout, stderr)."""
    full_cmd = [*_SSH_BASE, cmd]
    proc = await asyncio.create_subprocess_exec(
        *full_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return (-1, "", f"Command timed out after {timeout}s")

    return (
        proc.returncode or 0,
        stdout.decode(errors="replace"),
        stderr.decode(errors="replace"),
    )


async def send_command(cmd: str) -> tuple[bool, str]:
    """Send a command to the Minecraft server console.

    Returns (success, output). Output comes from recent log lines since
    ``send-command`` only writes to the container logs, not stdout.
    """
    # Capture log timestamp BEFORE sending
    before = datetime.now(timezone.utc)

    safe_cmd = cmd.replace("'", "'\"'\"'")
    ret, _, stderr = await _ssh(f"{_SEND_CMD_BASE} '{safe_cmd}'")

    if ret != 0:
        logger.warning("send-command failed: rc=%d stderr=%s", ret, stderr)
        return False, stderr.strip() or "Command execution failed"

    # Give the server a moment to process
    await asyncio.sleep(1.5)

    # Grab logs written after the command
    since = before.strftime("%Y-%m-%dT%H:%M:%S")
    log_cmd = (
        f"docker logs --since '{since}' --until 5s {MC_CONTAINER} 2>&1 | tail -20"
    )
    _, stdout, _ = await _ssh(log_cmd, timeout=10)

    return True, stdout.strip() or "(no output)"


async def get_status() -> dict:
    """Get server status: online, version, world, players, uptime."""
    ret, _, _ = await _ssh(f"docker ps --filter name={MC_CONTAINER} --format '{{{{.Status}}}}'")

    if ret != 0:
        return {"online": False, "error": "SSH connection failed"}

    # Check if container is running
    _, status_out, _ = await _ssh(
        f"docker inspect -f '{{{{.State.Running}}}} {{{{.State.StartedAt}}}}' {MC_CONTAINER}"
    )
    parts = status_out.strip().split(" ", 1)
    online = parts[0] == "true" if parts else False

    if not online:
        return {"online": False}

    # Get server version
    _, version_out, _ = await _ssh(
        f"docker exec {MC_CONTAINER} cat /data/Dedicated_Server.txt 2>/dev/null || echo 'unknown'"
    )

    # Get world name from server.properties
    _, props, _ = await _ssh(
        f"docker exec {MC_CONTAINER} grep '^level-name=' /data/server.properties | cut -d= -f2"
    )

    # Get player list
    ok, player_list = await send_command("list")
    players = []
    if ok:
        # Parse "There are X/Y players online: name1, name2"
        m = re.search(r"There are (\d+)/(\d+) players online:\s*(.*)", player_list)
        if m:
            current, maximum = int(m.group(1)), int(m.group(2))
            if current > 0:
                players = [p.strip() for p in m.group(3).split(",") if p.strip()]

    # Uptime from container
    started = parts[1] if len(parts) > 1 else ""
    uptime = ""
    if started:
        try:
            started_dt = datetime.fromisoformat(
                started.replace("Z", "+00:00")
            )
            delta = datetime.now(timezone.utc) - started_dt
            hours, rem = divmod(int(delta.total_seconds()), 3600)
            mins, _ = divmod(rem, 60)
            uptime = f"{hours}h {mins}m"
        except (ValueError, TypeError):
            uptime = started

    return {
        "online": True,
        "version": version_out.strip(),
        "world": props.strip(),
        "players": players,
        "max_players": 10,
        "uptime": uptime,
    }


async def get_logs(lines: int = 100) -> str:
    """Get recent server logs."""
    _, stdout, _ = await _ssh(
        f"docker logs --tail {lines} {MC_CONTAINER} 2>&1"
    )
    return stdout.strip()


async def get_whitelist() -> list[dict]:
    """Get current allowlist."""
    _, stdout, _ = await _ssh(
        f"docker exec {MC_CONTAINER} cat /data/allowlist.json 2>/dev/null"
    )
    import json as _json

    try:
        return _json.loads(stdout)
    except Exception:
        return []


async def add_to_whitelist(name: str) -> tuple[bool, str]:
    """Add a player to the allowlist and reload."""
    ok, out = await send_command(f"allowlist add {name}")
    if ok:
        await send_command("allowlist reload")
    return ok, out


async def remove_from_whitelist(name: str) -> tuple[bool, str]:
    """Remove a player from the allowlist and reload."""
    ok, out = await send_command(f"allowlist remove {name}")
    if ok:
        await send_command("allowlist reload")
    return ok, out


async def create_backup() -> tuple[bool, str]:
    """Create a world backup using tar on the host."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    world = "Mundo D&D"  # FIXME: Read from config
    backup_name = f"world_backup_{timestamp}.tar.gz"

    # Tell players, force save, then backup
    await send_command("say §e[Backup] Starting world backup...")
    await send_command("save-all")
    await asyncio.sleep(2)
    await send_command("save hold")
    await asyncio.sleep(1)

    ret, stdout, stderr = await _ssh(
        f"docker exec {MC_CONTAINER} tar -czf /data/backups/{backup_name} "
        f"-C /data/worlds '{world}' 2>&1",
        timeout=60,
    )
    await send_command("save resume")
    await send_command("say §a[Backup] Complete!")

    if ret != 0:
        return False, stderr or stdout or "Backup failed"
    return True, backup_name


async def list_backups() -> list[dict]:
    """List existing backups with size and date."""
    _, stdout, _ = await _ssh(
        f"docker exec {MC_CONTAINER} sh -c 'ls -lh /data/backups/*.tar.gz 2>/dev/null' || echo ''"
    )
    backups = []
    for line in stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 5:
            backups.append({
                "name": parts[-1].split("/")[-1],
                "size": parts[4],
                "date": f"{parts[5]} {parts[6]} {parts[7]}" if len(parts) >= 8 else "",
            })
    return backups
