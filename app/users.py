import uuid
from typing import Optional
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers,UUIDIDMixin, models
from fastapi_users.authentication import(
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy
)
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.authentication import BearerTransport, JWTStrategy, AuthenticationBackend
from app.db import User, get_user_db

SECRET = "THISISSECRET"

class userManager(UUIDIDMixin,BaseUserManager[User,uuid.UUID]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(
        self, user: models.UP, request: Request | None = None) -> None:
        print(f"User {user.id} is registered")

    async def on_after_forgot_password(self, user: User, token: str , request: Optional[Request] | None = None) -> None:
        print(f"User {user.id} is forgot password")

    async def on_after_request_verify(
        self, user: models.UP, token: str, request: Request | None = None
    ) -> None:
        print(f"Verfication requested for user {user.id}.Verification token = {token}")

async def get_User_manager(user_db: SQLAlchemyUserDatabase= Depends(get_user_db)):
    yield userManager(user_db)

bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

def get_jwt_strategy()->JWTStrategy:
    return JWTStrategy(secret=SECRET,lifetime_seconds=3600)

auth_backend = AuthenticationBackend(
    name = 'jwt',
    transport = bearer_transport,
    get_strategy = get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User,uuid.UUID](get_User_manager,[auth_backend])
current_active_user = fastapi_users.current_user(active=True)