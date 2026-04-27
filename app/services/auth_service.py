from datetime import datetime, timezone

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User


async def register_user(session: AsyncSession, email: str, password: str) -> User:
    existing = await session.scalar(select(User).where(User.email == email))
    if existing is not None:
        logger.info('register: email already exists', email=email)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='email already registered')

    user = User(email=email, password_hash=hash_password(password), is_admin=False)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    logger.info('user registered', user_id=user.id, email=email)
    return user


async def authenticate(session: AsyncSession, email: str, password: str) -> tuple[str, datetime]:
    user = await session.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(password, user.password_hash):
        logger.info('login failed', email=email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='invalid credentials')

    token, _, expire = create_access_token(subject=user.id)
    logger.info('user logged in', user_id=user.id)
    return token, expire


async def revoke_token(jti: str, exp: int) -> None:
    redis = get_redis()
    now_ts = int(datetime.now(tz=timezone.utc).timestamp())
    ttl = max(exp - now_ts, 1)
    await redis.set(f'jwt:blacklist:{jti}', '1', ex=ttl)
    logger.info('token revoked', jti=jti, ttl=ttl)
