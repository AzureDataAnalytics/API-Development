"""
app/main.py
-----------
FastAPI application entry point.

Registers both routers and a catch-all exception handler that prevents
unhandled exceptions from leaking stack traces to API callers.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.routes import items, orders

app = FastAPI(
    title="Food Orders API",
    description=(
        "REST API for managing food orders backed by **Azure Cosmos DB**.\n\n"
        "## Features\n"
        "- Full CRUD for orders and order items\n"
        "- Cascade delete — removing an order also removes all its items\n"
        "- Nutritional info and allergy tracking per item\n"
        "- Realistic seed data with 100 orders across 8 food categories\n"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={"name": "Food Orders API", "email": "api@foodorders.example.com"},
    license_info={"name": "MIT"},
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(orders.router)
app.include_router(items.router)

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
