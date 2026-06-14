from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.application.services.llm_provider import get_llm_provider
import logging

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.on_event("startup")
def _startup():
    # instantiate provider to trigger autodiscovery and log the selected model
    try:
        provider = get_llm_provider()
        # If provider exposes a 'model' attribute (OllamaProvider), also log the model name
        model_name = getattr(provider, "model", None)
        logging.getLogger("llm_provider").info(
            "LLM provider initialized: %s, model=%s", type(provider).__name__, model_name
        )
    except Exception as exc:
        logging.getLogger("llm_provider").exception("Failed to initialize LLM provider: %s", exc)

