from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from app.api.rag import router as rag_router
from app.api.system import router as system_router
from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.users import router as users_router
from app.core.config import get_settings


settings = get_settings()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description="Autonomous Data Governance System API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(documents_router)
app.include_router(system_router)
app.include_router(rag_router)

@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "ADGS API is running",
        "environment": settings.ENVIRONMENT,
    }