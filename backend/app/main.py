from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .routers import addresses, auth, cart, catalog, checkout, orders, payment_methods, payments, regions
from .services.errors import ServiceError


app = FastAPI(title="Build Mart API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(regions.router)
app.include_router(cart.router)
app.include_router(addresses.router)
app.include_router(payment_methods.router)
app.include_router(checkout.router)
app.include_router(orders.router)
app.include_router(payments.router)


@app.exception_handler(ServiceError)
async def handle_service_error(request: Request, exc: ServiceError) -> JSONResponse:
    content = {"detail": exc.message, "code": exc.code, **exc.extra}
    return JSONResponse(status_code=exc.status_code, content=jsonable_encoder(content))


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Submitted values are dropped so card numbers and passwords are never echoed back.
    errors = [{key: value for key, value in error.items() if key not in ("input", "ctx", "url")} for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(errors)})


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)