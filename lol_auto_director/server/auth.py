"""Bearer token authentication for the regie API."""

from __future__ import annotations

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer = HTTPBearer(auto_error=False)


def make_verify_token(expected_token: str):
    def verify(
        credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
    ) -> None:
        if not expected_token:
            raise HTTPException(status_code=503, detail="Server API token not configured")
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Missing Bearer token")
        if credentials.credentials != expected_token:
            raise HTTPException(status_code=403, detail="Invalid API token")

    return verify
