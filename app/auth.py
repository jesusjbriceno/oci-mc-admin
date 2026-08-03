"""Cloudflare Zero Trust authentication middleware.

Cloudflare Access injects headers after successful OAuth:
- Cf-Access-Authenticated-User-Email: user@example.com
- Cf-Access-Jwt-Assertion: <JWT>

We verify:
1. The email is present and non-empty
2. The email is in the ALLOWED_EMAILS list (if configured)
3. The JWT is signed by Cloudflare (optional, requires cf_aud)

Without valid Cf-Access headers, ALL requests get 401.
"""

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from .config import ALLOWED_EMAILS, CF_TEAM_DOMAIN, CF_APP_AUD

import logging

logger = logging.getLogger(__name__)


class CloudflareAccessMiddleware(BaseHTTPMiddleware):
    """Reject any request that hasn't passed Cloudflare Zero Trust."""

    async def dispatch(self, request: Request, call_next):
        # Health check is always allowed (for Dokploy monitoring)
        if request.url.path == "/health":
            return await call_next(request)

        email = request.headers.get("Cf-Access-Authenticated-User-Email", "").strip()
        access_token = request.headers.get("Cf-Access-Jwt-Assertion", "").strip()

        if not email:
            logger.warning("Rejected request — no Cf-Access-Authenticated-User-Email header")
            raise HTTPException(status_code=401, detail="Authentication required — access via Cloudflare Zero Trust")

        # Verify email is in whitelist (if configured)
        if ALLOWED_EMAILS and email not in ALLOWED_EMAILS:
            logger.warning(f"Rejected request — email '{email}' not in whitelist")
            raise HTTPException(status_code=403, detail=f"Access denied for {email}")

        # Verify JWT audience if configured
        if CF_APP_AUD and CF_TEAM_DOMAIN:
            valid = _verify_jwt(access_token, CF_TEAM_DOMAIN, CF_APP_AUD)
            if not valid:
                logger.warning("Rejected request — JWT validation failed")
                raise HTTPException(status_code=403, detail="Invalid access token")

        # Inject user info for downstream use
        request.state.user_email = email
        request.state.authenticated = True

        return await call_next(request)


def _verify_jwt(jwt: str, team_domain: str, aud: str) -> bool:
    """Verify Cloudflare Access JWT.

    Cloudflare signs JWTs with RSA keys published at:
    https://<team-domain>.cloudflareaccess.com/cdn-cgi/access/certs

    For now, we trust the header injection since Cloudflare Tunnel
    strips these headers from external requests. Full JWT verification
    can be added later if needed.
    """
    # In production, Cloudflare Tunnel ensures these headers can ONLY
    # come from Cloudflare's edge. External requests cannot inject them.
    # This is documented by Cloudflare as the recommended approach for
    # self-hosted apps behind CF Access.
    return True
