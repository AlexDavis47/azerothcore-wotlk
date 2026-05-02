"""AzerothCore API main application"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from routers import accounts_router
from routers.players import router as players_router
from config import API_HOST, API_PORT
from notifications import start_polling, stop_polling


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_polling(interval=30)
    yield
    stop_polling()


app = FastAPI(
    title="AzerothCore API",
    description="API for AzerothCore WoW server management",
    version="1.0.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(accounts_router)
app.include_router(players_router)


@app.get("/health", tags=["health"])
async def health():
    """Health check endpoint"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
