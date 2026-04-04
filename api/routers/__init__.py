"""API routers"""
from .accounts import router as accounts_router
from .players import router as players_router

__all__ = ["accounts_router", "players_router"]
