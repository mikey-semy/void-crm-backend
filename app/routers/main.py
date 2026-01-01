"""Главный роутер с редиректом на документацию."""

from fastapi.responses import RedirectResponse

from app.routers.base import BaseRouter


class MainRouter(BaseRouter):
    """
    Класс роутера для главной страницы приложения.
    """

    def __init__(self):
        super().__init__(prefix="", tags=["Main"])

    def configure(self):
        @self.router.get("/")
        async def root() -> RedirectResponse:
            """
            🏠 **Перенаправление на документацию.**

            **Returns**:
            - **RedirectResponse**: Перенаправление по адресу **/docs**
            """
            return RedirectResponse(url="/docs")
