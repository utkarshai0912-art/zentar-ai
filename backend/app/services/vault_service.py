"""
Zentar Intelligence — Vault Service

Business logic for managing user secrets: AI credentials, environment
variables, third-party integrations, MCP servers, and audit logging.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import asc, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.encryption import encryption_service
from app.models.vault import (
    AuditLog,
    EnvVariable,
    Integration,
    McpServer,
    PlatformApiKey,
    UserCredential,
)

logger = logging.getLogger("zentar.services.vault")


class VaultService:
    """Manages user secrets, credentials, integrations, and MCP servers."""

    PROVIDER_NAMES = [
        "openai", "anthropic", "gemini", "openrouter", "groq",
        "together", "fireworks", "deepseek", "xai", "mistral",
        "cohere", "azure_openai", "ollama", "lm_studio", "openai_compatible",
    ]

    INTEGRATION_TYPES = [
        "google", "github", "gitlab", "slack", "discord", "telegram",
        "whatsapp", "supabase", "postgresql", "mysql", "redis",
        "qdrant", "pinecone", "stripe", "razorpay", "aws",
        "cloudflare", "railway", "vercel", "netlify", "smtp",
        "twilio", "elevenlabs", "deepgram", "assemblyai",
    ]

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Audit Logging ────────────────────────

    async def _log_audit(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str = None,
        details: dict = None,
        ip_address: str = None,
    ):
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
        )
        self.db.add(entry)
        logger.info("Audit: %s %s %s by %s", action, resource_type, resource_id, user_id)

    # ── AI Provider Credentials ──────────────

    async def list_credentials(
        self,
        user_id: str,
        provider_name: str = None,
        enabled_only: bool = False,
    ) -> List[Dict[str, Any]]:
        q = select(UserCredential).where(
            UserCredential.user_id == user_id,
            UserCredential.is_deleted == False,
        )
        if provider_name:
            q = q.where(UserCredential.provider_name == provider_name)
        if enabled_only:
            q = q.where(UserCredential.is_enabled == True)
        q = q.order_by(UserCredential.priority.asc(), UserCredential.created_at.desc())

        result = await self.db.execute(q)
        rows = result.scalars().all()
        return [self._cred_to_dict(c) for c in rows]

    async def get_credential(self, credential_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        q = select(UserCredential).where(
            UserCredential.id == credential_id,
            UserCredential.user_id == user_id,
            UserCredential.is_deleted == False,
        )
        result = await self.db.execute(q)
        cred = result.scalar_one_or_none()
        return self._cred_to_dict(cred) if cred else None

    async def create_credential(self, user_id: str, data: dict, ip: str = None) -> Dict[str, Any]:
        cred = UserCredential(
            user_id=user_id,
            provider_name=data["provider_name"],
            label=data["label"],
            api_key_encrypted=encryption_service.encrypt(data["api_key"]),
            base_url=data.get("base_url"),
            org_id=data.get("org_id"),
            project_id=data.get("project_id"),
            default_model=data.get("default_model"),
            max_tokens=data.get("max_tokens"),
            temperature=data.get("temperature"),
            timeout=data.get("timeout", 30),
            is_enabled=data.get("is_enabled", True),
            is_default=data.get("is_default", False),
            priority=data.get("priority", 0),
        )

        if cred.is_default:
            await self._unset_default_credential(user_id, cred.provider_name)

        self.db.add(cred)
        await self.db.flush()
        await self._log_audit(user_id, "created", "credential", cred.id, ip_address=ip)
        return self._cred_to_dict(cred)

    async def update_credential(self, credential_id: str, user_id: str, data: dict, ip: str = None) -> Optional[Dict[str, Any]]:
        q = select(UserCredential).where(
            UserCredential.id == credential_id,
            UserCredential.user_id == user_id,
            UserCredential.is_deleted == False,
        )
        result = await self.db.execute(q)
        cred = result.scalar_one_or_none()
        if not cred:
            return None

        mutable = {
            "label", "base_url", "org_id", "project_id", "default_model",
            "max_tokens", "temperature", "timeout", "is_enabled", "is_default", "priority",
        }
        for key, value in data.items():
            if key == "api_key" and value:
                cred.api_key_encrypted = encryption_service.encrypt(value)
            elif key in mutable:
                setattr(cred, key, value)

        if data.get("is_default"):
            await self._unset_default_credential(user_id, cred.provider_name, exclude=cred.id)

        cred.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self._log_audit(user_id, "updated", "credential", cred.id, ip_address=ip)
        return self._cred_to_dict(cred)

    async def delete_credential(self, credential_id: str, user_id: str, ip: str = None) -> bool:
        q = select(UserCredential).where(
            UserCredential.id == credential_id,
            UserCredential.user_id == user_id,
            UserCredential.is_deleted == False,
        )
        result = await self.db.execute(q)
        cred = result.scalar_one_or_none()
        if not cred:
            return False
        cred.is_deleted = True
        cred.deleted_at = datetime.now(timezone.utc)
        await self._log_audit(user_id, "deleted", "credential", cred.id, ip_address=ip)
        await self.db.flush()
        return True

    async def test_credential(self, credential_id: str, user_id: str) -> Tuple[bool, str]:
        q = select(UserCredential).where(
            UserCredential.id == credential_id,
            UserCredential.user_id == user_id,
            UserCredential.is_deleted == False,
        )
        result = await self.db.execute(q)
        cred = result.scalar_one_or_none()
        if not cred:
            return False, "Credential not found"

        api_key = encryption_service.decrypt(cred.api_key_encrypted)
        provider = cred.provider_name
        base_url = cred.base_url
        model = cred.default_model or "gpt-4o"

        try:
            import httpx
            headers = {"Content-Type": "application/json"}

            if provider == "anthropic":
                headers["x-api-key"] = api_key
                headers["anthropic-version"] = "2023-06-01"
                url = f"{base_url or 'https://api.anthropic.com/v1'}/messages"
                payload = {"model": model, "max_tokens": 10, "messages": [{"role": "user", "content": "ping"}]}
            elif provider == "gemini":
                url = f"{base_url or 'https://generativelanguage.googleapis.com/v1beta'}/models/{model or 'gemini-pro'}:generateContent?key={api_key}"
                payload = {"contents": [{"parts": [{"text": "ping"}]}]}
            elif provider == "ollama":
                url = f"{base_url or 'http://localhost:11434'}/api/generate"
                payload = {"model": model or "llama3", "prompt": "ping", "stream": False}
            else:
                headers["Authorization"] = f"Bearer {api_key}"
                url = f"{base_url or 'https://api.openai.com/v1'}/chat/completions"
                payload = {"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5}

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code < 500:
                    return True, "Connection successful"
                return False, f"API error: {resp.status_code} - {resp.text[:200]}"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    async def _unset_default_credential(self, user_id: str, provider_name: str, exclude: str = None):
        q = select(UserCredential).where(
            UserCredential.user_id == user_id,
            UserCredential.provider_name == provider_name,
            UserCredential.is_default == True,
            UserCredential.is_deleted == False,
        )
        if exclude:
            q = q.where(UserCredential.id != exclude)
        result = await self.db.execute(q)
        for cred in result.scalars().all():
            cred.is_default = False

    def _cred_to_dict(self, cred: UserCredential) -> Dict[str, Any]:
        if not cred:
            return None
        return {
            "id": cred.id,
            "provider_name": cred.provider_name,
            "label": cred.label,
            "api_key_masked": encryption_service.mask(
                encryption_service.decrypt(cred.api_key_encrypted)
            ),
            "base_url": cred.base_url,
            "org_id": cred.org_id,
            "project_id": cred.project_id,
            "default_model": cred.default_model,
            "max_tokens": cred.max_tokens,
            "temperature": cred.temperature,
            "timeout": cred.timeout,
            "is_enabled": cred.is_enabled,
            "is_default": cred.is_default,
            "priority": cred.priority,
            "created_at": cred.created_at.isoformat() if cred.created_at else None,
            "updated_at": cred.updated_at.isoformat() if cred.updated_at else None,
        }

    async def reveal_credential_key(self, credential_id: str, user_id: str) -> Optional[str]:
        q = select(UserCredential).where(
            UserCredential.id == credential_id,
            UserCredential.user_id == user_id,
            UserCredential.is_deleted == False,
        )
        result = await self.db.execute(q)
        cred = result.scalar_one_or_none()
        if not cred:
            return None
        await self._log_audit(user_id, "revealed", "credential", cred.id)
        return encryption_service.decrypt(cred.api_key_encrypted)

    # ── Environment Variables ────────────────

    async def list_env_vars(
        self, user_id: str, category: str = None, search: str = None
    ) -> List[Dict[str, Any]]:
        q = select(EnvVariable).where(
            EnvVariable.user_id == user_id,
            EnvVariable.is_deleted == False,
        )
        if category:
            q = q.where(EnvVariable.category == category)
        if search:
            q = q.where(EnvVariable.name.ilike(f"%{search}%"))
        q = q.order_by(EnvVariable.category.asc(), EnvVariable.name.asc())

        result = await self.db.execute(q)
        return [self._env_to_dict(v) for v in result.scalars().all()]

    async def get_env_var(self, var_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        q = select(EnvVariable).where(
            EnvVariable.id == var_id,
            EnvVariable.user_id == user_id,
            EnvVariable.is_deleted == False,
        )
        result = await self.db.execute(q)
        var = result.scalar_one_or_none()
        return self._env_to_dict(var) if var else None

    async def create_env_var(self, user_id: str, data: dict, ip: str = None) -> Dict[str, Any]:
        var = EnvVariable(
            user_id=user_id,
            name=data["name"],
            value_encrypted=encryption_service.encrypt(data["value"]),
            category=data.get("category", "general"),
            is_sensitive=data.get("is_sensitive", True),
        )
        self.db.add(var)
        await self.db.flush()
        await self._log_audit(user_id, "created", "env_variable", var.id, ip_address=ip)
        return self._env_to_dict(var)

    async def update_env_var(self, var_id: str, user_id: str, data: dict, ip: str = None) -> Optional[Dict[str, Any]]:
        q = select(EnvVariable).where(
            EnvVariable.id == var_id,
            EnvVariable.user_id == user_id,
            EnvVariable.is_deleted == False,
        )
        result = await self.db.execute(q)
        var = result.scalar_one_or_none()
        if not var:
            return None

        if "value" in data and data["value"]:
            var.value_encrypted = encryption_service.encrypt(data["value"])
        if "name" in data:
            var.name = data["name"]
        if "category" in data:
            var.category = data["category"]
        if "is_sensitive" in data:
            var.is_sensitive = data["is_sensitive"]

        var.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self._log_audit(user_id, "updated", "env_variable", var.id, ip_address=ip)
        return self._env_to_dict(var)

    async def delete_env_var(self, var_id: str, user_id: str, ip: str = None) -> bool:
        q = select(EnvVariable).where(
            EnvVariable.id == var_id,
            EnvVariable.user_id == user_id,
            EnvVariable.is_deleted == False,
        )
        result = await self.db.execute(q)
        var = result.scalar_one_or_none()
        if not var:
            return False
        var.is_deleted = True
        var.deleted_at = datetime.now(timezone.utc)
        await self._log_audit(user_id, "deleted", "env_variable", var.id, ip_address=ip)
        await self.db.flush()
        return True

    async def reveal_env_var(self, var_id: str, user_id: str) -> Optional[str]:
        q = select(EnvVariable).where(
            EnvVariable.id == var_id,
            EnvVariable.user_id == user_id,
            EnvVariable.is_deleted == False,
        )
        result = await self.db.execute(q)
        var = result.scalar_one_or_none()
        if not var:
            return None
        await self._log_audit(user_id, "revealed", "env_variable", var.id)
        return encryption_service.decrypt(var.value_encrypted)

    def _env_to_dict(self, var: EnvVariable) -> Dict[str, Any]:
        if not var:
            return None
        decrypted = encryption_service.decrypt(var.value_encrypted)
        return {
            "id": var.id,
            "name": var.name,
            "value_masked": encryption_service.mask(decrypted) if var.is_sensitive else decrypted,
            "category": var.category,
            "is_sensitive": var.is_sensitive,
            "created_at": var.created_at.isoformat() if var.created_at else None,
            "updated_at": var.updated_at.isoformat() if var.updated_at else None,
        }

    async def get_env_categories(self, user_id: str) -> List[Dict[str, int]]:
        q = select(EnvVariable).where(
            EnvVariable.user_id == user_id,
            EnvVariable.is_deleted == False,
        )
        result = await self.db.execute(q)
        counts = {}
        for var in result.scalars().all():
            cat = var.category or "general"
            counts[cat] = counts.get(cat, 0) + 1
        return [{"category": k, "count": v} for k, v in sorted(counts.items())]

    # ── Integrations ─────────────────────────

    async def list_integrations(self, user_id: str) -> List[Dict[str, Any]]:
        q = select(Integration).where(
            Integration.user_id == user_id,
            Integration.is_deleted == False,
        ).order_by(Integration.integration_type.asc())
        result = await self.db.execute(q)
        return [self._int_to_dict(i) for i in result.scalars().all()]

    async def get_integration(self, integration_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        q = select(Integration).where(
            Integration.id == integration_id,
            Integration.user_id == user_id,
            Integration.is_deleted == False,
        )
        result = await self.db.execute(q)
        integ = result.scalar_one_or_none()
        return self._int_to_dict(integ) if integ else None

    async def create_integration(self, user_id: str, data: dict, ip: str = None) -> Dict[str, Any]:
        integ = Integration(
            user_id=user_id,
            integration_type=data["integration_type"],
            label=data["label"],
            credentials_encrypted=encryption_service.encrypt(
                json.dumps(data.get("credentials", {}))
            ) if data.get("credentials") else None,
            is_enabled=data.get("is_enabled", True),
        )
        self.db.add(integ)
        await self.db.flush()
        await self._log_audit(user_id, "created", "integration", integ.id, ip_address=ip)
        return self._int_to_dict(integ)

    async def update_integration(self, integration_id: str, user_id: str, data: dict, ip: str = None) -> Optional[Dict[str, Any]]:
        q = select(Integration).where(
            Integration.id == integration_id,
            Integration.user_id == user_id,
            Integration.is_deleted == False,
        )
        result = await self.db.execute(q)
        integ = result.scalar_one_or_none()
        if not integ:
            return None

        if "credentials" in data and data["credentials"]:
            integ.credentials_encrypted = encryption_service.encrypt(json.dumps(data["credentials"]))
        if "label" in data:
            integ.label = data["label"]
        if "is_enabled" in data:
            integ.is_enabled = data["is_enabled"]

        integ.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self._log_audit(user_id, "updated", "integration", integ.id, ip_address=ip)
        return self._int_to_dict(integ)

    async def delete_integration(self, integration_id: str, user_id: str, ip: str = None) -> bool:
        q = select(Integration).where(
            Integration.id == integration_id,
            Integration.user_id == user_id,
            Integration.is_deleted == False,
        )
        result = await self.db.execute(q)
        integ = result.scalar_one_or_none()
        if not integ:
            return False
        integ.is_deleted = True
        integ.deleted_at = datetime.now(timezone.utc)
        await self._log_audit(user_id, "deleted", "integration", integ.id, ip_address=ip)
        await self.db.flush()
        return True

    async def test_integration(self, integration_id: str, user_id: str) -> Tuple[bool, str]:
        q = select(Integration).where(
            Integration.id == integration_id,
            Integration.user_id == user_id,
            Integration.is_deleted == False,
        )
        result = await self.db.execute(q)
        integ = result.scalar_one_or_none()
        if not integ:
            return False, "Integration not found"

        import httpx
        try:
            creds = {}
            if integ.credentials_encrypted:
                creds = json.loads(encryption_service.decrypt(integ.credentials_encrypted))

            itype = integ.integration_type
            async with httpx.AsyncClient(timeout=15) as client:
                if itype == "github":
                    token = creds.get("token") or creds.get("personal_access_token")
                    resp = await client.get(
                        "https://api.github.com/user",
                        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"},
                    )
                elif itype == "gitlab":
                    token = creds.get("token") or creds.get("personal_access_token")
                    resp = await client.get(
                        "https://gitlab.com/api/v4/user",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                elif itype == "slack":
                    token = creds.get("token") or creds.get("bot_token")
                    resp = await client.get(
                        "https://slack.com/api/auth.test",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                elif itype == "discord":
                    token = creds.get("token") or creds.get("bot_token")
                    resp = await client.get(
                        "https://discord.com/api/v10/users/@me",
                        headers={"Authorization": f"Bot {token}"},
                    )
                elif itype in ("stripe", "razorpay"):
                    api_key = creds.get("api_key") or creds.get("secret_key")
                    base = "https://api.stripe.com/v1" if itype == "stripe" else "https://api.razorpay.com/v1"
                    resp = await client.get(f"{base}/balance", auth=(api_key, "") if itype == "stripe" else (api_key, ""))
                elif itype == "smtp":
                    return True, "SMTP validation requires sending a test email"
                else:
                    return True, f"Connection test for {itype} submitted"

                if resp.status_code < 500:
                    integ.health_status = "healthy"
                else:
                    integ.health_status = "unhealthy"
                integ.last_health_check_at = datetime.now(timezone.utc)
                await self.db.flush()

                if resp.status_code < 400:
                    return True, f"Connection successful ({resp.status_code})"
                return False, f"Connection failed: {resp.status_code} - {resp.text[:200]}"
        except Exception as e:
            integ.health_status = "unhealthy"
            integ.last_health_check_at = datetime.now(timezone.utc)
            await self.db.flush()
            return False, f"Connection failed: {str(e)}"

    def _int_to_dict(self, integ: Integration) -> Dict[str, Any]:
        if not integ:
            return None
        return {
            "id": integ.id,
            "integration_type": integ.integration_type,
            "label": integ.label,
            "has_credentials": bool(integ.credentials_encrypted),
            "is_enabled": integ.is_enabled,
            "health_status": integ.health_status,
            "last_health_check_at": integ.last_health_check_at.isoformat() if integ.last_health_check_at else None,
            "created_at": integ.created_at.isoformat() if integ.created_at else None,
            "updated_at": integ.updated_at.isoformat() if integ.updated_at else None,
        }

    # ── MCP Servers ──────────────────────────

    async def list_mcp_servers(self, user_id: str) -> List[Dict[str, Any]]:
        q = select(McpServer).where(
            McpServer.user_id == user_id,
            McpServer.is_deleted == False,
        ).order_by(McpServer.name.asc())
        result = await self.db.execute(q)
        return [self._mcp_to_dict(m) for m in result.scalars().all()]

    async def get_mcp_server(self, server_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        q = select(McpServer).where(
            McpServer.id == server_id,
            McpServer.user_id == user_id,
            McpServer.is_deleted == False,
        )
        result = await self.db.execute(q)
        server = result.scalar_one_or_none()
        return self._mcp_to_dict(server) if server else None

    async def create_mcp_server(self, user_id: str, data: dict, ip: str = None) -> Dict[str, Any]:
        server = McpServer(
            user_id=user_id,
            name=data["name"],
            description=data.get("description"),
            server_url=data["server_url"],
            auth_type=data.get("auth_type", "none"),
            auth_config_encrypted=encryption_service.encrypt(
                json.dumps(data.get("auth_config", {}))
            ) if data.get("auth_config") else None,
            permissions=data.get("permissions", []),
            allowed_agents=data.get("allowed_agents", []),
            is_enabled=data.get("is_enabled", True),
            auto_reconnect=data.get("auto_reconnect", False),
        )
        self.db.add(server)
        await self.db.flush()
        await self._log_audit(user_id, "created", "mcp_server", server.id, ip_address=ip)
        return self._mcp_to_dict(server)

    async def update_mcp_server(self, server_id: str, user_id: str, data: dict, ip: str = None) -> Optional[Dict[str, Any]]:
        q = select(McpServer).where(
            McpServer.id == server_id,
            McpServer.user_id == user_id,
            McpServer.is_deleted == False,
        )
        result = await self.db.execute(q)
        server = result.scalar_one_or_none()
        if not server:
            return None

        mutable = {
            "name", "description", "server_url", "auth_type",
            "permissions", "allowed_agents", "is_enabled", "auto_reconnect",
        }
        for key, value in data.items():
            if key == "auth_config" and value:
                server.auth_config_encrypted = encryption_service.encrypt(json.dumps(value))
            elif key in mutable:
                setattr(server, key, value)

        server.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self._log_audit(user_id, "updated", "mcp_server", server.id, ip_address=ip)
        return self._mcp_to_dict(server)

    async def delete_mcp_server(self, server_id: str, user_id: str, ip: str = None) -> bool:
        q = select(McpServer).where(
            McpServer.id == server_id,
            McpServer.user_id == user_id,
            McpServer.is_deleted == False,
        )
        result = await self.db.execute(q)
        server = result.scalar_one_or_none()
        if not server:
            return False
        server.is_deleted = True
        server.deleted_at = datetime.now(timezone.utc)
        await self._log_audit(user_id, "deleted", "mcp_server", server.id, ip_address=ip)
        await self.db.flush()
        return True

    async def test_mcp_server(self, server_id: str, user_id: str) -> Tuple[bool, str]:
        q = select(McpServer).where(
            McpServer.id == server_id,
            McpServer.user_id == user_id,
            McpServer.is_deleted == False,
        )
        result = await self.db.execute(q)
        server = result.scalar_one_or_none()
        if not server:
            return False, "MCP server not found"

        import httpx
        try:
            headers = {"Content-Type": "application/json"}
            if server.auth_type == "api_key":
                auth_config = json.loads(
                    encryption_service.decrypt(server.auth_config_encrypted)
                ) if server.auth_config_encrypted else {}
                headers[auth_config.get("header_name", "X-API-Key")] = auth_config.get("api_key", "")
            elif server.auth_type == "bearer":
                auth_config = json.loads(
                    encryption_service.decrypt(server.auth_config_encrypted)
                ) if server.auth_config_encrypted else {}
                headers["Authorization"] = f"Bearer {auth_config.get('token', '')}"

            async with httpx.AsyncClient(timeout=10) as client:
                try:
                    resp = await client.get(server.server_url.rstrip("/") + "/health", headers=headers)
                except httpx.HTTPStatusError:
                    resp = await client.get(server.server_url, headers=headers)

                if resp.status_code < 500:
                    server.health_status = "healthy"
                else:
                    server.health_status = "unhealthy"
                server.last_health_check_at = datetime.now(timezone.utc)
                await self.db.flush()
                return True, f"Server reachable ({resp.status_code})"
        except Exception as e:
            server.health_status = "unhealthy"
            server.last_health_check_at = datetime.now(timezone.utc)
            await self.db.flush()
            return False, f"Connection failed: {str(e)}"

    def _mcp_to_dict(self, server: McpServer) -> Dict[str, Any]:
        if not server:
            return None
        return {
            "id": server.id,
            "name": server.name,
            "description": server.description,
            "server_url": server.server_url,
            "auth_type": server.auth_type,
            "has_auth_config": bool(server.auth_config_encrypted),
            "permissions": server.permissions,
            "allowed_agents": server.allowed_agents,
            "is_enabled": server.is_enabled,
            "health_status": server.health_status,
            "last_health_check_at": server.last_health_check_at.isoformat() if server.last_health_check_at else None,
            "auto_reconnect": server.auto_reconnect,
            "created_at": server.created_at.isoformat() if server.created_at else None,
            "updated_at": server.updated_at.isoformat() if server.updated_at else None,
        }

    # ── Platform API Keys (Admin) ────────────

    async def list_platform_keys(self) -> List[Dict[str, Any]]:
        q = select(PlatformApiKey).where(
            PlatformApiKey.is_deleted == False,
        ).order_by(PlatformApiKey.provider_name.asc())
        result = await self.db.execute(q)
        return [self._pkey_to_dict(k) for k in result.scalars().all()]

    async def get_platform_key(self, key_id: str) -> Optional[Dict[str, Any]]:
        q = select(PlatformApiKey).where(
            PlatformApiKey.id == key_id,
            PlatformApiKey.is_deleted == False,
        )
        result = await self.db.execute(q)
        key = result.scalar_one_or_none()
        return self._pkey_to_dict(key) if key else None

    async def upsert_platform_key(self, data: dict, ip: str = None) -> Dict[str, Any]:
        q = select(PlatformApiKey).where(
            PlatformApiKey.provider_name == data["provider_name"],
        )
        result = await self.db.execute(q)
        existing = result.scalar_one_or_none()

        if existing:
            if "api_key" in data and data["api_key"]:
                existing.api_key_encrypted = encryption_service.encrypt(data["api_key"])
            if "label" in data:
                existing.label = data["label"]
            if "base_url" in data:
                existing.base_url = data["base_url"]
            if "org_id" in data:
                existing.org_id = data["org_id"]
            if "default_model" in data:
                existing.default_model = data["default_model"]
            if "is_active" in data:
                existing.is_active = data["is_active"]
            existing.updated_at = datetime.now(timezone.utc)
            await self._log_audit("admin", "updated", "platform_key", existing.id, ip_address=ip)
            return self._pkey_to_dict(existing)
        else:
            key = PlatformApiKey(
                provider_name=data["provider_name"],
                label=data.get("label", data["provider_name"]),
                api_key_encrypted=encryption_service.encrypt(data["api_key"]),
                base_url=data.get("base_url"),
                org_id=data.get("org_id"),
                default_model=data.get("default_model"),
                is_active=data.get("is_active", True),
            )
            self.db.add(key)
            await self.db.flush()
            await self._log_audit("admin", "created", "platform_key", key.id, ip_address=ip)
            return self._pkey_to_dict(key)

    async def delete_platform_key(self, key_id: str, ip: str = None) -> bool:
        q = select(PlatformApiKey).where(
            PlatformApiKey.id == key_id,
            PlatformApiKey.is_deleted == False,
        )
        result = await self.db.execute(q)
        key = result.scalar_one_or_none()
        if not key:
            return False
        key.is_deleted = True
        key.deleted_at = datetime.now(timezone.utc)
        await self._log_audit("admin", "deleted", "platform_key", key.id, ip_address=ip)
        await self.db.flush()
        return True

    def _pkey_to_dict(self, key: PlatformApiKey) -> Dict[str, Any]:
        if not key:
            return None
        return {
            "id": key.id,
            "provider_name": key.provider_name,
            "label": key.label,
            "api_key_masked": encryption_service.mask(
                encryption_service.decrypt(key.api_key_encrypted)
            ),
            "base_url": key.base_url,
            "org_id": key.org_id,
            "default_model": key.default_model,
            "is_active": key.is_active,
            "created_at": key.created_at.isoformat() if key.created_at else None,
            "updated_at": key.updated_at.isoformat() if key.updated_at else None,
        }

    # ── User Credential Helper for AI Service ─

    async def get_user_provider_config(
        self, user_id: str, provider_name: str = None
    ) -> Dict[str, Any]:
        """Build a provider config dict using user credentials with platform fallback."""
        q = select(UserCredential).where(
            UserCredential.user_id == user_id,
            UserCredential.is_enabled == True,
            UserCredential.is_deleted == False,
        )
        if provider_name:
            q = q.where(UserCredential.provider_name == provider_name)
        q = q.order_by(UserCredential.priority.asc(), UserCredential.created_at.desc())
        result = await self.db.execute(q)
        user_creds = result.scalars().all()

        # Build config from user credentials
        config = {}
        for cred in user_creds:
            pn = cred.provider_name
            if pn not in config or cred.is_default:
                config[pn] = {
                    "api_key": encryption_service.decrypt(cred.api_key_encrypted),
                    "base_url": cred.base_url,
                    "default_model": cred.default_model,
                    "max_tokens": cred.max_tokens,
                    "temperature": cred.temperature,
                    "timeout": cred.timeout,
                }

        # Fall back to platform keys for providers not configured by user
        pq = select(PlatformApiKey).where(
            PlatformApiKey.is_active == True,
            PlatformApiKey.is_deleted == False,
        )
        if provider_name:
            pq = pq.where(PlatformApiKey.provider_name == provider_name)
        presult = await self.db.execute(pq)
        for pkey in presult.scalars().all():
            pn = pkey.provider_name
            if pn not in config:
                config[pn] = {
                    "api_key": encryption_service.decrypt(pkey.api_key_encrypted),
                    "base_url": pkey.base_url,
                    "default_model": pkey.default_model,
                }

        # Finally, fall back to env settings
        from app.core.config import get_settings
        s = get_settings()
        env_providers = {
            "openai": {"api_key": s.OPENAI_API_KEY, "base_url": s.OPENAI_BASE_URL, "default_model": s.OPENAI_DEFAULT_MODEL},
            "anthropic": {"api_key": s.ANTHROPIC_API_KEY, "base_url": s.ANTHROPIC_BASE_URL, "default_model": s.ANTHROPIC_DEFAULT_MODEL},
            "gemini": {"api_key": s.GEMINI_API_KEY, "base_url": s.GEMINI_BASE_URL, "default_model": None},
            "deepseek": {"api_key": s.DEEPSEEK_API_KEY, "base_url": s.DEEPSEEK_BASE_URL, "default_model": s.DEEPSEEK_DEFAULT_MODEL},
            "openrouter": {"api_key": s.OPENROUTER_API_KEY, "base_url": s.OPENROUTER_BASE_URL, "default_model": None},
            "qwen": {"api_key": s.QWEN_API_KEY, "base_url": s.QWEN_BASE_URL, "default_model": None},
            "ollama": {"api_key": None, "base_url": s.OLLAMA_BASE_URL, "default_model": s.OLLAMA_DEFAULT_MODEL},
        }
        for pn, cfg in env_providers.items():
            if cfg.get("api_key") and pn not in config:
                config[pn] = cfg

        return config


def get_user_provider_priority(config: Dict[str, Any]) -> List[str]:
    """Return ordered list of provider names for fallback."""
    ordered = ["openai", "anthropic", "gemini", "deepseek", "openrouter", "groq", "together",
               "fireworks", "mistral", "cohere", "xai", "azure_openai", "ollama", "qwen"]
    return [p for p in ordered if p in config]