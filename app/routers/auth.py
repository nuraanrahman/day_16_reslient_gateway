import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.security import create_access_token
from app.services.user_service import authenticate_user, create_user, get_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str


class RegisterResponse(BaseModel):
    id: str
    email: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(body: RegisterRequest):
    if get_user(body.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An account with email '{body.email}' already exists.",
        )
    new_user = create_user(email=body.email, plain_password=body.password)
    logger.info("user_registered", extra={
        "event": "user_registered",
        "user_id": new_user.id,
        "email": new_user.email,
    })
    return RegisterResponse(id=new_user.id, email=new_user.email)


@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(email=form_data.username, plain_password=form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    settings = get_settings()
    expire_minutes = settings.access_token_expire_minutes
    token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=expire_minutes),
    )
    logger.info("user_logged_in", extra={
        "event": "user_logged_in",
        "user_id": user.id,
        "email": user.email,
    })
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expire_minutes * 60,
    )
