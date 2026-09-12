"""HTTP routers.

Route handlers stay thin. Business logic belongs in services or
decision modules, not here.
"""

from fastapi import APIRouter

from app.routes.agent import router as agent_router
from app.routes.arena import router as arena_router
from app.routes.catalogue import router as catalogue_router
from app.routes.decision import router as decision_router
from app.routes.demo import router as demo_router
from app.routes.intent import router as intent_router
from app.routes.learning import router as learning_router
from app.routes.match import router as match_router
from app.routes.merchant import router as merchant_router
from app.routes.negotiation import router as negotiation_router
from app.routes.offers import router as offers_router
from app.routes.optimisation import router as optimisation_router
from app.routes.orders import router as orders_router
from app.routes.transactions import router as transactions_router

api_v1_router = APIRouter()
api_v1_router.include_router(catalogue_router)
api_v1_router.include_router(intent_router)
api_v1_router.include_router(match_router)
api_v1_router.include_router(merchant_router)
api_v1_router.include_router(offers_router)
api_v1_router.include_router(optimisation_router)
api_v1_router.include_router(decision_router)
api_v1_router.include_router(negotiation_router)
api_v1_router.include_router(transactions_router)
api_v1_router.include_router(orders_router)
api_v1_router.include_router(demo_router)
api_v1_router.include_router(arena_router)
api_v1_router.include_router(learning_router)
api_v1_router.include_router(agent_router)
