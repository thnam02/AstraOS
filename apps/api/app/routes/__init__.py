"""HTTP routers.

Route handlers stay thin. Business logic belongs in services or
decision modules, not here.
"""

from fastapi import APIRouter

from app.routes.catalogue import router as catalogue_router
from app.routes.intent import router as intent_router
from app.routes.match import router as match_router
from app.routes.merchant import router as merchant_router

api_v1_router = APIRouter()
api_v1_router.include_router(catalogue_router)
api_v1_router.include_router(intent_router)
api_v1_router.include_router(match_router)
api_v1_router.include_router(merchant_router)
