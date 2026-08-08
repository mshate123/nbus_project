"""Application factory and FastAPI entrypoint for the ledger service."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.routes import router
from config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create a configured FastAPI application."""
    resolved_settings = settings or get_settings()
    engine = create_async_engine(resolved_settings.database_url, pool_size=10, max_overflow=5)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Expose the request session factory and dispose the engine on shutdown."""
        app.state.session_factory = session_factory
        app.state.settings = resolved_settings
        yield
        await engine.dispose()

    app = FastAPI(title="nbus-ledger", version="0.1.0", lifespan=lifespan)
    app.include_router(router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Return liveness without requiring a database connection."""
        return {"status": "ok"}

    @app.get("/ready")
    async def ready() -> JSONResponse:
        """Return readiness only when the database accepts a query."""
        try:
            async with session_factory() as session:
                await session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return JSONResponse(
                status_code=503, content={"status": "unavailable"}
            )
        return JSONResponse(status_code=200, content={"status": "ok"})

    return app


app = create_app()
