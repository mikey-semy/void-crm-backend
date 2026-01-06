"""Users роутеры."""

from app.routers.v1.users.profile import UserRouter
from app.routers.v1.users.settings import UserSettingsRouter
from app.routers.v1.users.websocket import UsersWebSocketRouter

__all__ = [
    "UserRouter",
    "UserSettingsRouter",
    "UsersWebSocketRouter",
]
