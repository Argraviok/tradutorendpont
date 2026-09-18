from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers.convert import router as convert_router

settings = get_settings()

app = FastAPI(
    title="API Transpiler - Universal Endpoint Converter",
    description="Backend para transpilação 1:1 determinística de endpoints de APIs para Python (FastAPI/Flask)",
    version="1.0.0"
)

# Configuração de CORS para permitir acesso do Angular
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite requisições do frontend local
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro de rotas
app.include_router(convert_router)


@app.get("/api/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "API Transpiler Backend",
        "has_gemini_key": bool(settings.gemini_api_key),
        "default_model": settings.default_model
    }


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "API Transpiler Universal está ativo.",
        "docs": "/docs",
        "health": "/api/health"
    }
