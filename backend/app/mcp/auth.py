"""
Zentar Intelligence — MCP Authentication

Handles OAuth and token-based authentication for MCP connections.
"""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import get_settings

logger = logging.getLogger("zentar.mcp.auth")

settings = get_settings()


class MCPClientRegistration:
    """Represents a registered MCP client."""

    def __init__(
        self,
        client_id: str,
        client_name: str,
        client_uri: str,
        redirect_uris: List[str],
        scopes: List[str],
        client_secret: Optional[str] = None,
    ):
        self.client_id = client_id
        self.client_name = client_name
        self.client_uri = client_uri
        self.redirect_uris = redirect_uris
        self.scopes = scopes
        self.client_secret = client_secret
        self.created_at = time.time()
        self.is_confidential = bool(client_secret)


class MCPAuthProvider:
    """Handles authorization for MCP connections.

    Supports:
    - OAuth 2.0 authorization code flow
    - Token-based authentication (Bearer tokens)
    - API key authentication
    """

    def __init__(self):
        self._clients: Dict[str, MCPClientRegistration] = {}
        self._tokens: Dict[str, Dict[str, Any]] = {}
        self._auth_codes: Dict[str, Dict[str, Any]] = {}

    def register_client(
        self,
        client_name: str,
        client_uri: str,
        redirect_uris: List[str],
        scopes: Optional[List[str]] = None,
        generate_secret: bool = False,
    ) -> Dict[str, str]:
        """Register a new MCP client for OAuth."""
        client_id = f"mcp_{uuid.uuid4().hex[:16]}"
        client_secret = None

        if generate_secret:
            client_secret = f"mcp_secret_{uuid.uuid4().hex[:24]}"

        registration = MCPClientRegistration(
            client_id=client_id,
            client_name=client_name,
            client_uri=client_uri,
            redirect_uris=redirect_uris,
            scopes=scopes or ["tools:read", "tools:execute"],
            client_secret=client_secret,
        )
        self._clients[client_id] = registration
        logger.info("Registered MCP client: %s (%s)", client_name, client_id)

        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "client_name": client_name,
        }

    def authorize(
        self,
        client_id: str,
        redirect_uri: str,
        scopes: List[str],
        user_id: str,
    ) -> Optional[str]:
        """Create an authorization code for OAuth flow."""
        client = self._clients.get(client_id)
        if not client:
            logger.warning("Unknown client: %s", client_id)
            return None

        if redirect_uri not in client.redirect_uris:
            logger.warning("Invalid redirect URI: %s", redirect_uri)
            return None

        code = f"mcp_auth_{uuid.uuid4().hex[:24]}"
        self._auth_codes[code] = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scopes": scopes,
            "user_id": user_id,
            "expires_at": time.time() + 300,  # 5 minute expiry
            "used": False,
        }
        return code

    def exchange_code(
        self,
        code: str,
        client_id: str,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Exchange an authorization code for tokens."""
        auth_data = self._auth_codes.get(code)
        if not auth_data:
            return None

        if auth_data["used"]:
            return None

        if auth_data["expires_at"] < time.time():
            return None

        if auth_data["client_id"] != client_id:
            return None

        # Verify client secret if confidential client
        client = self._clients.get(client_id)
        if client and client.is_confidential:
            if not client_secret or client_secret != client.client_secret:
                return None

        auth_data["used"] = True

        # Issue tokens
        access_token = f"mcp_token_{uuid.uuid4().hex[:32]}"
        refresh_token = f"mcp_refresh_{uuid.uuid4().hex[:32]}"

        self._tokens[access_token] = {
            "client_id": client_id,
            "user_id": auth_data["user_id"],
            "scopes": auth_data["scopes"],
            "token_type": "access",
            "expires_at": time.time() + 3600,
        }
        self._tokens[refresh_token] = {
            "client_id": client_id,
            "user_id": auth_data["user_id"],
            "scopes": auth_data["scopes"],
            "token_type": "refresh",
            "expires_at": time.time() + 86400 * 30,
        }

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 3600,
        }

    def validate_token(self, token: str, required_scopes: Optional[List[str]] = None) -> bool:
        """Validate a Bearer token."""
        token_data = self._tokens.get(token)
        if not token_data:
            return False

        if token_data["expires_at"] < time.time():
            self._tokens.pop(token, None)
            return False

        if token_data["token_type"] != "access":
            return False

        if required_scopes:
            token_scopes = set(token_data.get("scopes", []))
            if not all(s in token_scopes for s in required_scopes):
                return False

        return True

    def validate_api_key(self, api_key: str) -> Optional[str]:
        """Validate an API key. Returns user_id if valid."""
        # Delegate to core API key validation
        from app.core.security import validate_api_key
        return validate_api_key(api_key)

    def revoke_token(self, token: str) -> bool:
        """Revoke a token."""
        return bool(self._tokens.pop(token, None))

    def cleanup_expired(self):
        """Remove expired tokens and codes."""
        now = time.time()
        self._tokens = {k: v for k, v in self._tokens.items() if v["expires_at"] > now}
        self._auth_codes = {k: v for k, v in self._auth_codes.items() if v["expires_at"] > now and not v["used"]}


# Global MCP auth provider
mcp_auth_provider = MCPAuthProvider()
