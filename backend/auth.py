"""
Authentication — JWT + RBAC
=============================
Provides register, login, and token validation.
Roles: admin (full access + user management), analyst (full analysis), viewer (read-only).
"""
import os
import time
from typing import Optional, Dict
from jose import jwt, JWTError
from passlib.hash import bcrypt
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from persistence import create_user, get_user, get_user_by_id
import logging
logger = logging.getLogger(__name__)

SECRET_KEY = os.environ.get("JWT_SECRET", "yield-intelligence-dev-secret-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

security = HTTPBearer(auto_error=False)

ROLE_PERMISSIONS = {
    "admin": {"read", "write", "optimize", "upload", "export", "manage_users", "scenarios"},
    "analyst": {"read", "write", "optimize", "upload", "export", "scenarios"},
    "viewer": {"read", "export"},
}


def hash_password(password: str) -> str:
    return bcrypt.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.verify(password, password_hash)


def create_token(user_id: int, username: str, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": time.time() + TOKEN_EXPIRE_HOURS * 3600,
        "iat": time.time(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("exp", 0) < time.time():
            raise HTTPException(401, "Token expired")
        return payload
    except JWTError:
        raise HTTPException(401, "Invalid token")


def register_user(username: str, password: str, role: str = "analyst") -> Dict:
    """Register a new user."""
    if len(password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    if role not in ROLE_PERMISSIONS:
        raise HTTPException(400, f"Invalid role. Must be one of: {list(ROLE_PERMISSIONS.keys())}")
    try:
        user_id = create_user(username, hash_password(password), role)
    except ValueError as e:
        raise HTTPException(409, str(e))
    token = create_token(user_id, username, role)
    return {"user_id": user_id, "username": username, "role": role, "token": token}


def login_user(username: str, password: str) -> Dict:
    """Authenticate and return JWT."""
    user = get_user(username)
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    token = create_token(user["id"], user["username"], user["role"])
    return {"user_id": user["id"], "username": user["username"], "role": user["role"], "token": token}


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[Dict]:
    """Extract user from JWT token. Returns None if no auth header (anonymous mode)."""
    if credentials is None:
        return None  # Anonymous access allowed
    payload = decode_token(credentials.credentials)
    user = get_user_by_id(int(payload["sub"]))
    if not user:
        raise HTTPException(401, "User not found")
    return user


def require_role(*roles):
    """Dependency that checks user has one of the specified roles."""
    async def checker(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
        if credentials is None:
            # Anonymous access — check if "anonymous" is in allowed roles
            if "anonymous" in roles:
                return {"id": 0, "username": "anonymous", "role": "analyst"}
            raise HTTPException(401, "Authentication required")
        payload = decode_token(credentials.credentials)
        user_role = payload.get("role", "viewer")
        if user_role not in roles:
            raise HTTPException(403, f"Requires role: {', '.join(roles)}. You have: {user_role}")
        return {"id": int(payload["sub"]), "username": payload["username"], "role": user_role}
    return checker


def check_permission(user: Optional[Dict], permission: str) -> bool:
    """Check if user has a specific permission."""
    if user is None:
        return permission in ROLE_PERMISSIONS.get("analyst", set())  # Anonymous = analyst
    role = user.get("role", "viewer")
    return permission in ROLE_PERMISSIONS.get(role, set())
