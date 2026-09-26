"""Vercel entrypoint for the DataPilot FastAPI service."""

from app.api.main import app

__all__ = ["app"]
