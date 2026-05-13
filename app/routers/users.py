from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.dependencies import get_current_user
from app.services.user_service import User

router = APIRouter(prefix="/users", tags=["users"])


class MeResponse(BaseModel):
    id: str
    email: str
    created_at: str


@router.get("/me", response_model=MeResponse)
def get_me(current_user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        created_at=current_user.created_at.isoformat(),
    )
