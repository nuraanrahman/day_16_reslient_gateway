import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.dependencies import (
    get_chat_service,
    get_circuit_breaker,
    get_cost_tracker,
    get_current_user,
    get_llm_provider,
)
from app.models.schemas import ChatRequest, ChatResponse
from app.providers.base import LLMProvider
from app.services.chat_service import ChatService
from app.services.circuit_breaker import CircuitBreaker, CircuitBreakerOpen
from app.services.cost_tracker import CostTracker, DAILY_LIMIT
from app.services.user_service import User

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
@limiter.limit("10/minute")
async def post_chat(
    request: Request,
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    provider: LLMProvider = Depends(get_llm_provider),
    service: ChatService = Depends(get_chat_service),
    tracker: CostTracker = Depends(get_cost_tracker),
    breaker: CircuitBreaker = Depends(get_circuit_breaker),
) -> ChatResponse:
    if not request.app.state.ai_enabled:
        raise HTTPException(
            status_code=503,
            detail="AI feature is disabled. Set OPENAI_API_KEY to enable it.",
        )

    user_id = current_user.id

    if tracker.is_over_budget(user_id):
        tokens_today = tracker.get_usage(user_id)
        logger.warning("budget_exceeded", extra={
            "event": "budget_exceeded",
            "user_id": user_id,
            "tokens_today": tokens_today,
            "daily_limit": DAILY_LIMIT,
        })
        raise HTTPException(
            status_code=429,
            detail=(
                f"Daily token limit reached. "
                f"Used {tokens_today:,} / {DAILY_LIMIT:,} tokens today. "
                f"Resets at midnight."
            ),
        )

    try:
        reply, message_count, tokens_used = service.reply(
            body.session_id, body.message, provider, breaker
        )
    except CircuitBreakerOpen:
        raise HTTPException(
            status_code=503,
            detail="AI service is temporarily down. Please retry in 60 seconds.",
        )

    tracker.record_usage(user_id, tokens_used)

    logger.info("request_done", extra={
        "event": "request_done",
        "user_id": user_id,
        "tokens_this_request": tokens_used,
        "tokens_today": tracker.get_usage(user_id),
    })

    return ChatResponse(reply=reply, session_id=body.session_id, message_count=message_count)


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> dict:
    history = service.get_history(session_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "messages": history}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> dict:
    if not service.delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"detail": f"Session '{session_id}' deleted"}
