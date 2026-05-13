import uuid
from datetime import datetime, timezone

from pydantic import BaseModel

from app.core.security import hash_password, verify_password


class User(BaseModel):
    id: str
    email: str
    hashed_password: str
    created_at: datetime


users_db: dict[str, User] = {}


def create_user(email: str, plain_password: str) -> User:
    new_user = User(
        id=str(uuid.uuid4()),
        email=email,
        hashed_password=hash_password(plain_password),
        created_at=datetime.now(timezone.utc),
    )
    users_db[email] = new_user
    return new_user


def get_user(email: str) -> User | None:
    return users_db.get(email)


def authenticate_user(email: str, plain_password: str) -> User | None:
    user = get_user(email)
    if user is None:
        hash_password("dummy_to_prevent_timing_attack")
        return None
    if not verify_password(plain_password, user.hashed_password):
        return None
    return user
