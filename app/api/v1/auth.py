from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger

from app.core.deps import DbSession
from app.core.security import decode_token
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services import auth_service

router = APIRouter(prefix='/auth', tags=['auth'])

_bearer = HTTPBearer(auto_error=True)


@router.post('/register', response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: DbSession) -> UserResponse:
    user = await auth_service.register_user(session, payload.email, payload.password)
    return UserResponse(id=user.id, email=user.email, is_admin=user.is_admin)


@router.post('/login', response_model=TokenResponse)
async def login(payload: LoginRequest, session: DbSession) -> TokenResponse:
    token, _ = await auth_service.authenticate(session, payload.email, payload.password)
    return TokenResponse(token_access=token)


@router.post('/logout', status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> None:
    try:
        payload = decode_token(credentials.credentials)
    except ValueError:
        logger.warning('logout: invalid token')
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='invalid token')

    jti = payload.get('jti')
    exp = payload.get('exp')
    if not jti or not exp:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='invalid token')

    await auth_service.revoke_token(jti, int(exp))
