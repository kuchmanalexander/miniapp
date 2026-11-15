import contextvars
import logging
import sys

# Номер текущего запроса (виден в каждой строке лога)
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


_configured = False


def setup_logging(level: str = "INFO") -> None:
    """Единый формат логов: время, уровень, номер запроса, источник, сообщение."""
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"
        )
    )
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(level.upper())
    _configured = True