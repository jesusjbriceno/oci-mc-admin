# oci-mc-admin

Web panel to manage a Minecraft Bedrock server running on OCI VPS.

## Stack

- **Backend**: Python 3.11 + FastAPI
- **Frontend**: Jinja2 + HTMX + Tailwind CSS (CDN)
- **Deployment**: Docker → Dokploy
- **Auth**: Cloudflare Zero Trust (Google OAuth) + email whitelist

## MVP Features

- [x] Server status dashboard (online/offline, version, uptime, world)
- [x] Connected players list
- [x] Command console (send commands, view output)
- [x] Whitelist management (add/remove/list)
- [x] Recent server logs
- [x] Manual world backups
- [x] Scheduled backups (configurable)

## Project Structure

```
oci-mc-admin/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings from env vars
│   ├── server.py            # Minecraft server client (SSH/send-command)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── dashboard.py     # Status, players
│   │   ├── console.py       # Command sending
│   │   ├── whitelist.py     # Allowlist management
│   │   ├── logs.py          # Server logs viewer
│   │   └── backups.py       # Backup management
│   └── templates/
│       ├── base.html         # Layout + HTMX + Tailwind
│       ├── dashboard.html
│       ├── console.html
│       ├── whitelist.html
│       ├── logs.html
│       └── backups.html
├── static/
│   └── (empty — using CDN for Tailwind)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `MC_SERVER_HOST` | VPS hostname/IP | `51.170.48.83` |
| `MC_SSH_KEY` | Path to SSH private key | `~/.ssh/id_ed25519_oci_new` |
| `MC_SSH_USER` | SSH username | `ubuntu` |
| `MC_CONTAINER` | Docker container name | `minecraft-bedrock` |
| `MC_DATA_DIR` | Server data directory on host | `/opt/minecraft-bedrock/data` |
| `BACKUP_DIR` | Backup storage directory | `/opt/minecraft-bedrock/backups` |
| `BACKUP_RETENTION` | Number of backups to keep | `7` |
| `CF_TEAM_DOMAIN` | Cloudflare team domain for auth check | (required) |
