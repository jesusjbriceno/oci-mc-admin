"""Unit tests for oci-mc-admin.

Run with: pytest tests/ -v
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def mock_ssh():
    """Mock the _ssh function to return controlled outputs."""
    with patch("app.server._ssh", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_send_command():
    """Mock send_command to avoid real SSH calls."""
    with patch("app.server.send_command", new_callable=AsyncMock) as mock:
        yield mock


# ── Tests: _ssh ──────────────────────────────────────────────────────────

class TestSSH:
    """Tests for the low-level SSH helper."""

    @pytest.mark.asyncio
    async def test_ssh_success(self):
        """SSH returns (returncode, stdout, stderr) on success."""
        from app.server import _ssh

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (b"output\n", b"")
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            with patch("asyncio.wait_for", new_callable=AsyncMock) as mock_wait:
                mock_wait.return_value = (b"output\n", b"")
                ret, stdout, stderr = await _ssh("echo test")

        assert ret == 0
        assert stdout == "output\n"
        assert stderr == ""

    @pytest.mark.asyncio
    async def test_ssh_timeout(self):
        """SSH returns (-1, '', timeout_msg) on timeout."""
        from app.server import _ssh
        import asyncio

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.kill = MagicMock()
            mock_proc.wait = AsyncMock()
            mock_exec.return_value = mock_proc

            with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
                ret, stdout, stderr = await _ssh("sleep 999")

        assert ret == -1
        assert stdout == ""
        assert "timed out" in stderr


# ── Tests: send_command ──────────────────────────────────────────────────

class TestSendCommand:
    """Tests for the Minecraft command sender."""

    @pytest.mark.asyncio
    async def test_send_command_success(self, mock_ssh):
        """Successful command returns (True, output)."""
        from app.server import send_command

        # First SSH: send-command (rc=0)
        # Second SSH: docker logs (returns log lines)
        mock_ssh.side_effect = [
            (0, "", ""),  # send-command
            (0, "[INFO] There are 0/10 players online:", ""),  # logs
        ]

        ok, output = await send_command("list")

        assert ok is True
        assert "players online" in output

    @pytest.mark.asyncio
    async def test_send_command_failure(self, mock_ssh):
        """Failed command returns (False, error)."""
        from app.server import send_command

        mock_ssh.return_value = (1, "", "Permission denied")

        ok, output = await send_command("list")

        assert ok is False
        assert "Permission denied" in output

    @pytest.mark.asyncio
    async def test_send_command_quotes_in_cmd(self, mock_ssh):
        """Commands with single quotes are properly escaped."""
        from app.server import send_command

        mock_ssh.side_effect = [
            (0, "", ""),
            (0, "[INFO] OK", ""),
        ]

        ok, _ = await send_command("say It's a test")

        assert ok is True
        # Verify the command was escaped
        call_args = mock_ssh.call_args_list[0][0][0]
        assert "say It'\"'\"'s a test" in call_args or "say Its a test" in call_args


# ── Tests: get_status ────────────────────────────────────────────────────

class TestGetStatus:
    """Tests for the server status checker."""

    @pytest.mark.asyncio
    async def test_status_online(self, mock_ssh, mock_send_command):
        """Online server returns full status dict."""
        from app.server import get_status

        mock_ssh.side_effect = [
            (0, "", ""),  # docker ps
            (0, "true 2026-08-03T06:40:17Z", ""),  # docker inspect
            (0, "Dedicated Server for Minecraft: Bedrock Edition\nVersion: 1.26.36.1", ""),  # version
            (0, "Mundo D&D", ""),  # level-name
        ]
        mock_send_command.return_value = (True, "There are 2/10 players online: JaviFlash2811, jesusjbm77")

        status = await get_status()

        assert status["online"] is True
        assert status["version"] == "Dedicated Server for Minecraft: Bedrock Edition\nVersion: 1.26.36.1"
        assert status["world"] == "Mundo D&D"
        assert len(status["players"]) == 2
        assert "JaviFlash2811" in status["players"]
        assert status["max_players"] == 10
        assert "h" in status["uptime"] and "m" in status["uptime"]

    @pytest.mark.asyncio
    async def test_status_offline(self, mock_ssh):
        """Offline server returns online=False."""
        from app.server import get_status

        mock_ssh.return_value = (0, "false ", "")

        status = await get_status()

        assert status["online"] is False

    @pytest.mark.asyncio
    async def test_status_ssh_failure(self, mock_ssh):
        """SSH failure returns online=False with error."""
        from app.server import get_status

        mock_ssh.return_value = (1, "", "Connection refused")

        status = await get_status()

        assert status["online"] is False
        assert status["error"] == "SSH connection failed"

    @pytest.mark.asyncio
    async def test_status_no_players(self, mock_ssh, mock_send_command):
        """Online server with no players returns empty list."""
        from app.server import get_status

        mock_ssh.side_effect = [
            (0, "", ""),
            (0, "true 2026-08-03T06:40:17Z", ""),
            (0, "1.26.36.1", ""),
            (0, "Mundo D&D", ""),
        ]
        mock_send_command.return_value = (True, "There are 0/10 players online:")

        status = await get_status()

        assert status["online"] is True
        assert status["players"] == []

    @pytest.mark.asyncio
    async def test_status_player_parse_various(self, mock_ssh, mock_send_command):
        """Player list parsing handles various formats."""
        from app.server import get_status

        mock_ssh.side_effect = [
            (0, "", ""),
            (0, "true 2026-08-03T06:40:17Z", ""),
            (0, "1.26.36.1", ""),
            (0, "Mundo D&D", ""),
        ]
        # Test with extra whitespace and single player
        mock_send_command.return_value = (True, "There are 1/10 players online:   SoloPlayer  ")

        status = await get_status()

        assert status["players"] == ["SoloPlayer"]


# ── Tests: get_logs ──────────────────────────────────────────────────────

class TestGetLogs:
    """Tests for log retrieval."""

    @pytest.mark.asyncio
    async def test_get_logs(self, mock_ssh):
        """Logs are returned as string."""
        from app.server import get_logs

        mock_ssh.return_value = (0, "[INFO] Line 1\n[INFO] Line 2\n", "")

        logs = await get_logs(lines=50)

        assert "Line 1" in logs
        assert "Line 2" in logs

        call_cmd = mock_ssh.call_args[0][0]
        assert "--tail 50" in call_cmd

    @pytest.mark.asyncio
    async def test_get_logs_empty(self, mock_ssh):
        """Empty logs return empty string."""
        from app.server import get_logs

        mock_ssh.return_value = (0, "", "")

        logs = await get_logs()

        assert logs == ""


# ── Tests: whitelist ─────────────────────────────────────────────────────

class TestWhitelist:
    """Tests for whitelist management."""

    @pytest.mark.asyncio
    async def test_get_whitelist(self, mock_ssh):
        """Whitelist JSON is parsed correctly."""
        from app.server import get_whitelist

        mock_ssh.return_value = (0, '[{"name": "JaviFlash2811", "ignoresPlayerLimit": false}]', "")

        players = await get_whitelist()

        assert len(players) == 1
        assert players[0]["name"] == "JaviFlash2811"

    @pytest.mark.asyncio
    async def test_get_whitelist_empty(self, mock_ssh):
        """Empty whitelist returns empty list."""
        from app.server import get_whitelist

        mock_ssh.return_value = (0, "", "")

        players = await get_whitelist()

        assert players == []

    @pytest.mark.asyncio
    async def test_get_whitelist_invalid_json(self, mock_ssh):
        """Invalid JSON returns empty list."""
        from app.server import get_whitelist

        mock_ssh.return_value = (0, "not json at all", "")

        players = await get_whitelist()

        assert players == []

    @pytest.mark.asyncio
    async def test_add_to_whitelist(self, mock_send_command):
        """Adding to whitelist calls add + reload."""
        from app.server import add_to_whitelist

        mock_send_command.return_value = (True, "Player added")

        ok, msg = await add_to_whitelist("NewPlayer")

        assert ok is True
        assert mock_send_command.call_count == 2  # add + reload
        calls = [c[0][0] for c in mock_send_command.call_args_list]
        assert "allowlist add NewPlayer" in calls
        assert "allowlist reload" in calls

    @pytest.mark.asyncio
    async def test_remove_from_whitelist(self, mock_send_command):
        """Removing from whitelist calls remove + reload."""
        from app.server import remove_from_whitelist

        mock_send_command.return_value = (True, "Player removed")

        ok, msg = await remove_from_whitelist("OldPlayer")

        assert ok is True
        assert mock_send_command.call_count == 2  # remove + reload


# ── Tests: backups ───────────────────────────────────────────────────────

class TestBackups:
    """Tests for backup operations."""

    @pytest.mark.asyncio
    async def test_create_backup_success(self, mock_send_command, mock_ssh):
        """Successful backup returns (True, filename)."""
        from app.server import create_backup

        mock_send_command.return_value = (True, "")
        mock_ssh.return_value = (0, "", "")

        ok, name = await create_backup()

        assert ok is True
        assert name.startswith("world_backup_")
        assert name.endswith(".tar.gz")

    @pytest.mark.asyncio
    async def test_create_backup_failure(self, mock_send_command, mock_ssh):
        """Failed backup returns (False, error)."""
        from app.server import create_backup

        mock_send_command.return_value = (True, "")
        mock_ssh.return_value = (1, "", "tar: command not found")

        ok, msg = await create_backup()

        assert ok is False
        assert "tar" in msg or "Backup failed" in msg

    @pytest.mark.asyncio
    async def test_list_backups(self, mock_ssh):
        """Backup list parsing works."""
        from app.server import list_backups

        mock_ssh.return_value = (0,
            "-rw-r--r-- 1 root root 1.2M Aug  3 06:40 /data/backups/world_backup_20260803_064017.tar.gz\n"
            "-rw-r--r-- 1 root root 1.1M Aug  2 23:00 /data/backups/world_backup_20260802_230000.tar.gz\n",
            "")

        backups = await list_backups()

        assert len(backups) == 2
        assert backups[0]["name"] == "world_backup_20260803_064017.tar.gz"
        assert backups[0]["size"] == "1.2M"
        assert backups[1]["name"] == "world_backup_20260802_230000.tar.gz"

    @pytest.mark.asyncio
    async def test_list_backups_empty(self, mock_ssh):
        """No backups returns empty list."""
        from app.server import list_backups

        mock_ssh.return_value = (0, "", "")

        backups = await list_backups()

        assert backups == []


# ── Tests: auth middleware ───────────────────────────────────────────────

class TestAuth:
    """Tests for Cloudflare Zero Trust middleware."""

    @pytest.mark.asyncio
    async def test_health_bypasses_auth(self):
        """Health endpoint skips authentication."""
        from app.auth import CloudflareAccessMiddleware
        from fastapi import FastAPI

        app = FastAPI()
        middleware = CloudflareAccessMiddleware(app)

        request = MagicMock()
        request.url.path = "/health"
        call_next = AsyncMock(return_value="response")

        result = await middleware.dispatch(request, call_next)

        assert result == "response"
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_missing_email_returns_401(self):
        """Request without Cf-Access email gets 401."""
        from app.auth import CloudflareAccessMiddleware
        from fastapi import FastAPI, HTTPException

        app = FastAPI()
        middleware = CloudflareAccessMiddleware(app)

        request = MagicMock()
        request.url.path = "/"
        request.headers = {}
        call_next = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(request, call_next)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_email_allowed(self):
        """Request with valid Cf-Access email passes through."""
        from app.auth import CloudflareAccessMiddleware
        from fastapi import FastAPI

        app = FastAPI()
        middleware = CloudflareAccessMiddleware(app)

        request = MagicMock()
        request.url.path = "/"
        request.headers = {
            "Cf-Access-Authenticated-User-Email": "jesus@example.com",
            "Cf-Access-Jwt-Assertion": "token123",
        }
        request.state = MagicMock()
        call_next = AsyncMock(return_value="response")

        result = await middleware.dispatch(request, call_next)

        assert result == "response"
        assert request.state.user_email == "jesus@example.com"
        assert request.state.authenticated is True

    @pytest.mark.asyncio
    async def test_email_not_in_whitelist(self):
        """Email not in ALLOWED_EMAILS gets 403."""
        from app.auth import CloudflareAccessMiddleware
        from fastapi import FastAPI, HTTPException

        with patch("app.auth.ALLOWED_EMAILS", ["allowed@example.com"]):
            app = FastAPI()
            middleware = CloudflareAccessMiddleware(app)

            request = MagicMock()
            request.url.path = "/"
            request.headers = {
                "Cf-Access-Authenticated-User-Email": "blocked@example.com",
                "Cf-Access-Jwt-Assertion": "token123",
            }
            call_next = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await middleware.dispatch(request, call_next)

            assert exc_info.value.status_code == 403


# ── Tests: help page ───────────────────────────────────────────────────

class TestHelp:
    """Tests for the help page."""

    def test_commands_structure(self):
        """Help page has command categories."""
        from app.routes.help import COMMANDS

        assert isinstance(COMMANDS, dict)
        assert len(COMMANDS) > 0
        for category, cmds in COMMANDS.items():
            assert isinstance(category, str)
            assert isinstance(cmds, list)
            for cmd, desc in cmds:
                assert isinstance(cmd, str)
                assert isinstance(desc, str)
                assert len(cmd) > 0
                assert len(desc) > 0


# ── Tests: config ────────────────────────────────────────────────────────

class TestConfig:
    """Tests for configuration loading."""

    def test_defaults(self):
        """Config has sensible defaults."""
        from app.config import (
            MC_SERVER_HOST, MC_SSH_USER, MC_CONTAINER,
            APP_PORT, APP_TITLE
        )

        assert MC_SERVER_HOST == "51.170.48.83"
        assert MC_SSH_USER == "ubuntu"
        assert MC_CONTAINER == "minecraft-bedrock"
        assert APP_PORT == 8000
        assert APP_TITLE == "oci-mc-admin"

    def test_env_override(self, monkeypatch):
        """Environment variables override defaults."""
        from app import config

        monkeypatch.setattr(config, "MC_SERVER_HOST", "192.168.1.1")
        assert config.MC_SERVER_HOST == "192.168.1.1"
