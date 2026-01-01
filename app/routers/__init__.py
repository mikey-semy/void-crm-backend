"""Настройка роутеров приложения."""

from fastapi import FastAPI

from .health import HealthRouter
from .main import MainRouter
from .v1 import APIv1


def setup_routers(app: FastAPI):
    """
    Настраивает все роутеры для приложения FastAPI.
    """
    app.include_router(HealthRouter().get_router())
    app.include_router(MainRouter().get_router())

    v1_router = APIv1()
    v1_router.configure_routes()

    app.include_router(v1_router.get_router(), prefix="/api/v1")
