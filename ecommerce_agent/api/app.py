"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse

from ecommerce_agent.api.routes import ask, documents, health, products
from ecommerce_agent.config import PROJECT_ROOT

STATIC_DIR = PROJECT_ROOT / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    from ecommerce_agent.agent.tracing import flush_tracing

    flush_tracing()


def create_app() -> FastAPI:
    app = FastAPI(title="Local Agent API", lifespan=lifespan)
    app.include_router(ask.router)
    app.include_router(health.router)
    app.include_router(products.router)
    app.include_router(documents.router)

    @app.get("/")
    def ui():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/ecommerce")
    def ecommerce_catalog():
        return FileResponse(STATIC_DIR / "ecommerce.html")

    return app


app = create_app()
