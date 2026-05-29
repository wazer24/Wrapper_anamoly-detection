"""Secrets management abstraction layer.
Supports three backends in order of preference:
1. HashiCorp Vault    (VAULT_ADDR + VAULT_TOKEN)
2. File-based secrets  (SECRETS_DIR, e.g. Docker secrets at /run/secrets)
3. Environment vars    (default, no extra setup)
"""
import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_SECRET_BACKEND: Optional[str] = None


def _detect_backend() -> str:
    global _SECRET_BACKEND
    if _SECRET_BACKEND:
        return _SECRET_BACKEND
    if os.environ.get("VAULT_ADDR") and os.environ.get("VAULT_TOKEN"):
        _SECRET_BACKEND = "vault"
    elif os.environ.get("SECRETS_DIR"):
        _SECRET_BACKEND = "file"
    else:
        _SECRET_BACKEND = "env"
    return _SECRET_BACKEND


def _get_from_env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _get_from_file(key: str, default: str = "") -> str:
    secrets_dir = Path(os.environ.get("SECRETS_DIR", "/run/secrets"))
    for ext in ("", ".txt", ".json"):
        candidate = secrets_dir / f"{key}{ext}"
        if candidate.exists():
            raw = candidate.read_text(encoding="utf-8").strip()
            if ext == ".json":
                try:
                    data = json.loads(raw)
                    if isinstance(data, dict) and key in data:
                        return str(data[key])
                except json.JSONDecodeError:
                    pass
            return raw
    return default


def _get_from_vault(key: str, default: str = "") -> str:
    try:
        import hvac
        vault_addr = os.environ.get("VAULT_ADDR", "")
        vault_token = os.environ.get("VAULT_TOKEN", "")
        vault_path = os.environ.get("VAULT_SECRET_PATH", "secret/data/ai-db-optimizer")
        if not vault_addr or not vault_token:
            return default
        client = hvac.Client(url=vault_addr, token=vault_token)
        secret = client.secrets.kv.v2.read_secret_version(path=vault_path)
        data = secret.get("data", {}).get("data", {})
        return str(data.get(key, default))
    except Exception as e:
        logger.warning("[Secrets] Vault read failed for '%s': %s", key, e)
        return default


def get_secret(key: str, default: str = "") -> str:
    backend = _detect_backend()
    if backend == "vault":
        return _get_from_vault(key, default)
    elif backend == "file":
        return _get_from_file(key, default)
    return _get_from_env(key, default)
