from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_bootstrap import router as bootstrap_router
from app.core.config import get_settings
from app.core.dependencies import bootstrap_service_dependency


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # Warm startup dependency container.
    _ = bootstrap_service_dependency()
    yield
    if settings.cache_backend == "redis":
        cache = bootstrap_service_dependency().cache
        close = getattr(cache, "close", None)
        if callable(close):
            close()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Shell Bootstrap API",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    app.include_router(bootstrap_router)

    return app


app = create_app()
