from fastapi import APIRouter
from app.api.v1.endpoints import users, billing, ml

api_router = APIRouter()
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(billing.router, prefix="/billing", tags=["Billing"])
api_router.include_router(ml.router, prefix="/ml", tags=["ML Model"])