from fastapi import APIRouter
from app.api.v1.endpoints import reports, search, drift, domains, auth_profiles, audit_logs, costs, security_patterns

api_router = APIRouter()

api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(drift.router, prefix="/projects", tags=["Drift"])
api_router.include_router(domains.router, prefix="/domains", tags=["Domains"])
api_router.include_router(auth_profiles.router, prefix="/auth-profiles", tags=["Auth Profiles"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["Audit Logs"])
api_router.include_router(costs.router, prefix="/costs", tags=["LLM Costs"])
api_router.include_router(security_patterns.router, prefix="/security-patterns", tags=["Security Testing"])
