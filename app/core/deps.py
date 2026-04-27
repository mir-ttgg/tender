from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.core.security import decode_token
from app.database import get_session
from app.models import User
from sqlalchemy import select

_bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except ValueError:
        logger.warning('token decode failed')
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='invalid token')

    jti = payload.get('jti')
    if jti:
        redis = get_redis()
        if await redis.get(f'jwt:blacklist:{jti}'):
            logger.info('token revoked', jti=jti)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='token revoked')

    sub = payload.get('sub')
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='invalid token')

    user = await session.scalar(select(User).where(User.id == int(sub)))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='user not found')
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_session)]
