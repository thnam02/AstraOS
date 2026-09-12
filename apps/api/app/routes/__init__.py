"""HTTP routers.

Route handlers stay thin. Business logic belongs in services or
decision modules, not here.
"""

from fastapi import APIRouter

api_v1_router = APIRouter()
