"""Exceptions raised by the CasaTunes API client."""


class CasaTunesError(Exception):
    """Base CasaTunes client exception."""


class CasaTunesConnectionError(CasaTunesError):
    """The CasaTunes server could not be reached."""


class CasaTunesResponseError(CasaTunesError):
    """The CasaTunes server returned an invalid or unsuccessful response."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status
