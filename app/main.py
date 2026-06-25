"""
app/main.py
-----------
FastAPI application entry point.

Registers both routers and a catch-all exception handler that prevents
unhandled exceptions from leaking stack traces to API callers.
"""
from __future__ import annotations

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from app.dependencies.auth import require_api_key
from app.routes import items, orders

app = FastAPI(
    title="Food Orders API",
    description=(
        "REST API for managing food orders backed by **Azure Cosmos DB**.\n\n"
        "## Authentication\n"
        "All endpoints (except `GET /health`) require an **API key** in the "
        "`X-API-Key` request header. Click the **Authorize** button above and "
        "enter your key to test endpoints interactively here in Swagger UI.\n\n"
        "## Features\n"
        "- Full CRUD for orders and order items\n"
        "- Cascade delete — removing an order also removes all its items\n"
        "- Nutritional info and allergy tracking per item\n"
        "- Private image storage proxied through the API\n"
        "- Realistic seed data with 100 orders across 8 food categories\n"
    ),
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={"name": "Food Orders API", "email": "api@foodorders.example.com"},
    license_info={"name": "MIT"},
)

# ── Routers ───────────────────────────────────────────────────────────────────
# require_api_key is applied to both routers — /health is intentionally excluded
# so load balancers and uptime monitors can reach it without credentials.

app.include_router(orders.router, dependencies=[Depends(require_api_key)])
app.include_router(items.router, dependencies=[Depends(require_api_key)])

# ── Global exception handler ──────────────────────────────────────────────────


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a safe 500 JSON body instead of leaking a Python traceback."""
    return JSONResponse(
        status_code=500,
        content={"message": "An unexpected error occurred.", "detail": str(exc)},
    )


# ── Utility endpoints ─────────────────────────────────────────────────────────


@app.get("/health", tags=["Health"], summary="Liveness check")
def health() -> dict:
    """Returns 200 OK when the application process is running."""
    return {"status": "ok"}
