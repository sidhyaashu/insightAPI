from fastapi import APIRouter
from app.api.v1.endpoints import crawls, reports, search

api_router = APIRouter()

api_router.include_router(crawls.router, prefix="/crawls", tags=["Crawls"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
