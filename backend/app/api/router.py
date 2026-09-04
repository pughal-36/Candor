"""
Candor — Central API router.
Aggregates all route modules under /api/v1.
"""
from fastapi import APIRouter

from app.api.routes import upload, batches, exceptions_route, config_route

api_router = APIRouter()

api_router.include_router(upload.router, tags=["upload"])
api_router.include_router(batches.router, tags=["batches"])
api_router.include_router(exceptions_route.router, tags=["exceptions"])
api_router.include_router(config_route.router, tags=["config"])
