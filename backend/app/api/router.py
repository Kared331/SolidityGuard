from fastapi import APIRouter, Depends

from app.auth import verify_api_key

from app.api.analysis import router as analysis_router
from app.api.detections import router as detections_router
from app.api.fuzz import router as fuzz_router
from app.api.knowledge import router as knowledge_router
from app.api.llm_audit import router as llm_audit_router
from app.api.projects import router as projects_router
from app.api.reports import router as reports_router
from app.api.vulnerabilities import router as vulnerabilities_router

api_router = APIRouter()
api_router.include_router(projects_router, prefix="/api/v1/projects", dependencies=[Depends(verify_api_key)])
api_router.include_router(analysis_router, prefix="/api/v1/projects", dependencies=[Depends(verify_api_key)])
api_router.include_router(fuzz_router, prefix="/api/v1/projects", dependencies=[Depends(verify_api_key)])
api_router.include_router(llm_audit_router, prefix="/api/v1/projects", dependencies=[Depends(verify_api_key)])
api_router.include_router(reports_router, prefix="/api/v1", dependencies=[Depends(verify_api_key)])
api_router.include_router(detections_router, prefix="/api/v1", dependencies=[Depends(verify_api_key)])
api_router.include_router(knowledge_router, prefix="/api/v1", dependencies=[Depends(verify_api_key)])
api_router.include_router(vulnerabilities_router, prefix="/api/v1", dependencies=[Depends(verify_api_key)])
