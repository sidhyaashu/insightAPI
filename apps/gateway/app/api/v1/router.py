"""Gateway — API Router Aggregator."""
from fastapi import APIRouter
from app.api.v1.endpoints.proxy import router as rest_router
from app.api.v1.endpoints.ws import router as ws_router

api_router = APIRouter()

# WebSocket routes must be registered before catch-all REST proxy
api_router.include_router(ws_router)
api_router.include_router(rest_router)
