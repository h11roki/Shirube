from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.exc import OperationalError

from app.application.ports import StorageUnavailableError


@contextmanager
def unavailable_as_storage_error() -> Iterator[None]:
    try:
        yield
    except OperationalError as error:
        raise StorageUnavailableError(str(error.orig)) from error
