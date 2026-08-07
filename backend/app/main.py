from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.core.database import Base, engine
from app.api.endpoints import auth, optimize, reports, contributions, upload, backend_config

# Automatically create all database tables for SQLite / PostgreSQL
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise Quantum Optimization-as-a-Service (QOaaS) Platform REST API",
    version="2.0.0",
)

# ── CORS ───────────────────────────────────────────────────────────────────
# Origins are driven by the CORS_ORIGINS environment variable (comma-separated).
# Default: "http://localhost:3000" (Next.js dev server).
# Setting allow_origins=["*"] combined with allow_credentials=True is invalid
# per the CORS spec — we use an explicit list instead.
allowed_origins = settings.get_cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# ── Routers ────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(optimize.router, prefix=settings.API_V1_STR, tags=["Optimization"])
app.include_router(reports.router, prefix=settings.API_V1_STR, tags=["Reports"])
app.include_router(contributions.router, prefix=f"{settings.API_V1_STR}/contributions", tags=["Contributions"])
app.include_router(upload.router, prefix=settings.API_V1_STR, tags=["File Upload"])
app.include_router(backend_config.router, prefix=settings.API_V1_STR, tags=["Backend Config"])


@app.get("/")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": "2.0.0",
        "environment": settings.ENV,
    }
