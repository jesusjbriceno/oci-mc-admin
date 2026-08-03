"""Application configuration — reads from environment with sensible defaults."""

import os
from pathlib import Path

# ── Minecraft Server Connection ────────────────────────────────────────

MC_SERVER_HOST: str = os.getenv("MC_SERVER_HOST", "51.170.48.83")
MC_SSH_USER: str = os.getenv("MC_SSH_USER", "ubuntu")
MC_SSH_KEY: str = os.getenv(
    "MC_SSH_KEY",
    str(Path.home() / ".ssh" / "id_ed25519_oci_new"),
)
MC_CONTAINER: str = os.getenv("MC_CONTAINER", "minecraft-bedrock")
MC_DATA_DIR: str = os.getenv("MC_DATA_DIR", "/opt/minecraft-bedrock/data")
MC_SSH_PORT: int = int(os.getenv("MC_SSH_PORT", "22"))

# ── Backups ─────────────────────────────────────────────────────────────

BACKUP_DIR: str = os.getenv("BACKUP_DIR", "/opt/minecraft-bedrock/backups")
BACKUP_RETENTION: int = int(os.getenv("BACKUP_RETENTION", "7"))

# ── Auth (Cloudflare Zero Trust) ────────────────────────────────────────

# Cloudflare Access JWT verification
CF_TEAM_DOMAIN: str = os.getenv("CF_TEAM_DOMAIN", "")
CF_APP_AUD: str = os.getenv("CF_APP_AUD", "")  # Application Audience (AUD) tag
ALLOWED_EMAILS: list[str] = [
    e.strip()
    for e in os.getenv("ALLOWED_EMAILS", "").split(",")
    if e.strip()
]

# ── App ─────────────────────────────────────────────────────────────────

APP_TITLE: str = "oci-mc-admin"
APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
