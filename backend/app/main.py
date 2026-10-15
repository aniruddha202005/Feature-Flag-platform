import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.cache import FlagCache
from app.config import settings
from app.db import Base, engine, get_db
from app.deps import get_cache
from app.exceptions import FlagAlreadyExistsError, FlagNotFoundError
from app.routers import evaluate, flags
from app.schemas import HealthOut

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Feature Flag Platform",
    version="1.0.0",
    description="Create, target and roll out feature flags with cache-first evaluation.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(flags.router)
app.include_router(evaluate.router)


@app.exception_handler(FlagNotFoundError)
async def handle_not_found(_: Request, exc: FlagNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(FlagAlreadyExistsError)
async def handle_conflict(_: Request, exc: FlagAlreadyExistsError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.get("/health", response_model=HealthOut, tags=["health"])
def health(db: Session = Depends(get_db), cache: FlagCache = Depends(get_cache)):
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    redis_ok = cache.ping()
    status = "ok" if db_ok and redis_ok else "degraded"
    return HealthOut(status=status, database=db_ok, redis=redis_ok)
