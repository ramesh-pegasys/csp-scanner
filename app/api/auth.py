# app/api/auth.py


def verify_jwt_token(token: str | None = None):
    """Stub for JWT token verification (real implementation is patched in tests)."""
    return {"token": token}
