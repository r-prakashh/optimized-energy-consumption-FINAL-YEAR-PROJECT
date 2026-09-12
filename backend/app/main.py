from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

app = FastAPI(
    title="Energy Forecasting & Cost Optimization API",
    description=(
        "Forecasts household energy consumption from historical patterns, "
        "estimates electricity cost, and produces a budget-constrained "
        "appliance usage plan."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to the deployed frontend origin before submission
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
def health_check():
    return {"status": "ok"}
