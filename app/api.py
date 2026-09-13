from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.env_variables.router import router as env_variables_router
from app.modules.files.router import router as files_router
from app.modules.folders.router import router as folders_router
from app.modules.items.router import router as items_router
from app.modules.snippets.router import router as snippets_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(folders_router)
api_router.include_router(snippets_router)
api_router.include_router(env_variables_router)
api_router.include_router(files_router)
api_router.include_router(items_router)
