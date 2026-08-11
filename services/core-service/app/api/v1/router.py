"""Core Service — API v1 Router Aggregator."""
from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, payments, internal, apikeys

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(payments.router)
api_router.include_router(internal.router)
api_router.include_router(apikeys.router)
