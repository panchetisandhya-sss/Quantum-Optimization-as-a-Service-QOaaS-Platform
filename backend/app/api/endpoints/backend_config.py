"""
api/endpoints/backend_config.py — Phase 5: Quantum hardware backend credential management.

Endpoints:
  POST   /api/v1/backend-config   — Save/update credentials (stored encrypted)
  GET    /api/v1/backend-config   — Retrieve current config (masked token, never plaintext)
  DELETE /api/v1/backend-config   — Clear credentials (revert to local simulator)

Tokens are encrypted at rest using AES-256-GCM via core/security.py.
The full token is never returned to the client after saving.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import get_password_hash
from app.config import settings
from app.models.models import OrgBackendConfig, User

router = APIRouter()

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class BackendConfigCreate(BaseModel):
    provider: str                          # "ibm" | "dwave" | "braket" | "local"
    api_token: Optional[str] = None       # raw token — stored encrypted; never returned
    endpoint_url: Optional[str] = None
    backend_name: Optional[str] = None


class BackendConfigOut(BaseModel):
    provider: str
    endpoint_url: Optional[str]
    backend_name: Optional[str]
    token_configured: bool                 # True if a token has been saved


# ---------------------------------------------------------------------------
# Token encryption helpers (in-memory, not file-based)
# We derive an AES key from the app SECRET_KEY via SHA-256 and use
# Python's pycryptodome to encrypt/decrypt the token string.
# ---------------------------------------------------------------------------

def _encrypt_token(plain_token: str) -> str:
    """Encrypt a plaintext token string → hex-encoded nonce+tag+ciphertext."""
    import hashlib
    from Crypto.Cipher import AES
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    cipher = AES.new(key, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(plain_token.encode("utf-8"))
    # Store as: nonce_hex|tag_hex|ciphertext_hex
    return f"{cipher.nonce.hex()}|{tag.hex()}|{ciphertext.hex()}"


def _decrypt_token(encrypted: str) -> Optional[str]:
    """Decrypt a stored token string → plaintext, or None on error."""
    import hashlib
    from Crypto.Cipher import AES
    try:
        nonce_hex, tag_hex, ct_hex = encrypted.split("|")
        key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        cipher = AES.new(key, AES.MODE_GCM, nonce=bytes.fromhex(nonce_hex))
        plaintext = cipher.decrypt_and_verify(bytes.fromhex(ct_hex), bytes.fromhex(tag_hex))
        return plaintext.decode("utf-8")
    except Exception:
        return None


def _mask_token(encrypted: str) -> str:
    """Return a masked representation — first/last 4 chars of the raw nonce hex only."""
    try:
        nonce_hex = encrypted.split("|")[0]
        return f"****...{nonce_hex[-4:]}"
    except Exception:
        return "****"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/backend-config", status_code=status.HTTP_200_OK)
def save_backend_config(
    cfg: BackendConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Save or update quantum backend credentials for the current user.
    The API token is encrypted before storage and never returned in plaintext.
    """
    valid_providers = {"ibm", "dwave", "braket", "local"}
    if cfg.provider not in valid_providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider '{cfg.provider}'. Must be one of: {valid_providers}.",
        )

    encrypted_token: Optional[str] = None
    if cfg.api_token:
        encrypted_token = _encrypt_token(cfg.api_token)

    existing = (
        db.query(OrgBackendConfig)
        .filter(OrgBackendConfig.user_id == current_user.id)
        .first()
    )
    if existing:
        existing.provider = cfg.provider
        if encrypted_token is not None:
            existing.encrypted_api_token = encrypted_token
        existing.endpoint_url = cfg.endpoint_url
        existing.backend_name = cfg.backend_name
    else:
        new_cfg = OrgBackendConfig(
            user_id=current_user.id,
            provider=cfg.provider,
            encrypted_api_token=encrypted_token,
            endpoint_url=cfg.endpoint_url,
            backend_name=cfg.backend_name,
        )
        db.add(new_cfg)

    db.commit()
    return {
        "success": True,
        "provider": cfg.provider,
        "token_configured": encrypted_token is not None,
        "message": f"Backend config saved. Provider: {cfg.provider}.",
    }


@router.get("/backend-config", response_model=BackendConfigOut)
def get_backend_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BackendConfigOut:
    """
    Retrieve the current backend configuration.
    Returns provider, endpoint, and backend name.
    token_configured = True if a token has been stored.
    The actual token is NEVER returned.
    """
    cfg = (
        db.query(OrgBackendConfig)
        .filter(OrgBackendConfig.user_id == current_user.id)
        .first()
    )
    if not cfg:
        return BackendConfigOut(
            provider="local",
            endpoint_url=None,
            backend_name=None,
            token_configured=False,
        )
    return BackendConfigOut(
        provider=cfg.provider,
        endpoint_url=cfg.endpoint_url,
        backend_name=cfg.backend_name,
        token_configured=cfg.encrypted_api_token is not None,
    )


@router.delete("/backend-config", status_code=status.HTTP_200_OK)
def delete_backend_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Clear saved backend credentials and revert to local simulator.
    """
    cfg = (
        db.query(OrgBackendConfig)
        .filter(OrgBackendConfig.user_id == current_user.id)
        .first()
    )
    if cfg:
        db.delete(cfg)
        db.commit()
    return {
        "success": True,
        "message": "Backend credentials cleared. Reverted to local NumPy simulator.",
    }


# ---------------------------------------------------------------------------
# Helper — called by the optimization pipeline to load decrypted config
# ---------------------------------------------------------------------------

def get_decrypted_backend_config(user_id: str, db: Session) -> Optional[Dict[str, Any]]:
    """
    Load and decrypt the backend config for a user.
    Returns None if no config exists (use local solver).
    Returns a dict with 'provider', 'api_token', 'endpoint_url', 'backend_name'.
    """
    cfg = (
        db.query(OrgBackendConfig)
        .filter(OrgBackendConfig.user_id == user_id)
        .first()
    )
    if not cfg or cfg.provider == "local":
        return None

    plain_token = _decrypt_token(cfg.encrypted_api_token) if cfg.encrypted_api_token else None
    return {
        "provider": cfg.provider,
        "api_token": plain_token,
        "endpoint_url": cfg.endpoint_url,
        "backend_name": cfg.backend_name,
    }
