import hashlib
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.dependencies import get_user_service
from api.schemas.user import UserResponse
from application.user_service import UserService
from config import config
from domain.exceptions import UserNotFoundError

SECRET_KEY = config.JWT_SECRET
ALGORITHM = config.JWT_ALGORITHM
EXPIRE_DAYS = config.JWT_EXPIRE_DAYS

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


def create_token(user_id: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=EXPIRE_DAYS)
    return jwt.encode({"sub": user_id, "exp": exp}, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, service: UserService = Depends(get_user_service)):
    try:
        user = service.get_user_by_email(body.email)
    except UserNotFoundError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    hashed = hashlib.sha256(body.password.encode()).hexdigest()
    if user.password_hash != hashed:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return TokenResponse(
        access_token=create_token(str(user.id)),
        user=UserResponse.from_domain(user),
    )
