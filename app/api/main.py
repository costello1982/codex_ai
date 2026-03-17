"""FastAPI entrypoint."""
from fastapi import FastAPI

from app.api.routes_design import router as design_router
from app.api.routes_docs import router as docs_router
from app.api.routes_generate import router as generate_router
from app.core.logging import setup_logging

setup_logging()
app = FastAPI(title="NX-OS VXLAN EVPN Designer")
app.include_router(docs_router)
app.include_router(design_router)
app.include_router(generate_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
