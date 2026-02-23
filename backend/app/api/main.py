from fastapi import APIRouter
from backend.app.api.routes import home
from backend.app.api.routes.auth import register, activate

api_router = APIRouter()

api_router.include_router(home.router)
api_router.include_router(register.router)
api_router.include_router(activate.router)
