import secrets

from fastapi import Header, HTTPException

from app import config


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not config.API_KEY:
        raise HTTPException(status_code=503, detail="Write access is not configured")
    if x_api_key is None or not secrets.compare_digest(
        x_api_key.encode(), config.API_KEY.encode()
    ):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
