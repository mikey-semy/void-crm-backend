from starlette.status import HTTP_503_SERVICE_UNAVAILABLE

from app.core.exceptions import BaseAPIException


class ServiceUnavailableException(BaseAPIException):
    """
    Исключение, которое возникает, когда сервис недоступен.

    Это исключение наследуется от базового класса BaseAPIException и используется для
    обработки ситуаций, когда определённый сервис не может быть достигнут.

    Attributes:
        status_code (int): Код состояния HTTP, установленный на 503, что соответствует ошибке "Сервис недоступен".
        detail (str): Подробное сообщение об ошибке, указывающее, что указанный сервис недоступен.
        error_type (str): Тип ошибки, установленный как "dependecies_error", что указывает на зависимость от недоступного сервиса.

    Args:
        service_name (str): Имя сервиса, который недоступен. Это значение будет включено в сообщение об ошибке.
    """

    def __init__(self, service_name: str):
        """
        Инициализация исключения ServiceUnavailableException.

        Args:
            service_name (str): Имя недоступного сервиса.
        """
        super().__init__(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{service_name} сервис не доступен",
            error_type="dependecies_error",
        )
