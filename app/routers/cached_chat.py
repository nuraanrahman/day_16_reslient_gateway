import logging

from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_anthropic_provider, get_openai_provider
from app.models.schemas import CachedChatRequest, CachedChatResponse
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.openai_provider import OpenAIProvider
from app.services.prompts import get_system_prompt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["cached-chat"])


@router.post("/chat-cached", response_model=CachedChatResponse)
async def chat_cached(
    body: CachedChatRequest,
    anthropic_provider: AnthropicProvider = Depends(get_anthropic_provider),
    openai_provider: OpenAIProvider = Depends(get_openai_provider),
) -> CachedChatResponse:
    try:
        system_prompt = get_system_prompt(body.prompt_name)
    except KeyError as e:
        raise HTTPException(status_code=422, detail=str(e))

    provider_name = body.provider.lower()

    try:
        if provider_name == "anthropic":
            reply, cache_creation, cache_read, total = anthropic_provider.generate(
                system_prompt=system_prompt,
                user_message=body.user_message,
            )
            cached_tokens = cache_read
        elif provider_name == "openai":
            reply, _, cache_read, total = openai_provider.generate(
                system_prompt=system_prompt,
                user_message=body.user_message,
            )
            cached_tokens = cache_read
        else:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown provider '{body.provider}'. Use 'anthropic' or 'openai'.",
            )
    except HTTPException:
        raise
    except Exception as e:
        # All 3 retry attempts failed — return 502 to the client.
        logger.error("llm_all_retries_failed", extra={
            "event": "llm_all_retries_failed",
            "provider": provider_name,
            "error": str(e),
        })
        raise HTTPException(status_code=502, detail=f"LLM error after all retries: {e}")

    cache_hit_rate = round(cached_tokens / total, 4) if total > 0 else 0.0

    logger.info("cached_chat_done", extra={
        "event": "cached_chat_done",
        "provider": provider_name,
        "prompt_name": body.prompt_name,
        "cached_tokens": cached_tokens,
        "total_tokens": total,
        "cache_hit_rate": cache_hit_rate,
    })

    return CachedChatResponse(
        reply=reply,
        cached_tokens=cached_tokens,
        total_tokens=total,
        cache_hit_rate=cache_hit_rate,
    )
