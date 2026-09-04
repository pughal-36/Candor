"""
Candor — FastAPI application entry point.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Candor starting — confidence threshold: %.0f%%",
        settings.confidence_threshold * 100,
    )
    yield


app = FastAPI(
    title="Candor API",
    description=(
        "Deterministic-first reconciliation agent for merchant payments.\n\n"
        "Pipeline: PDF ingestion → exact match pass → LLM fuzzy pass → "
        "verification gate → exception ledger."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error processing %s: %s", request.url, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )


app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["meta"])
def health() -> dict:
    """Liveness check."""
    return {"status": "ok", "version": "0.1.0"}
