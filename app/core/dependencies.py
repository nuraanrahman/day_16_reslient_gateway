from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.openai_provider import OpenAIProvider
from app.services.chat_service import ChatService
from app.services.circuit_breaker import CircuitBreaker
from app.services.cost_tracker import CostTracker
from app.services.user_service import User, get_user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise credentials_error

    email: str | None = payload.get("sub")
    if email is None:
        raise credentials_error

    user = get_user(email)
    if user is None:
        raise credentials_error

    return user


@lru_cache
def get_openai_provider() -> OpenAIProvider:
    settings = get_settings()
    return OpenAIProvider(api_key=settings.openai_api_key, model=settings.default_model)


@lru_cache
def get_anthropic_provider() -> AnthropicProvider:
    settings = get_settings()
    return AnthropicProvider(api_key=settings.anthropic_api_key, model=settings.anthropic_model)


# Default LLM provider for the existing /chat endpoint
def get_llm_provider() -> OpenAIProvider:
    return get_openai_provider()


@lru_cache
def get_chat_service() -> ChatService:
    return ChatService()


@lru_cache
def get_cost_tracker() -> CostTracker:
    return CostTracker()


@lru_cache
def get_circuit_breaker() -> CircuitBreaker:
    return CircuitBreaker(failure_threshold=5, recovery_timeout=60)
