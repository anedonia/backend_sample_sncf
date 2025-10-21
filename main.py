from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from opticapa.features.axe_ef.router import axe_ef_router
from opticapa.features.probes_routes.router import probe_router
from opticapa.shared.config.config import settings

docs_url_dict = dict(
    docs_url="/api/docs", redoc_url="/api/redoc", openapi_url="/api/openapi.json"
)
if settings.environment == "production":
    docs_url_dict = {"openapi_url": None, "docs_url": None, "redoc_url": None}

app = FastAPI(
    title="Opticapa api services",
    docs_url=docs_url_dict["docs_url"],
    redoc_url=docs_url_dict["redoc_url"],
    openapi_url=docs_url_dict["openapi_url"],
    description="Welcome to Opticapa API Documentation",
    version="0.7.0",
)


origins = [settings.frontend_url, "http://localhost:4200"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

features_router = APIRouter(prefix="/api")
features_router.include_router(probe_router)
features_router.include_router(axe_ef_router)


app.include_router(features_router)
app.include_router(probe_router)
