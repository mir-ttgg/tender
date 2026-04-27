from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.config import settings
from app.core.redis import close_redis
from app.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    logger.info('api starting', prefix=settings.api_v1_prefix)
    try:
        yield
    finally:
        await close_redis()
        logger.info('api stopped')


app = FastAPI(title='TenderHelp API', version='0.1.0', lifespan=lifespan)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    logger.bind(path=request.url.path, status=exc.status_code).info('http error: {}', exc.detail)
    return JSONResponse(status_code=exc.status_code, content={'detail': exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.bind(path=request.url.path).info('validation error: {}', exc.errors())
    return JSONResponse(status_code=422, content={'detail': exc.errors()})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.bind(path=request.url.path).exception('unhandled error')
    return JSONResponse(status_code=500, content={'detail': 'internal server error'})


@app.get('/health', tags=['health'])
async def health() -> dict[str, str]:
    return {'status': 'ok'}
