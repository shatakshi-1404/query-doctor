import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import models  # noqa: F401  (importing registers the tables)
from app.api.routes import history, queries
from app.core.database import Base, engine, get_db

logger = logging.getLogger("querydoctor")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        logger.exception("Could not create history tables. Is PostgreSQL running?")
    else:
        logger.info("QueryDoctor backend ready. Tables verified.")
    yield


app = FastAPI(title="QueryDoctor", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(queries.router, prefix="/api/queries", tags=["queries"])
app.include_router(history.router, prefix="/api/history", tags=["history"])


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    error_id = uuid.uuid4().hex[:8]
    logger.exception("Unhandled error [%s] on %s %s", error_id, request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Something went wrong on our side (reference: {error_id})."},
    )


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health/db")
def database_health_check(db: Session = Depends(get_db)):
    try:
        users_count = db.execute(text("SELECT count(*) FROM users")).scalar()
    except Exception:
        raise HTTPException(status_code=503, detail="Database is unavailable.")
    return {"status": "ok", "database": "connected", "users_count": users_count}
