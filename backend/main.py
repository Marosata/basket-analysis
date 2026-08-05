from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.routers import ingestion, analytics
from app.services.data_fetcher import DataNotFoundError, UpstreamAPIError

app = FastAPI(title="Basket Analysis API")

app.include_router(ingestion.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1/analytics")


@app.exception_handler(DataNotFoundError)
async def data_not_found_handler(request: Request, exc: DataNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(UpstreamAPIError)
async def upstream_api_error_handler(request: Request, exc: UpstreamAPIError):
    # Upstream API errors map to 502 Bad Gateway
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
